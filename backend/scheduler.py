import itertools
import logging
import time
from . import gaode_api

# ---------------------------
# Core Scheduling Logic (Ported & Adapted from v9)
# ---------------------------

class Scheduler:
    def __init__(self, depots_data, tasks_data, vehicles_data):
        """
        初始化调度器
        :param depots_data: list of {'id': str, 'lat': float, 'lng': float}
        :param tasks_data: list of {'id': str, 'lat': float, 'lng': float, 'start': float, 'duration': float, 'power': float}
        :param vehicles_data: list of {'id': str, 'power': float, 'energy': float}
        """
        self.depots = {d['id']: d for d in depots_data}
        self.tasks = {t['id']: {
            'id': t['id'],
            'lat': t['lat'], 
            'lng': t['lng'],
            'r_start': float(t['start']), 
            'r_end': float(t['start']) + float(t['duration']),
            'p': float(t['power']),
            'duration': float(t['duration'])
        } for t in tasks_data}
        
        self.vehicles = {v['id']: {'P': float(v['power']), 'E': float(v['energy'])} for v in vehicles_data}
        
        # 矩阵缓存
        self.tau = {} # (from_id, to_id) -> hours
        self.polylines = {} # (from_id, to_id) -> polyline string
        
        # 收集所有涉及的坐标点用于构建矩阵
        self.all_locations = []
        for d in depots_data:
            self.all_locations.append({'id': d['id'], 'lat': d['lat'], 'lng': d['lng']})
        for t in tasks_data:
            self.all_locations.append({'id': t['id'], 'lat': t['lat'], 'lng': t['lng']})

    def build_travel_matrix(self):
        """调用高德 API 构建 N x N 的通行时间矩阵"""
        # 并发获取所有点对的路径数据
        raw_matrix = gaode_api.get_matrix_async(self.all_locations)
        
        for key, val in raw_matrix.items():
            u, v = key
            # 将秒转换为小时 (用于算法计算)
            self.tau[(u, v)] = val['duration'] / 3600.0
            self.polylines[(u, v)] = val['polyline']
            
        # 自环设为 0
        for loc in self.all_locations:
            self.tau[(loc['id'], loc['id'])] = 0.0

    def _get_travel_time(self, u, v):
        """获取两点间行驶时间 (小时)，如果 API 失败则返回无穷大"""
        return self.tau.get((u, v), 999.0)

    def compute_sequence_metrics(self, seq, v_id, upper_bound=float('inf')):
        """
        评估某辆车执行某个任务序列的可行性和成本
        Args:
            seq: 任务ID列表
            v_id: 车辆ID
            upper_bound: 当前已知的全局最优总时间（用于剪枝）
        Returns: (feasible, depot_used, total_time, energy_sum, max_power, timeline)
        """
        if not seq:
            return True, None, 0.0, 0.0, 0.0, []

        m = len(seq)
        best_overall = None 

        # 尝试从每一个车库出发
        for d_id in self.depots:
            
            # 内部递归函数：将序列切分为多次往返 (Trip)
            def try_from(i, current_time, current_energy, current_max_p, current_timeline):
                # 剪枝 1: 如果当前单一车辆的累积时间已经超过了全局(所有车辆)的最优解，
                # 虽然这里不仅是单一车辆比较，但如果单车耗时过长通常也意味着总解不好。
                # 更严格的剪枝应该在外部循环做，这里只能做局部剪枝。
                # 不过，如果 current_time 已经甚至超过了 upper_bound，那肯定没戏了。
                if current_time > upper_bound:
                    return False, None, None, None, None, None

                if i >= m:
                    return True, current_time, current_energy, current_max_p, current_timeline, current_time

                best_local = None

                # 尝试构建一个 Trip，包含 seq[i] 到 seq[j]
                for j in range(i, m):
                    subseq = seq[i:j+1]
                    first = subseq[0]
                    last = subseq[-1]

                    # 1. 从车库/上一次位置出发去第一个任务
                    # 注意：如果是第一趟Trip，从 d_id 出发；
                    # 如果是后续Trip，current_time 已经是 "返回d_id并准备好出发" 的时间了吗？
                    # 递归设计是：try_from(..., return_time)
                    # 所以 current_time 是上一趟回到车库的时间点。
                    # 这一趟从 d_id 出发去 first
                    
                    travel_time_d_1 = self._get_travel_time(d_id, first)
                    
                    # 最早出发时间 & 实际出发时间
                    earliest_depart = max(0.0, self.tasks[first]['r_start'] - travel_time_d_1)
                    depart_time = max(current_time, earliest_depart)
                    arrival_first = depart_time + travel_time_d_1
                    
                    if arrival_first - self.tasks[first]['r_start'] > 1e-5:
                        continue 

                    # 构建 Timeline 事件
                    timeline_trip = []
                    # ... (timeline构建逻辑同前，略微精简) ...
                    timeline_trip.append({
                        "type": "travel", "from": d_id, "to": first, 
                        "start": depart_time, "end": arrival_first,
                        "polyline": self.polylines.get((d_id, first), "")
                    })

                    if arrival_first < self.tasks[first]['r_start'] - 1e-5:
                        timeline_trip.append({"type": "idle_task", "at": first, "start": arrival_first, "end": self.tasks[first]['r_start']})

                    timeline_trip.append({"type": "work", "task": first, "start": self.tasks[first]['r_start'], "end": self.tasks[first]['r_end']})

                    cur_time = self.tasks[first]['r_end']
                    prev = first
                    feasible_trip = True

                    # 2. Trip 内部：任务间移动
                    for nxt in subseq[1:]:
                        travel_t = self._get_travel_time(prev, nxt)
                        arrive = cur_time + travel_t
                        
                        if arrive - self.tasks[nxt]['r_start'] > 1e-5:
                            feasible_trip = False; break
                        
                        timeline_trip.append({
                            "type": "travel", "from": prev, "to": nxt, 
                            "start": cur_time, "end": arrive,
                            "polyline": self.polylines.get((prev, nxt), "")
                        })
                        
                        if arrive < self.tasks[nxt]['r_start'] - 1e-5:
                            timeline_trip.append({"type": "idle_task", "at": nxt, "start": arrive, "end": self.tasks[nxt]['r_start']})
                        
                        timeline_trip.append({"type": "work", "task": nxt, "start": self.tasks[nxt]['r_start'], "end": self.tasks[nxt]['r_end']})
                        
                        cur_time = self.tasks[nxt]['r_end']
                        prev = nxt

                    if not feasible_trip:
                        continue

                    # 3. 返回车库
                    return_travel = self._get_travel_time(last, d_id)
                    return_time = cur_time + return_travel
                    timeline_trip.append({
                        "type": "travel", "from": last, "to": d_id, 
                        "start": cur_time, "end": return_time,
                        "polyline": self.polylines.get((last, d_id), "")
                    })
                    
                    # 4. 车辆能力约束校验
                    trip_energy = sum(self.tasks[t]['p'] * self.tasks[t]['duration'] for t in subseq)
                    trip_max_power = max(self.tasks[t]['p'] for t in subseq)
                    veh = self.vehicles[v_id]
                    if trip_max_power > veh['P'] + 1e-5 or trip_energy > veh['E'] + 1e-5:
                        continue

                    # 剪枝 2: 如果当前部分解已经比局部最优差，直接跳过 (假设目标是最小化单车时间)
                    # if best_local and return_time + ... > best_local[0]: continue

                    # 5. 递归
                    # 下一趟出发前，如果在车库有等待时间，将在 merged_timeline 里处理
                    # 递归传入新的累积值
                    new_timeline = current_timeline + timeline_trip
                    
                    # 处理中间等待 (idle_depot) 会在合并时处理，这里简化逻辑：
                    # 递归函数本身只负责计算“从 return_time 开始的后续部分”
                    # 我们需要把 timeline 传递下去或者在回溯时合并。
                    # 为了保持原逻辑结构，这里不传递完整 timeline，只传递时间。
                    
                    ok_next, tot_next, energy_next, maxp_next, timeline_next, final_return = try_from(
                        j+1, return_time, 
                        current_energy + trip_energy, 
                        max(current_max_p, trip_max_power),
                        [] # 这里的 timeline 仅仅是后续的
                    )
                    
                    if not ok_next:
                        continue

                    # 合并
                    merged = list(timeline_trip)
                    if timeline_next:
                        first_next = timeline_next[0]
                        next_depart = first_next.get("start", None)
                        if next_depart is not None and next_depart - return_time > 1e-5:
                            merged.append({"type": "idle_depot", "at": d_id, "start": return_time, "end": next_depart})
                    merged.extend(timeline_next)

                    # 计算该方案的总时间 (last_return - initial_depart)
                    # 注意：try_from 的 current_time 参数实际上是 "Available time at Depot"
                    # 最外层调用时是 0.0。
                    # 该方案的结束时间是 final_return。
                    # 总耗时 = final_return - (timeline_trip[0]['start']) ? 
                    # 原逻辑是 sum(trip_duration)，即累加每一趟的 (return - depart)。
                    # 这里保持原逻辑： tot_next 已经是后续所有trip的耗时和。
                    
                    trip_dur = return_time - depart_time
                    total_time_candidate = trip_dur + tot_next
                    
                    energy_sum_candidate = trip_energy + energy_next
                    max_power_candidate = max(trip_max_power, maxp_next)

                    if best_local is None or total_time_candidate < best_local[0]:
                        best_local = (total_time_candidate, energy_sum_candidate, max_power_candidate, merged, final_return)

                if best_local is None:
                    return False, None, None, None, None, None
                # 返回 cost (duration), energy, power, timeline, final_time
                return True, best_local[0], best_local[1], best_local[2], best_local[3], best_local[4]

            # 启动递归
            ok, tot_time, energy_sum, max_power, timeline_list, final_return_time = try_from(0, 0.0, 0.0, 0.0, [])
            if not ok:
                continue
            
            # 记录对于这辆车，从哪个Depot出发最好
            if best_overall is None or tot_time < best_overall[0]:
                best_overall = (tot_time, energy_sum, max_power, timeline_list, d_id)

        if best_overall is None:
            return False, None, None, None, None, None

        total_time, energy_sum, max_power, timeline, depot_used = best_overall
        return True, depot_used, total_time, energy_sum, max_power, timeline

    def _greedy_solve(self):
        """
        贪心算法求初值：
        1. 简单的最近邻策略或直接按顺序分配
        2. 返回一个可行解的总时间，作为 Branch & Bound 的上限
        """
        task_ids = list(self.tasks.keys())
        vehicle_ids = list(self.vehicles.keys())
        
        # 简单策略：将所有任务平均分配给车辆
        # 仅为了快速获取一个 Upper Bound
        import math
        chunk_size = math.ceil(len(task_ids) / len(vehicle_ids))
        
        total_time = 0.0
        feasible = True
        
        for i, v_id in enumerate(vehicle_ids):
            chunk = task_ids[i*chunk_size : (i+1)*chunk_size]
            if not chunk: continue
            
            # 简单的序列：按时间窗开始时间排序
            chunk.sort(key=lambda t: self.tasks[t]['r_start'])
            
            ok, _, ttime, _, _, _ = self.compute_sequence_metrics(chunk, v_id)
            if ok:
                total_time += ttime
            else:
                feasible = False; break
        
        if feasible:
            return total_time
        return float('inf')

    def solve(self):
        """
        主求解逻辑 (Branch & Bound 优化版)
        """
        task_ids = list(self.tasks.keys())
        vehicle_ids = list(self.vehicles.keys())
        
        best_solution = None
        
        # 1. 获取初始上限 (Greedy)
        best_total_time = self._greedy_solve()
        logging.info(f"Greedy Initial Upper Bound: {best_total_time}")
        
        start_time = time.time()
        LIMIT_SECONDS = 8.0 
        
        # 2. 任务分配循环
        assignment_iter = itertools.product(range(len(vehicle_ids)), repeat=len(task_ids))
        
        for assign in assignment_iter:
            if time.time() - start_time > LIMIT_SECONDS:
                logging.warning("Scheduling timeout reached, returning best found.")
                break
                
            groups = {v: [] for v in vehicle_ids}
            for t_id, v_idx in zip(task_ids, assign):
                groups[vehicle_ids[v_idx]].append(t_id)

            perm_lists = []
            for v in vehicle_ids:
                if not groups[v]:
                    perm_lists.append([()])
                else:
                    # 优化：如果任务数 > 5，全排列太慢，这里可以进一步限制
                    # 比如只取按时间窗排序后的几个邻域变种
                    perm_lists.append(list(itertools.permutations(groups[v])))
            
            for prod in itertools.product(*perm_lists):
                current_total_time = 0.0
                feasible = True
                current_sol = {}
                
                # 逐个车辆计算
                for v_id, seq in zip(vehicle_ids, prod):
                    # 剪枝：如果当前累积时间已经超过最优解，停止计算剩余车辆
                    if current_total_time >= best_total_time:
                        feasible = False; break
                    
                    # 将剩余的时间配额传给 compute_sequence_metrics 进行内部剪枝
                    time_budget = best_total_time - current_total_time
                    ok, depot, ttime, energy, max_p, timeline = self.compute_sequence_metrics(seq, v_id, upper_bound=time_budget)
                    
                    if not ok:
                        feasible = False; break
                    
                    current_total_time += ttime
                    current_sol[v_id] = {
                        "seq": seq, "depot": depot, "time": ttime, 
                        "energy": energy, "timeline": timeline
                    }
                
                if feasible:
                    if current_total_time < best_total_time:
                        best_total_time = current_total_time
                        best_solution = current_sol
                        logging.info(f"New Best Solution found: {best_total_time:.2f}h")

        return best_solution


