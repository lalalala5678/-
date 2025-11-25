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

    def compute_sequence_metrics(self, seq, v_id):
        """
        评估某辆车执行某个任务序列的可行性和成本 (核心逻辑移植自 v9)
        Returns: (feasible, depot_used, total_time, energy_sum, max_power, timeline)
        """
        if not seq:
            return True, None, 0.0, 0.0, 0.0, []

        m = len(seq)
        best_overall = None 

        # 尝试从每一个车库出发 (通常只有一个 Depot，但逻辑支持多个)
        for d_id in self.depots:
            
            # 内部递归函数：将序列切分为多次往返 (Trip)
            # 每次 Trip: Depot -> Task1 -> Task2 ... -> Depot
            def try_from(i, current_time):
                if i >= m:
                    return True, 0.0, 0.0, 0.0, [], current_time

                best_local = None

                # 尝试构建一个 Trip，包含 seq[i] 到 seq[j]
                for j in range(i, m):
                    subseq = seq[i:j+1]
                    first = subseq[0]
                    last = subseq[-1]

                    # 1. 从车库出发去第一个任务
                    travel_time_d_1 = self._get_travel_time(d_id, first)
                    
                    # 最早出发时间 & 实际出发时间
                    earliest_depart = max(0.0, self.tasks[first]['r_start'] - travel_time_d_1)
                    depart_time = max(current_time, earliest_depart)
                    arrival_first = depart_time + travel_time_d_1
                    
                    # 硬时间窗约束：必须在任务开始前或准点到达
                    if arrival_first - self.tasks[first]['r_start'] > 1e-5:
                        continue 

                    # 构建 Timeline 事件
                    timeline_trip = []
                    timeline_trip.append({
                        "type": "travel", "from": d_id, "to": first, 
                        "start": depart_time, "end": arrival_first,
                        "polyline": self.polylines.get((d_id, first), "")
                    })

                    # 如果早到，原地等待
                    if arrival_first < self.tasks[first]['r_start'] - 1e-5:
                        timeline_trip.append({"type": "idle_task", "at": first, "start": arrival_first, "end": self.tasks[first]['r_start']})

                    # 执行任务
                    timeline_trip.append({"type": "work", "task": first, "start": self.tasks[first]['r_start'], "end": self.tasks[first]['r_end']})

                    cur_time = self.tasks[first]['r_end']
                    prev = first
                    feasible_trip = True

                    # 2. Trip 内部：任务间移动
                    for nxt in subseq[1:]:
                        travel_t = self._get_travel_time(prev, nxt)
                        arrive = cur_time + travel_t
                        
                        # 时间窗检查
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
                    
                    trip_duration = return_time - depart_time

                    # 4. 车辆能力约束校验 (功率 & 能量)
                    trip_energy = sum(self.tasks[t]['p'] * self.tasks[t]['duration'] for t in subseq)
                    trip_max_power = max(self.tasks[t]['p'] for t in subseq)

                    veh = self.vehicles[v_id]
                    if trip_max_power > veh['P'] + 1e-5 or trip_energy > veh['E'] + 1e-5:
                        continue

                    # 5. 递归：处理剩余任务 seq[j+1:]
                    ok_next, tot_next, energy_next, maxp_next, timeline_next, final_return = try_from(j+1, return_time)
                    if not ok_next:
                        continue

                    # 合并 Timeline
                    merged_timeline = list(timeline_trip)
                    if timeline_next:
                        # 如果下一趟 Trip 开始时间晚于当前返回时间，中间是在车库等待
                        first_next = timeline_next[0]
                        next_depart = first_next.get("start", None)
                        if next_depart is not None and next_depart - return_time > 1e-5:
                            merged_timeline.append({"type": "idle_depot", "at": d_id, "start": return_time, "end": next_depart})
                    merged_timeline.extend(timeline_next)

                    total_time_candidate = trip_duration + tot_next
                    energy_sum_candidate = trip_energy + energy_next
                    max_power_candidate = max(trip_max_power, maxp_next)

                    if best_local is None or total_time_candidate < best_local[0]:
                        best_local = (total_time_candidate, energy_sum_candidate, max_power_candidate, merged_timeline, final_return)

                if best_local is None:
                    return False, None, None, None, None, None
                return True, best_local[0], best_local[1], best_local[2], best_local[3], best_local[4]

            # 启动递归
            ok, tot_time, energy_sum, max_power, timeline_list, final_return_time = try_from(0, 0.0)
            if not ok:
                continue
            if best_overall is None or tot_time < best_overall[0]:
                best_overall = (tot_time, energy_sum, max_power, timeline_list, d_id)

        if best_overall is None:
            return False, None, None, None, None, None

        total_time, energy_sum, max_power, timeline, depot_used = best_overall
        return True, depot_used, total_time, energy_sum, max_power, timeline

    def solve(self):
        """
        主求解逻辑
        使用全排列 (Brute Force) 搜索最优解。
        适用于小规模任务 (N <= 8)。
        """
        task_ids = list(self.tasks.keys())
        vehicle_ids = list(self.vehicles.keys())
        
        best_solution = None
        best_total_time = float('inf')
        
        # 安全限制：防止计算超时
        start_time = time.time()
        LIMIT_SECONDS = 8.0 
        
        # 1. 任务分配循环：遍历所有可能的“任务-车辆”分配方案
        # 笛卡尔积: (车辆1, 车辆1, ...), (车辆1, 车辆2, ...)
        assignment_iter = itertools.product(range(len(vehicle_ids)), repeat=len(task_ids))
        
        for assign in assignment_iter:
            if time.time() - start_time > LIMIT_SECONDS:
                logging.warning("Scheduling timeout reached, returning best found.")
                break
                
            # 构建分组：{ 'V1': ['T1', 'T2'], 'V2': ['T3'] }
            groups = {v: [] for v in vehicle_ids}
            for t_id, v_idx in zip(task_ids, assign):
                groups[vehicle_ids[v_idx]].append(t_id)

            # 2. 序列优化循环：对每辆车的任务生成全排列
            perm_lists = []
            for v in vehicle_ids:
                if not groups[v]:
                    perm_lists.append([()])
                else:
                    perm_lists.append(list(itertools.permutations(groups[v])))
            
            # 组合各车的排列
            for prod in itertools.product(*perm_lists):
                total_time = 0.0
                feasible = True
                current_sol = {}
                
                for v_id, seq in zip(vehicle_ids, prod):
                    seq = list(seq)
                    ok, depot, ttime, energy, max_p, timeline = self.compute_sequence_metrics(seq, v_id)
                    if not ok:
                        feasible = False
                        break
                    total_time += ttime
                    current_sol[v_id] = {
                        "seq": seq, 
                        "depot": depot, 
                        "time": ttime, 
                        "energy": energy, 
                        "timeline": timeline
                    }
                
                if feasible:
                    if total_time < best_total_time:
                        best_total_time = total_time
                        best_solution = current_sol

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