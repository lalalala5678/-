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
const UnifiedMap = ({ apiKey, vehicles, parkingSpots, outageHeatPoints, supportHeatPoints, onMapClick, mode, outageMaxVal, supportMaxVal, showOutage, showSupport }) => {
    const mapContainerRef = useRef(null);
    const canvasRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const outageLayerRef = useRef(null);
    const supportLayerRef = useRef(null);
    const parkingLayerRef = useRef(null); // 新增：停车点图层
    const vehicleLayerRef = useRef(null); // 新增：车辆图层
    
    const [hoverInfo, setHoverInfo] = useState(null);

    // 使用 Ref 追踪 mode，解决闭包旧值问题
    const modeRef = useRef(mode);
    useEffect(() => {
        modeRef.current = mode;
    }, [mode]);

    // 使用 Ref 追踪 onMapClick，解决闭包旧值问题
    const onMapClickRef = useRef(onMapClick);
    useEffect(() => {
        onMapClickRef.current = onMapClick;
    }, [onMapClick]);

    // 1. 初始化高德地图
    useEffect(() => {
        if (!apiKey) return;

        // 避免重复加载 SDK
        if (window.AMap) {
            initMap();
            return;
        }

        const script = document.createElement("script");
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${apiKey}&plugin=AMap.HeatMap,AMap.CustomLayer`;
        script.async = true;
        script.onload = initMap;
        document.head.appendChild(script);

        function initMap() {
            if (!window.AMap || mapInstanceRef.current) return;

            const map = new window.AMap.Map(mapContainerRef.current, {
                zoom: 12,
                center: CONFIG.CITY_CENTER,
                mapStyle: "amap://styles/grey", // 使用灰色主题
                viewMode: "3D",
                pitch: 30
            });
            mapInstanceRef.current = map;

            // --- 初始化图层 (类似热力图的逻辑) ---
            
            // 1. 停车点图层 (LabelsLayer)
            const pLayer = new window.AMap.LabelsLayer({
                zIndex: 1000,
                collision: false // 允许重叠
            });
            map.add(pLayer);
            parkingLayerRef.current = pLayer;

            // 2. 车辆图层 (LabelsLayer)
            const vLayer = new window.AMap.LabelsLayer({
                zIndex: 500,
                collision: false
            });
            map.add(vLayer);
            vehicleLayerRef.current = vLayer;

            // 3. 断电概率热力图
            const outageHeatmap = new window.AMap.HeatMap(map, {
                radius: 50,
                opacity: [0, 0.7],
                gradient: {
                    0.2: 'rgb(0, 255, 255)',
                    0.5: 'rgb(0, 110, 255)',
                    0.65: 'rgb(0, 255, 0)',
                    0.8: 'yellow',
                    1.0: 'rgb(255, 0, 0)'
                },
                zIndex: 10
            });
            outageLayerRef.current = outageHeatmap;

            // 4. 支援能力热力图
            const supportHeatmap = new window.AMap.HeatMap(map, {
                radius: 45,
                opacity: [0, 0.6],
                gradient: {
                    0.2: "rgba(0,0,255,0.2)",
                    0.5: "rgb(0, 150, 255)",
                    0.9: "rgb(0, 255, 255)",
                    1.0: "white"
                },
                zIndex: 11
            });
            supportLayerRef.current = supportHeatmap;

            // 事件绑定
            map.on("click", (e) => {
                console.log("Map Clicked!", modeRef.current, e.lnglat);
                if (modeRef.current === "add-spot") {
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

    // 2. 数据更新：标记点与热力图
    useEffect(() => {
        const map = mapInstanceRef.current;
        if (!map) return;

        // 注意：不再调用 map.clearMap()，而是分别清空图层
        // 这样可以避免不同类型覆盖物互相影响

        // 预计算每个停车点的车辆
        const spotVehicleMap = {}; // { "lat,lng": [vehicles] }
        const getLocKey = (lat, lng) => `${Number(lat).toFixed(6)},${Number(lng).toFixed(6)}`;

        vehicles.forEach(v => {
            if (v.status === 'busy' && v.lat && v.lng) {
                const key = getLocKey(v.lat, v.lng);
                if (!spotVehicleMap[key]) spotVehicleMap[key] = [];
                spotVehicleMap[key].push(v);
            }
        });

        // --- 更新车辆图层 ---
        if (vehicleLayerRef.current) {
            vehicleLayerRef.current.clear();
            const vehicleMarkers = [];
            vehicles.forEach((v) => {
                if (v.status === 'busy') return;
                if (v.lng === null || v.lat === null) return;
                
                const marker = new window.AMap.LabelMarker({
                    position: [v.lng, v.lat],
                    icon: {
                        type: 'image',
                        image: 'https://a.amap.com/jsapi_demos/static/demo-center/icons/poi-marker-default.png', // 暂用默认黄色小点替代
                        size: [20, 26],
                        anchor: 'bottom-center'
                    },
                    text: {
                        content: '⚡', // 简单的文字图标
                        style: { fontSize: 12, fill: '#f59e0b' }
                    }
                });
                vehicleMarkers.push(marker);
            });
            vehicleLayerRef.current.add(vehicleMarkers);
        }

        // --- 更新停车点图层 ---
        if (parkingLayerRef.current) {
            parkingLayerRef.current.clear();
            const spotMarkers = [];
            console.log("Updating LabelsLayer with Spots:", parkingSpots);

            parkingSpots.forEach((p, idx) => {
                const key = getLocKey(p.lat, p.lng);
                const parkedVehicles = spotVehicleMap[key] || [];
                const count = parkedVehicles.length;
                
                // 构造 LabelMarker
                // 使用纯文本/图形绘制，不依赖 DOM，性能极高且不会被样式覆盖
                const marker = new window.AMap.LabelMarker({
                    position: [p.lng, p.lat],
                    opacity: 1,
                    zIndex: 2000,
                    icon: {
                        type: 'image',
                        // 使用高德默认蓝色图标，或者自定义图片URL
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
                        size: [19, 33],
                        anchor: 'bottom-center'
                    },
                    text: {
                        // 动态生成文本内容
                        content: `P${idx + 1} ${count > 0 ? `(${count})` : ''}`,
                        direction: 'top',
                        offset: [0, -5],
                        style: {
                            fontSize: 14,
                            fontWeight: 'bold',
                            fillColor: count > 0 ? '#ef4444' : '#fff', // 有车红色，无车白色
                            strokeColor: '#000',
                            strokeWidth: 2
                        }
                    },
                    extData: {
                        spotName: `P${idx + 1}`,
                        vehicles: parkedVehicles
                    }
                });

                // 绑定交互 (LabelsLayer 的事件绑定略有不同)
                marker.on('mouseover', (e) => {
                    const data = e.target.getExtData();
                    if (data && data.vehicles.length > 0) {
                        // 获取屏幕坐标
                        const pixel = map.lngLatToContainer(e.lnglat);
                        setHoverInfo({
                            x: pixel.getX(),
                            y: pixel.getY(),
                            spotName: data.spotName,
                            vehicles: data.vehicles
                        });
                    }
                });
                marker.on('mouseout', () => {
                    setHoverInfo(null);
                });

                spotMarkers.push(marker);
            });
            parkingLayerRef.current.add(spotMarkers);
        }

        // 更新热力图
        if (outageLayerRef.current) {
            outageLayerRef.current.setDataSet({ data: outageHeatPoints, max: outageMaxVal });
            showOutage ? outageLayerRef.current.show() : outageLayerRef.current.hide();
        }
        if (supportLayerRef.current) {
            supportLayerRef.current.setDataSet({ data: supportHeatPoints, max: supportMaxVal });
            showSupport ? supportLayerRef.current.show() : supportLayerRef.current.hide();
        }
    }, [vehicles, parkingSpots, outageHeatPoints, supportHeatPoints, outageMaxVal, supportMaxVal, showOutage, showSupport]);

    // 3. Canvas 雷达扫描特效 ... (保持不变)
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

            // HUD
            ctx.strokeStyle = "rgba(14, 165, 233, 0.15)";
            ctx.lineWidth = 1;
            [100, 200, 300, 400, 600].forEach(r => {
                ctx.beginPath();
                ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
                ctx.stroke();
                ctx.fillStyle = "rgba(14, 165, 233, 0.5)";
                ctx.font = "10px monospace";
                ctx.fillText(`${r/20}km`, centerX + r + 2, centerY);
            });
            
            ctx.beginPath();
            ctx.moveTo(centerX - 800, centerY);
            ctx.lineTo(centerX + 800, centerY);
            ctx.moveTo(centerX, centerY - 800);
            ctx.lineTo(centerX, centerY + 800);
            ctx.stroke();

            // Radar
            rotation += CONFIG.ANIMATION_SPEED;
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(rotation);
            
            const scanGradient = ctx.createConicGradient(0, 0, 0);
            scanGradient.addColorStop(0, "rgba(14, 165, 233, 0)");
            scanGradient.addColorStop(0.8, "rgba(14, 165, 233, 0)");
            scanGradient.addColorStop(0.95, "rgba(14, 165, 233, 0.1)");
            scanGradient.addColorStop(1, "rgba(14, 165, 233, 0.3)"); 
            
            ctx.fillStyle = scanGradient;
            ctx.beginPath();
            const scanRadius = 600;
            ctx.moveTo(0, 0);
            ctx.arc(0, 0, scanRadius, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.strokeStyle = "rgba(14, 165, 233, 0.6)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(scanRadius, 0);
            ctx.stroke();
            
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
            <div ref={mapContainerRef} className={`absolute inset-0 z-0 ${mode === "add-spot" ? "cursor-crosshair" : ""}`} />
            <canvas ref={canvasRef} className="absolute inset-0 z-10 pointer-events-none mix-blend-screen" />
            {hoverInfo && (
                <div 
                    className="absolute z-50 bg-slate-900/95 border border-cyan-500/50 text-cyan-50 p-3 rounded-lg shadow-2xl backdrop-blur pointer-events-none min-w-[160px]"
                    style={{ 
                        left: hoverInfo.x, 
                        top: hoverInfo.y, 
                        transform: 'translate(-50%, -100%) translateY(-60px)' 
                    }}
                >
                    <div className="text-sm font-bold text-cyan-400 mb-2 border-b border-cyan-500/30 pb-1 flex justify-between">
                        <span>{hoverInfo.spotName} 车辆列表</span>
                        <span className="text-white">{hoverInfo.vehicles.length} 辆</span>
                    </div>
                    <div className="max-h-40 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-slate-700 pr-1">
                        {hoverInfo.vehicles.map((v, i) => (
                            <div key={i} className="flex justify-between items-center text-xs bg-slate-800/50 p-1 rounded">
                                <span className="text-slate-400">{v.id}</span>
                                <span className="font-mono text-yellow-400">{v.load}kW</span>
                            </div>
                        ))}
                    </div>
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

    const [outageMaxVal, setOutageMaxVal] = useState(80);
    const [supportMaxVal, setSupportMaxVal] = useState(100);
    
    // 新增：热力图开关状态
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

    // ... (车辆管理 addVehicle, clearVehicles, handleMapClick, API methods 保持不变) ...
    const addVehicle = () => {
        const count = Math.max(1, Math.floor(addCount));
        const newVehicles = [];
        for (let i = 0; i < count; i++) {
            newVehicles.push({
                id: `EV-${1000 + vehicles.length + i + 1}`,
                status: "idle",
                load: newVehicleLoad,
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
    };

    const handleMapClick = (coord) => {
        console.log("Parent received click:", coord, "Mode:", interactionMode);
        if (interactionMode === "add-spot") {
            setParkingSpots((prev) => [
                ...prev, 
                { 
                    lng: Number(coord.lng), 
                    lat: Number(coord.lat), 
                    id: `P-${prev.length + 1}` 
                }
            ]);
        }
    };

    // --- API 交互逻辑 ---

    const generateHeatmap = async () => {
        try {
            const res = await fetch('/api/outage-heatmap');
            const data = await res.json();
            setOutageHeatmap(data);
            if (vehicles.length > 0) {
               calculateCurrentLoss();
            }
        } catch (e) {
            console.error("API Error:", e);
            alert("获取热力图失败");
        }
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
        } catch (e) {
            console.error("API Error:", e);
        }
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
        } catch (e) {
            console.error("Optimization Error:", e);
            alert("优化算法调用失败");
        } finally {
            setIsOptimizing(false);
        }
    };

    const resetSimulation = () => {
        setVehicles(vehicles.map((v) => ({ ...v, status: "idle", lng: null, lat: null })));
        setLossValue(null);
        setSupportHeatmap([]);
    };

    return (
        <div className="relative w-full h-screen bg-slate-950 overflow-hidden text-cyan-50 font-sans selection:bg-cyan-500 selection:text-white">
            
            {/* 统一地图组件 */}
            <UnifiedMap
                apiKey={apiKey}
                vehicles={vehicles}
                parkingSpots={parkingSpots}
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
                <div className="bg-slate-900/50 backdrop-blur border border-cyan-500/20 rounded-full px-6 py-1 pointer-events-auto">
                    <span className="text-sm text-cyan-300 font-mono flex items-center gap-2">
                        <Calculator className="w-4 h-4" /> Python 混合计算模式
                    </span>
                </div>
                <div className="flex items-center gap-6 pointer-events-auto">
                    <div className="font-mono text-cyan-300/80 bg-slate-900/50 px-4 py-1 rounded-full border border-cyan-900/50">
                        {currentTime.toLocaleTimeString()}
                    </div>
                    <button className="text-cyan-400 hover:text-white">
                        <Settings className="w-6 h-6" />
                    </button>
                </div>
            </header>

            {/* 左侧控制面板 */}
            <aside className="absolute top-24 bottom-8 left-8 w-96 flex flex-col gap-4 z-20 animate-in slide-in-from-left duration-500 pointer-events-auto">
                {/* 1. 资源配置 */}
                <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 shadow-2xl">
                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Truck className="w-4 h-4" /> 资源配置 (Fleet)
                    </h3>
                    <div className="mb-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <div className="flex-1">
                                <div className="text-[10px] text-slate-400 mb-1">单车载荷 (kW)</div>
                                <input
                                    type="number"
                                    value={newVehicleLoad}
                                    onChange={(e) => setNewVehicleLoad(Number(e.target.value))}
                                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm font-mono focus:border-cyan-500 outline-none text-white"
                                />
                            </div>
                            <div className="w-20">
                                <div className="text-[10px] text-slate-400 mb-1">数量</div>
                                <input
                                    type="number"
                                    min="1"
                                    value={addCount}
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

                {/* 2. 场景构建 */}
                <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 shadow-2xl flex-1 flex flex-col overflow-y-auto">
                    <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Layers className="w-4 h-4" /> 场景构建
                    </h3>
                    <div className="space-y-4 flex-1">
                        {/* 设定停车点 */}
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">1. 设定停车点</span>
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
                            
                            {/* 断电热力控制 */}
                            <div className="mb-4 space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-xs text-red-400">
                                        <input type="checkbox" checked={showOutage} onChange={(e) => setShowOutage(e.target.checked)} className="accent-red-500" />
                                        <span>显示断电热力</span>
                                    </div>
                                    <span className="text-[10px] text-slate-500">Max: {outageMaxVal}</span>
                                </div>
                                <input 
                                    type="range" min="10" max="200" step="5" 
                                    value={outageMaxVal} 
                                    onChange={(e) => setOutageMaxVal(Number(e.target.value))} 
                                    className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500" 
                                />
                            </div>

                            {/* 支援热力控制 */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-xs text-cyan-400">
                                        <input type="checkbox" checked={showSupport} onChange={(e) => setShowSupport(e.target.checked)} className="accent-cyan-500" />
                                        <span>显示支援热力</span>
                                    </div>
                                    <span className="text-[10px] text-slate-500">Max: {supportMaxVal}</span>
                                </div>
                                <input 
                                    type="range" min="10" max="200" step="5" 
                                    value={supportMaxVal} 
                                    onChange={(e) => setSupportMaxVal(Number(e.target.value))} 
                                    className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500" 
                                />
                            </div>
                        </div>

                        <div className="mt-4 pt-4 border-t border-slate-700">
                            {/* ... 底部计算按钮保持不变 ... */}
                            <div className="flex justify-between items-end mb-2">
                                <span className="text-sm text-slate-300">4. 算法求解</span>
                                {lossValue && (
                                    <div className="text-right">
                                        <div className="text-[10px] text-slate-500">Loss Function</div>
                                        <div className="text-xl font-mono font-bold text-red-400">{lossValue}</div>
                                    </div>
                                )}
                            </div>
                            <div className="flex gap-2 mb-2">
                                <button onClick={calculateCurrentLoss} className="flex-1 py-2 bg-slate-800 border border-slate-600 text-slate-300 rounded text-xs hover:bg-slate-700">
                                    计算当前 Loss
                                </button>
                                <button onClick={resetSimulation} className="px-3 py-2 bg-slate-800 border border-slate-600 text-slate-300 rounded text-xs hover:bg-slate-700" title="重置车辆位置">
                                    <Trash2 className="w-3 h-3" />
                                </button>
                            </div>
                            <button
                                onClick={runOptimization}
                                disabled={isOptimizing || parkingSpots.length === 0}
                                className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded shadow-lg uppercase disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
                            >
                                {isOptimizing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> 正在求解...
                                    </>
                                ) : (
                                    <>
                                        <Play className="w-4 h-4 fill-current" /> 运行最优分配算法 (Python)
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
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