def run_schedule(data):
    """
    API 入口函数
    data = { "tasks": [], "vehicles": [], "depots": [] }
    """
    try:
        # 1. 初始化调度器
        scheduler = Scheduler(data['depots'], data['tasks'], data['vehicles'])
        
        # 2. 构建路网矩阵 (高耗时操作，已并发优化)
        logging.info("Building travel matrix via Gaode API...")
        scheduler.build_travel_matrix()
        
        # 3. 运行算法
        logging.info("Solving schedule...")
        solution = scheduler.solve()
        
        if not solution:
            return {"status": "error", "message": "无法找到满足所有时间窗和电量约束的调度方案。请尝试增加车辆或调整任务时间。"}
        
        # 4. 格式化输出供前端渲染
        routes_output = []
        for v_id, info in solution.items():
            # 提取用于画线的完整坐标点
            full_path = []
            timeline = info['timeline']
            
            for event in timeline:
                if event['type'] == 'travel':
                    poly_str = event.get('polyline', '')
                    if poly_str:
                        # 高德 polyline 格式: "lng,lat;lng,lat"
                        coords_str = poly_str.split(';')
                        for c in coords_str:
                            if ',' in c:
                                lng, lat = map(float, c.split(','))
                                full_path.append([lng, lat])
            
            routes_output.append({
                "vehicle_id": v_id,
                "depot": info['depot'],
                "tasks": info['seq'],
                "timeline": timeline,
                "path": full_path, # [[lng,lat], ...]
                "stats": {
                    "total_time": info['time'],
                    "total_energy": info['energy']
                }
            })
            
        return {"status": "success", "routes": routes_output}

    except Exception as e:
        logging.exception("Scheduling failed")
        return {"status": "error", "message": str(e)}