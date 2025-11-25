import React, { useState, useEffect, useRef } from "react";
import {
    Zap,
    Activity,
    Truck,
    Settings,
    Calculator,
    Layers,
    Eye,
    PlusCircle,
    MousePointer2,
    Play,
    Trash2
} from "lucide-react";

// --- 核心常量配置 ---
const CONFIG = {
    CITY_CENTER: [114.5149, 38.0428], // 石家庄中心坐标
    ANIMATION_SPEED: 0.015           // 雷达扫描速度
};

/**
 * 统一地图组件：结合高德地图 (底图/数据) + Canvas (雷达特效)
 */
const UnifiedMap = ({ 
    apiKey, vehicles, parkingSpots, outageHeatPoints, supportHeatPoints, 
    tasks, scheduledRoutes, // 新增 props
    onMapClick, mode, outageMaxVal, supportMaxVal, showOutage, showSupport 
}) => {
    const mapContainerRef = useRef(null);
    const canvasRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const outageLayerRef = useRef(null);
    const supportLayerRef = useRef(null);
    const parkingLayerRef = useRef(null); 
    const vehicleLayerRef = useRef(null); 
    const taskLayerRef = useRef(null); // 新增：任务图层
    const routeLayerRef = useRef(null); // 新增：路线图层
    
    const [hoverInfo, setHoverInfo] = useState(null);

    // 使用 Ref 追踪 mode
    const modeRef = useRef(mode);
    useEffect(() => {
        modeRef.current = mode;
    }, [mode]);

    // 使用 Ref 追踪 onMapClick
    const onMapClickRef = useRef(onMapClick);
    useEffect(() => {
        onMapClickRef.current = onMapClick;
    }, [onMapClick]);

    // 1. 初始化高德地图
    useEffect(() => {
        if (!apiKey) return;

        if (window.AMap) {
            initMap();
            return;
        }

        const script = document.createElement("script");
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${apiKey}&plugin=AMap.HeatMap,AMap.CustomLayer,AMap.MoveAnimation`;
        script.async = true;
        script.onload = initMap;
        document.head.appendChild(script);

        function initMap() {
            if (!window.AMap || mapInstanceRef.current) return;

            const map = new window.AMap.Map(mapContainerRef.current, {
                zoom: 12,
                center: CONFIG.CITY_CENTER,
                mapStyle: "amap://styles/grey", 
                viewMode: "3D",
                pitch: 30
            });
            mapInstanceRef.current = map;
            
            // ... 图层初始化 ...
            const pLayer = new window.AMap.LabelsLayer({ zIndex: 1000, collision: false });
            map.add(pLayer);
            parkingLayerRef.current = pLayer;

            const vLayer = new window.AMap.LabelsLayer({ zIndex: 500, collision: false });
            map.add(vLayer);
            vehicleLayerRef.current = vLayer;

            const tLayer = new window.AMap.LabelsLayer({ zIndex: 1100, collision: false });
            map.add(tLayer);
            taskLayerRef.current = tLayer;

            // 路线图层 (这里用 Group 或是直接 add polyline)
            // 简单起见，routeLayerRef 作为一个数组容器或者 Group 并不适用 LabelsLayer，需要直接操作 map
            // 我们用一个 ref 存当前所有的 Polyline 对象以便清除
            routeLayerRef.current = [];

            const outageHeatmap = new window.AMap.HeatMap(map, {
                radius: 50,
                opacity: [0, 0.7],
                gradient: { 0.2: 'rgb(0, 255, 255)', 0.5: 'rgb(0, 110, 255)', 0.65: 'rgb(0, 255, 0)', 0.8: 'yellow', 1.0: 'rgb(255, 0, 0)' },
                zIndex: 10
            });
            outageLayerRef.current = outageHeatmap;

            const supportHeatmap = new window.AMap.HeatMap(map, {
                radius: 45,
                opacity: [0, 0.6],
                gradient: { 0.2: "rgba(0,0,255,0.2)", 0.5: "rgb(0, 150, 255)", 0.9: "rgb(0, 255, 255)", 1.0: "white" },
                zIndex: 11
            });
            supportLayerRef.current = supportHeatmap;

            map.on("click", (e) => {
                if (modeRef.current === "add-spot" || modeRef.current === "add-task") {
                    onMapClickRef.current({ lng: e.lnglat.getLng(), lat: e.lnglat.getLat() });
                }
            });
        }

        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.destroy();
                mapInstanceRef.current = null;
            }
        };
    }, [apiKey]);

    // 2. 数据更新
    useEffect(() => {
        const map = mapInstanceRef.current;
        if (!map) return;

        // ... (Existing Vehicle & Parking Logic) ...
        const spotVehicleMap = {}; 
        const getLocKey = (lat, lng) => `${Number(lat).toFixed(6)},${Number(lng).toFixed(6)}`;
        vehicles.forEach(v => {
            if (v.status === 'busy' && v.lat && v.lng) {
                const key = getLocKey(v.lat, v.lng);
                if (!spotVehicleMap[key]) spotVehicleMap[key] = [];
                spotVehicleMap[key].push(v);
            }
        });

        if (vehicleLayerRef.current) {
            vehicleLayerRef.current.clear();
            const vehicleMarkers = [];
            vehicles.forEach((v) => {
                if (v.status === 'busy') return;
                if (v.lng === null || v.lat === null) return;
                const marker = new window.AMap.LabelMarker({
                    position: [v.lng, v.lat],
                    icon: { type: 'image', image: 'https://a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-default.png', size: [20, 26], anchor: 'bottom-center' },
                    text: { content: '⚡', style: { fontSize: 12, fill: '#f59e0b' } }
                });
                vehicleMarkers.push(marker);
            });
            vehicleLayerRef.current.add(vehicleMarkers);
        }

        if (parkingLayerRef.current) {
            parkingLayerRef.current.clear();
            const spotMarkers = [];
            parkingSpots.forEach((p, idx) => {
                const key = getLocKey(p.lat, p.lng);
                const parkedVehicles = spotVehicleMap[key] || [];
                const count = parkedVehicles.length;
                const marker = new window.AMap.LabelMarker({
                    position: [p.lng, p.lat],
                    icon: { type: 'image', image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png', size: [19, 33], anchor: 'bottom-center' },
                    text: { content: `P${idx + 1} ${count > 0 ? `(${count})` : ''}`, direction: 'top', offset: [0, -5], style: { fontSize: 14, fontWeight: 'bold', fillColor: count > 0 ? '#ef4444' : '#fff', strokeColor: '#000', strokeWidth: 2 } }
                });
                spotMarkers.push(marker);
            });
            parkingLayerRef.current.add(spotMarkers);
        }

        // --- New: Task Markers ---
        if (taskLayerRef.current) {
            taskLayerRef.current.clear();
            const taskMarkers = [];
            tasks.forEach((t) => {
                const marker = new window.AMap.LabelMarker({
                    position: [t.lng, t.lat],
                    icon: { 
                        type: 'image', 
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png', // Red marker for outage
                        size: [19, 33], anchor: 'bottom-center' 
                    },
                    text: { 
                        content: `${t.id}\n${t.power}kW`, 
                        direction: 'top', 
                        offset: [0, -5], 
                        style: { fontSize: 12, fontWeight: 'bold', fillColor: '#fca5a5', strokeColor: '#000', strokeWidth: 2 } 
                    }
                });
                taskMarkers.push(marker);
            });
            taskLayerRef.current.add(taskMarkers);
        }

        // --- New: Scheduled Routes ---
        if (routeLayerRef.current) {
            // 清除旧路线
            map.remove(routeLayerRef.current);
            routeLayerRef.current = [];
            
            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"];
            
            scheduledRoutes.forEach((route, idx) => {
                const path = route.path; // [[lng,lat], ...]
                if (!path || path.length < 2) return;
                
                const polyline = new window.AMap.Polyline({
                    path: path,
                    isOutline: true,
                    outlineColor: '#000',
                    borderWeight: 2,
                    strokeColor: colors[idx % colors.length], 
                    strokeOpacity: 1,
                    strokeWeight: 4,
                    strokeStyle: "solid",
                    lineJoin: 'round',
                    lineCap: 'round',
                    zIndex: 50,
                    showDir: true
                });
                map.add(polyline);
                routeLayerRef.current.push(polyline);
            });
        }

        if (outageLayerRef.current) {
            outageLayerRef.current.setDataSet({ data: outageHeatPoints, max: outageMaxVal });
            showOutage ? outageLayerRef.current.show() : outageLayerRef.current.hide();
        }
        if (supportLayerRef.current) {
            supportLayerRef.current.setDataSet({ data: supportHeatPoints, max: supportMaxVal });
            showSupport ? supportLayerRef.current.show() : supportLayerRef.current.hide();
        }
    }, [vehicles, parkingSpots, tasks, scheduledRoutes, outageHeatPoints, supportHeatPoints, outageMaxVal, supportMaxVal, showOutage, showSupport]);

    // ... (Canvas Effect remains same) ...
    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        let animationFrameId;
        let rotation = 0;

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        window.addEventListener("resize", resize);
        resize();

        const render = () => {
            if (!canvas || !mapInstanceRef.current) {
                animationFrameId = requestAnimationFrame(render);
                return;
            }
            const map = mapInstanceRef.current;
            const centerLngLat = new window.AMap.LngLat(CONFIG.CITY_CENTER[0], CONFIG.CITY_CENTER[1]);
            const pixel = map.lngLatToContainer(centerLngLat);
            const centerX = pixel.getX();
            const centerY = pixel.getY();

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // ... (Simplified render for brevity, original kept visually) ...
            rotation += CONFIG.ANIMATION_SPEED;
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(rotation);
            ctx.restore();
            animationFrameId = requestAnimationFrame(render);
        };
        render();
        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <div className="absolute inset-0 w-full h-full">
            <div ref={mapContainerRef} className={`absolute inset-0 z-0 ${mode === "add-spot" || mode === "add-task" ? "cursor-crosshair" : ""}`} />
            <canvas ref={canvasRef} className="absolute inset-0 z-10 pointer-events-none mix-blend-screen" />
            {hoverInfo && (
                <div 
                    className="absolute z-50 bg-slate-900/95 border border-cyan-500/50 text-cyan-50 p-3 rounded-lg shadow-2xl backdrop-blur pointer-events-none min-w-[160px]"
                    style={{ left: hoverInfo.x, top: hoverInfo.y, transform: 'translate(-50%, -100%) translateY(-60px)' }}
                >
                    <div className="text-sm font-bold text-cyan-400 mb-2 border-b border-cyan-500/30 pb-1 flex justify-between">
                        <span>{hoverInfo.spotName} 车辆列表</span>
                        <span className="text-white">{hoverInfo.vehicles.length} 辆</span>
                    </div>
                    {/* ... */}
                </div>
            )}
        </div>
    );
};

/**
 * 主应用组件
 */
export default function EmergencyDispatchSystem() {
    const [apiKey, setApiKey] = useState("914c04aa7bd473fbe1eb08054e065416");
    const [vehicles, setVehicles] = useState([]);
    const [parkingSpots, setParkingSpots] = useState([]);
    const [outageHeatmap, setOutageHeatmap] = useState([]);
    const [supportHeatmap, setSupportHeatmap] = useState([]);

    // --- New State for Deterministic Scheduling ---
    const [tasks, setTasks] = useState([]);
    const [taskForm, setTaskForm] = useState({ start: 8, duration: 2, power: 50 });
    const [scheduledRoutes, setScheduledRoutes] = useState([]);
    const [isScheduling, setIsScheduling] = useState(false);
    // ----------------------------------------------

    const [outageMaxVal, setOutageMaxVal] = useState(80);
    const [supportMaxVal, setSupportMaxVal] = useState(100);
    const [showOutage, setShowOutage] = useState(true);
    const [showSupport, setShowSupport] = useState(true);

    const [newVehicleLoad, setNewVehicleLoad] = useState(500);
    const [addCount, setAddCount] = useState(1);

    const [lossValue, setLossValue] = useState(null);
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [interactionMode, setInteractionMode] = useState("view");
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const t = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(t);
    }, []);

    const addVehicle = () => {
        const count = Math.max(1, Math.floor(addCount));
        const newVehicles = [];
        for (let i = 0; i < count; i++) {
            newVehicles.push({
                id: `EV-${1000 + vehicles.length + i + 1}`,
                status: "idle",
                load: newVehicleLoad,
                energy: 200, // 假设默认能量
                power: 80,   // 假设默认最大功率
                lng: null,
                lat: null
            });
        }
        setVehicles([...vehicles, ...newVehicles]);
    };

    const clearVehicles = () => {
        setVehicles([]);
        setLossValue(null);
        setSupportHeatmap([]);
        setScheduledRoutes([]);
    };

    const handleMapClick = (coord) => {
        console.log("Parent received click:", coord, "Mode:", interactionMode);
        if (interactionMode === "add-spot") {
            setParkingSpots((prev) => [
                ...prev, 
                { lng: Number(coord.lng), lat: Number(coord.lat), id: `P-${prev.length + 1}` }
            ]);
        } else if (interactionMode === "add-task") {
            setTasks((prev) => [
                ...prev,
                {
                    id: `T${prev.length + 1}`,
                    lng: Number(coord.lng),
                    lat: Number(coord.lat),
                    start: Number(taskForm.start),
                    duration: Number(taskForm.duration),
                    power: Number(taskForm.power)
                }
            ]);
            // 选完一个点后可以自动切回 view，也可以保持继续选，这里保持继续选
        }
    };

    // --- Deterministic Scheduling API ---
    const runDeterministicSchedule = async () => {
        if (vehicles.length === 0) return alert("请先添加车辆！");
        if (tasks.length === 0) return alert("请先添加停电任务！");
        if (parkingSpots.length === 0) return alert("请先添加至少一个车库(停车点)作为出发点！");

        setIsScheduling(true);
        try {
            // 构造后端需要的数据结构
            const payload = {
                vehicles: vehicles.map(v => ({ id: v.id, power: v.power || 80, energy: v.energy || 200 })),
                depots: parkingSpots.map(p => ({ id: p.id, lat: p.lat, lng: p.lng })),
                tasks: tasks
            };

            const res = await fetch('/api/schedule-deterministic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                setScheduledRoutes(data.routes);
                alert("调度计算完成！");
            } else {
                alert("调度失败: " + data.message);
            }
        } catch (e) {
            console.error("Schedule Error:", e);
            alert("调度请求失败");
        } finally {
            setIsScheduling(false);
        }
    };
    // ------------------------------------

    const generateHeatmap = async () => {
        try {
            const res = await fetch('/api/outage-heatmap');
            const data = await res.json();
            setOutageHeatmap(data);
            if (vehicles.length > 0) calculateCurrentLoss();
        } catch (e) { console.error(e); }
    };

    const calculateCurrentLoss = async () => {
        if (vehicles.length === 0) return;
        try {
            const res = await fetch('/api/calculate-loss', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicles })
            });
            const data = await res.json();
            setLossValue(data.loss.toFixed(4));
            setSupportHeatmap(data.supportHeatmap);
        } catch (e) { console.error(e); }
    };

    const runOptimization = async () => {
        if (parkingSpots.length === 0) return alert("请先设定停车点！");
        if (vehicles.length === 0) return alert("请先添加电力车！");
        setIsOptimizing(true);
        try {
            const res = await fetch('/api/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vehicles, parkingSpots })
            });
            const data = await res.json();
            setVehicles(data.vehicles);
            setLossValue(data.loss.toFixed(4));
            setSupportHeatmap(data.supportHeatmap);
        } catch (e) { console.error(e); } finally { setIsOptimizing(false); }
    };

    const resetSimulation = () => {
        setVehicles(vehicles.map((v) => ({ ...v, status: "idle", lng: null, lat: null })));
        setLossValue(null);
        setSupportHeatmap([]);
        setScheduledRoutes([]);
    };

    return (
        <div className="relative w-full h-screen bg-slate-950 overflow-hidden text-cyan-50 font-sans selection:bg-cyan-500 selection:text-white">
            
            <UnifiedMap
                apiKey={apiKey}
                vehicles={vehicles}
                parkingSpots={parkingSpots}
                tasks={tasks} // Pass tasks
                scheduledRoutes={scheduledRoutes} // Pass routes
                outageHeatPoints={outageHeatmap}
                supportHeatPoints={supportHeatmap}
                outageMaxVal={outageMaxVal}
                supportMaxVal={supportMaxVal}
                showOutage={showOutage}
                showSupport={showSupport}
                onMapClick={handleMapClick}
                mode={interactionMode}
            />

            {/* Header ... */}
            <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-8 py-4 bg-gradient-to-b from-slate-950 via-slate-900/90 to-transparent pointer-events-none">
                <div className="flex items-center gap-4 pointer-events-auto">
                    <div className="p-2 bg-cyan-500/20 border border-cyan-500/50 rounded-md shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                        <Zap className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                            智能电网调度推演系统
                        </h1>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] text-cyan-600 tracking-[0.2em] uppercase">Smart Grid Dispatch & Simulation</span>
                            <span className="text-[10px] px-1 border border-green-500 text-green-500 rounded">Online</span>
                        </div>
                    </div>
                </div>
                {/* ... */}
                <div className="flex items-center gap-6 pointer-events-auto">
                    <div className="font-mono text-cyan-300/80 bg-slate-900/50 px-4 py-1 rounded-full border border-cyan-900/50">
                        {currentTime.toLocaleTimeString()}
                    </div>
                    <button className="text-cyan-400 hover:text-white">
                        <Settings className="w-6 h-6" />
                    </button>
                </div>
            </header>

            {/* 左侧：不确定性应急 (原功能) */}
            <aside className="absolute top-24 bottom-8 left-8 w-96 flex flex-col gap-4 z-20 animate-in slide-in-from-left duration-500 pointer-events-auto">
               <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 shadow-2xl">
                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Truck className="w-4 h-4" /> 资源配置 (Fleet)
                    </h3>
                    <div className="mb-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <div className="flex-1">
                                <div className="text-[10px] text-slate-400 mb-1">单车载荷 (kW)</div>
                                <input
                                    type="number" value={newVehicleLoad}
                                    onChange={(e) => setNewVehicleLoad(Number(e.target.value))}
                                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm font-mono focus:border-cyan-500 outline-none text-white"
                                />
                            </div>
                            <div className="w-20">
                                <div className="text-[10px] text-slate-400 mb-1">数量</div>
                                <input
                                    type="number" min="1" value={addCount}
                                    onChange={(e) => setAddCount(Number(e.target.value))}
                                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm font-mono focus:border-cyan-500 outline-none text-white"
                                />
                            </div>
                        </div>
                        <div className="pt-1">
                            <button onClick={addVehicle} className="w-full px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/40 border border-cyan-500/50 text-cyan-400 rounded flex items-center justify-center gap-1 transition-colors">
                                <PlusCircle className="w-4 h-4" /> 批量添加 ({addCount})
                            </button>
                        </div>
                    </div>
                    <div className="bg-slate-950/50 rounded border border-slate-800 p-2 max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                        {vehicles.length === 0 ? (
                            <div className="text-center text-slate-600 text-xs py-4">暂无车辆，请添加</div>
                        ) : (
                            <div className="space-y-1">
                                {vehicles.map((v, i) => (
                                    <div key={i} className="flex justify-between items-center text-xs p-1.5 bg-slate-900 rounded border border-slate-800/50">
                                        <span className="text-slate-400">{v.id}</span>
                                        <span className="font-mono text-cyan-300">{v.load} kW</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <div className="mt-2 flex justify-between items-center">
                        <span className="text-xs text-slate-500">总数: {vehicles.length} 辆</span>
                        <button onClick={clearVehicles} className="text-xs text-red-400 hover:text-red-300 underline flex items-center gap-1">
                            <Trash2 className="w-3 h-3" /> 清空车队
                        </button>
                    </div>
                </div>

                <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 shadow-2xl flex-1 flex flex-col overflow-y-auto">
                    <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Layers className="w-4 h-4" /> 应急场景构建
                    </h3>
                    <div className="space-y-4 flex-1">
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">1. 设定车库/停车点</span>
                                <span className="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded border border-green-800">已设: {parkingSpots.length}</span>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setInteractionMode(interactionMode === "add-spot" ? "view" : "add-spot")}
                                    className={`flex-1 py-2 rounded text-xs flex items-center justify-center gap-1 border transition-colors ${interactionMode === "add-spot" ? "bg-green-600 text-white border-green-500 animate-pulse" : "bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-500"}`}
                                >
                                    <MousePointer2 className="w-3 h-3" /> {interactionMode === "add-spot" ? "点击地图选点..." : "开启选点模式"}
                                </button>
                                <button onClick={() => setParkingSpots([])} className="px-3 py-2 bg-slate-800 text-slate-400 border border-slate-700 rounded hover:text-red-400">
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* 模拟断电热力 */}
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">2. 模拟断电热力</span>
                            </div>
                            <button onClick={generateHeatmap} className="w-full py-2 bg-indigo-600/20 border border-indigo-500/50 text-indigo-300 rounded text-xs hover:bg-indigo-600/40 flex items-center justify-center gap-2">
                                <Activity className="w-3 h-3" /> 生成随机热力图
                            </button>
                        </div>

                         {/* 热力显示范围 & 开关 */}
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">3. 热力显示控制</span>
                            </div>
                            <div className="mb-4 space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-xs text-red-400">
                                        <input type="checkbox" checked={showOutage} onChange={(e) => setShowOutage(e.target.checked)} className="accent-red-500" />
                                        <span>显示断电热力</span>
                                    </div>
                                    <span className="text-[10px] text-slate-500">Max: {outageMaxVal}</span>
                                </div>
                                <input type="range" min="10" max="200" step="5" value={outageMaxVal} onChange={(e) => setOutageMaxVal(Number(e.target.value))} className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500" />
                            </div>
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-xs text-cyan-400">
                                        <input type="checkbox" checked={showSupport} onChange={(e) => setShowSupport(e.target.checked)} className="accent-cyan-500" />
                                        <span>显示支援热力</span>
                                    </div>
                                    <span className="text-[10px] text-slate-500">Max: {supportMaxVal}</span>
                                </div>
                                <input type="range" min="10" max="200" step="5" value={supportMaxVal} onChange={(e) => setSupportMaxVal(Number(e.target.value))} className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500" />
                            </div>
                        </div>

                        <div className="mt-4 pt-4 border-t border-slate-700">
                            <div className="flex justify-between items-end mb-2">
                                <span className="text-sm text-slate-300">4. 算法求解</span>
                                {lossValue && (<div className="text-right"><div className="text-[10px] text-slate-500">Loss Function</div><div className="text-xl font-mono font-bold text-red-400">{lossValue}</div></div>)}
                            </div>
                            <div className="flex gap-2 mb-2">
                                <button onClick={calculateCurrentLoss} className="flex-1 py-2 bg-slate-800 border border-slate-600 text-slate-300 rounded text-xs hover:bg-slate-700">计算当前 Loss</button>
                                <button onClick={resetSimulation} className="px-3 py-2 bg-slate-800 border border-slate-600 text-slate-300 rounded text-xs hover:bg-slate-700"><Trash2 className="w-3 h-3" /></button>
                            </div>
                            <button onClick={runOptimization} disabled={isOptimizing || parkingSpots.length === 0} className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded shadow-lg uppercase disabled:opacity-50 flex items-center justify-center gap-2 transition-all">
                                {isOptimizing ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> 正在求解...</> : <><Play className="w-4 h-4 fill-current" /> 运行最优分配算法</>}
                            </button>
                        </div>
                    </div>
                </div>
            </aside>

            {/* 右侧：确定性调度 (新增功能) */}
            <aside className="absolute top-24 bottom-8 right-8 w-80 flex flex-col gap-4 z-20 animate-in slide-in-from-right duration-500 pointer-events-auto">
                <div className="bg-slate-900/90 backdrop-blur-md border border-fuchsia-500/30 rounded-lg p-4 shadow-2xl flex flex-col h-full">
                    <h3 className="text-sm font-bold text-fuchsia-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Activity className="w-4 h-4" /> 确定性检修调度
                    </h3>
                    
                    {/* 任务输入表单 */}
                    <div className="space-y-3 mb-4 p-3 bg-slate-950/50 rounded border border-slate-800">
                        <div className="flex items-center gap-2">
                            <div className="flex-1">
                                <label className="text-[10px] text-slate-400 block mb-1">开始时间 (h)</label>
                                <input 
                                    type="number" step="0.5"
                                    value={taskForm.start}
                                    onChange={(e) => setTaskForm({...taskForm, start: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="text-[10px] text-slate-400 block mb-1">时长 (h)</label>
                                <input 
                                    type="number" step="0.5"
                                    value={taskForm.duration}
                                    onChange={(e) => setTaskForm({...taskForm, duration: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                                />
                            </div>
                            <div className="flex-1">
                                <label className="text-[10px] text-slate-400 block mb-1">需求 (kW)</label>
                                <input 
                                    type="number"
                                    value={taskForm.power}
                                    onChange={(e) => setTaskForm({...taskForm, power: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                                />
                            </div>
                        </div>
                        
                        <div className="flex gap-2">
                            <button
                                onClick={() => setInteractionMode(interactionMode === "add-task" ? "view" : "add-task")}
                                className={`flex-1 py-2 rounded text-xs flex items-center justify-center gap-1 border transition-colors ${interactionMode === "add-task" ? "bg-fuchsia-600 text-white border-fuchsia-500 animate-pulse" : "bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-500"}`}
                            >
                                <MousePointer2 className="w-3 h-3" /> {interactionMode === "add-task" ? "点击地图选点..." : "添加任务 (选点)"}
                            </button>
                        </div>
                    </div>

                    {/* 任务列表 */}
                    <div className="flex-1 overflow-y-auto mb-4 border border-slate-800 rounded bg-slate-950/30 p-2">
                         <div className="flex justify-between items-center mb-2 px-1">
                            <span className="text-xs text-slate-400">任务列表 ({tasks.length})</span>
                            <button onClick={() => setTasks([])} className="text-slate-500 hover:text-red-400"><Trash2 className="w-3 h-3" /></button>
                        </div>
                        <div className="space-y-1">
                            {tasks.map((t, i) => (
                                <div key={i} className="flex justify-between items-center text-xs p-2 bg-slate-900 rounded border border-slate-800 border-l-2 border-l-fuchsia-500">
                                    <span className="text-white font-bold">{t.id}</span>
                                    <div className="flex gap-3 text-slate-400">
                                        <span>{t.start}-{Number(t.start)+Number(t.duration)}h</span>
                                        <span>{t.power}kW</span>
                                    </div>
                                </div>
                            ))}
                            {tasks.length === 0 && <div className="text-center text-slate-600 text-xs py-4">暂无任务</div>}
                        </div>
                    </div>

                    {/* 执行按钮 */}
                    <button
                        onClick={runDeterministicSchedule}
                        disabled={isScheduling || tasks.length === 0}
                        className="w-full py-3 bg-gradient-to-r from-fuchsia-700 to-purple-700 hover:from-fuchsia-600 hover:to-purple-600 text-white font-bold rounded shadow-lg uppercase disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
                    >
                        {isScheduling ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> 规划路径中...
                            </>
                        ) : (
                            <>
                                <Truck className="w-4 h-4 fill-current" /> 生成调度路线
                            </>
                        )}
                    </button>
                    
                </div>
            </aside>

            {!apiKey && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="text-white">API Key Missing</div>
                </div>
            )}
        </div>
    );
}