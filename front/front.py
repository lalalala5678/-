import React, { useState, useEffect, useRef, useMemo } from "react";
import {
    Zap,
    Activity,
    Truck,
    Settings,
    Clock,
    MousePointer2,
    Play,
    Trash2,
    Calculator,
    Layers,
    Eye,
    PlusCircle
} from "lucide-react";

// --- 核心常量配置 ---
const CONFIG = {
    CITY_CENTER: [114.5149, 38.0428], // 石家庄中心坐标 (雷达旋转锚点)
    GRID_RESOLUTION: 20,             // 算法网格分辨率
    MAP_SCALE: 12000,                // 模拟地图缩放比例
    ANIMATION_SPEED: 0.015           // 雷达扫描速度
};

/**
 * 服务层：模拟后端 API 调用与数学计算
 */
const MockApiService = {
    fetchOutageProbability: async () => {
        return new Promise((resolve) => {
            setTimeout(() => {
                const heatPoints = [];
                // 生成一些高热力区域
                const centers = [
                    { x: 0.05, y: 0.05 },
                    { x: -0.08, y: -0.02 },
                    { x: 0.02, y: -0.08 }
                ];

                for (let i = 0; i < 120; i++) {
                    // 围绕几个中心点随机分布
                    const center = centers[Math.floor(Math.random() * centers.length)];
                    const lng = CONFIG.CITY_CENTER[0] + center.x + (Math.random() - 0.5) * 0.1;
                    const lat = CONFIG.CITY_CENTER[1] + center.y + (Math.random() - 0.5) * 0.1;

                    heatPoints.push({
                        lng: lng,
                        lat: lat,
                        count: Math.floor(Math.random() * 80) + 20 // 20-100 的基础热力值
                    });
                }
                resolve(heatPoints);
            }, 600);
        });
    },

    calculateDistance: (p1, p2) => {
        const R = 6371;
        const dLat = (p2.lat - p1.lat) * Math.PI / 180;
        const dLng = (p2.lng - p1.lng) * Math.PI / 180;
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
};

/**
 * 算法层：调度优化核心逻辑
 */
class DispatchAlgorithm {
    constructor() {
        this.grid = [];
        this.resolution = CONFIG.GRID_RESOLUTION;
    }

    initGrid(center) {
        this.grid = [];
        const range = 0.15;
        for (let i = 0; i < this.resolution; i++) {
            for (let j = 0; j < this.resolution; j++) {
                this.grid.push({
                    lng: center[0] - range + (2 * range / this.resolution) * i,
                    lat: center[1] - range + (2 * range / this.resolution) * j,
                    outageProb: 0,
                    supportValue: 0
                });
            }
        }
    }

    mapOutageToGrid(heatPoints) {
        this.grid.forEach((cell) => {
            let prob = 0;
            heatPoints.forEach((p) => {
                const d = Math.sqrt(Math.pow(cell.lng - p.lng, 2) + Math.pow(cell.lat - p.lat, 2));
                // 距离衰减
                if (d < 0.05) {
                    prob += p.count * Math.exp(-d * 100);
                }
            });
            cell.outageProb = prob;
        });
        // 内部归一化以便 Loss 计算，但渲染用的原始值由前端控制
        this._normalize("outageProb");
    }

    calculateTotalSupport(vehicles) {
        this.grid.forEach((cell) => {
            let support = 0;
            vehicles.forEach((v) => {
                if (v.lng === null || v.lat === null) {
                    return;
                }

                const dist = MockApiService.calculateDistance(
                    { lng: v.lng, lat: v.lat },
                    { lng: cell.lng, lat: cell.lat }
                );
                // 载荷越大，支援半径和强度越大
                support += v.load / (Math.pow(dist, 2) + 0.1);
            });
            cell.supportValue = support;
        });
        this._normalize("supportValue");
    }

    // 获取用于渲染的支援热力数据
    getSupportHeatPoints() {
        return this.grid.map((cell) => ({
            lng: cell.lng,
            lat: cell.lat,
            count: cell.supportValue * 100
        })).filter((p) => p.count > 1);
    }

    _normalize(field) {
        const values = this.grid.map((c) => c[field]);
        const max = Math.max(...values) || 1;
        const min = Math.min(...values) || 0;
        const range = max - min || 1;
        this.grid.forEach((c) => {
            c[field] = (c[field] - min) / range;
        });
    }

    calculateLoss() {
        let loss = 0;
        this.grid.forEach((cell) => {
            const diff = cell.outageProb - cell.supportValue;
            loss += Math.pow(diff, 2);
        });
        return loss;
    }

    findBestSpots(vehicles, parkingSpots) {
        if (parkingSpots.length === 0) {
            return vehicles;
        }
        // 简单的贪心分配：载荷大的车去离高风险区最近的停车点（模拟）
        // 这里仅做随机分配演示
        return vehicles.map((v) => {
            const randomSpot = parkingSpots[Math.floor(Math.random() * parkingSpots.length)];
            return {
                ...v,
                lat: randomSpot.lat,
                lng: randomSpot.lng,
                status: "busy"
            };
        });
    }
}

const algorithmEngine = new DispatchAlgorithm();

/**
 * 视图组件：科技感雷达地图 (Canvas)
 */
const TechRadarMap = ({ vehicles, parkingSpots, outageHeatPoints, supportHeatPoints, onMapClick, mode, outageMaxVal, supportMaxVal }) => {
    const canvasRef = useRef(null);

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
            // 每一帧动态获取屏幕中心，确保其对应 City Center
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;

            ctx.fillStyle = "#020617";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // 网格
            ctx.strokeStyle = "rgba(14, 165, 233, 0.05)";
            ctx.lineWidth = 1;
            const gridSize = 50;
            const offset = (Date.now() / 50) % gridSize;
            
            for (let x = offset; x < canvas.width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }
            for (let y = offset; y < canvas.height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }

            // 扫描线
            rotation += CONFIG.ANIMATION_SPEED;
            ctx.save();
            // 将原点移动到屏幕中心（即石家庄市中心）
            ctx.translate(centerX, centerY);
            ctx.rotate(rotation);
            const scanGradient = ctx.createConicGradient(0, 0, 0);
            scanGradient.addColorStop(0, "rgba(14, 165, 233, 0)");
            scanGradient.addColorStop(0.85, "rgba(14, 165, 233, 0.02)");
            scanGradient.addColorStop(1, "rgba(14, 165, 233, 0.4)");
            
            ctx.fillStyle = scanGradient;
            ctx.beginPath();
            ctx.arc(0, 0, Math.max(canvas.width, canvas.height), 0, Math.PI * 2);
            ctx.fill();
            
            ctx.strokeStyle = "rgba(14, 165, 233, 0.8)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(Math.max(canvas.width, canvas.height), 0);
            ctx.stroke();
            ctx.restore();

            // 渲染函数: 绘制热力点
            const drawHeatPoint = (points, colorR, colorG, colorB, maxVal, scaleFactor = 1.5) => {
                if (!points || points.length === 0) {
                    return;
                }
                points.forEach((p) => {
                    // 坐标映射：(经度差 * 比例) + 屏幕中心
                    const x = centerX + (p.lng - CONFIG.CITY_CENTER[0]) * CONFIG.MAP_SCALE;
                    const y = centerY - (p.lat - CONFIG.CITY_CENTER[1]) * CONFIG.MAP_SCALE;

                    let ratio = p.count / maxVal;
                    if (ratio > 1) {
                        ratio = 1;
                    }
                    if (ratio < 0) {
                        ratio = 0;
                    }

                    const radius = 20 * scaleFactor * (0.5 + 0.5 * ratio);
                    const alpha = ratio * 0.6; 

                    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
                    gradient.addColorStop(0, `rgba(${colorR}, ${colorG}, ${colorB}, ${alpha})`);
                    gradient.addColorStop(1, `rgba(${colorR}, ${colorG}, ${colorB}, 0)`);

                    ctx.beginPath();
                    ctx.arc(x, y, radius, 0, Math.PI * 2);
                    ctx.fillStyle = gradient;
                    ctx.fill();
                });
            };

            // 绘制两层热力
            drawHeatPoint(outageHeatPoints, 239, 68, 68, outageMaxVal, 1.0);
            drawHeatPoint(supportHeatPoints, 6, 182, 212, supportMaxVal, 1.5);

            // 绘制元素
            parkingSpots.forEach((p, idx) => {
                const x = centerX + (p.lng - CONFIG.CITY_CENTER[0]) * CONFIG.MAP_SCALE;
                const y = centerY - (p.lat - CONFIG.CITY_CENTER[1]) * CONFIG.MAP_SCALE;
                
                ctx.beginPath();
                ctx.arc(x, y, 8, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(34, 197, 94, 0.3)";
                ctx.fill();
                
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fillStyle = "#22c55e";
                ctx.fill();
                
                ctx.fillStyle = "#fff";
                ctx.font = "10px monospace";
                ctx.fillText(`P${idx + 1}`, x + 6, y + 3);
            });

            vehicles.forEach((v) => {
                if (v.lng === null || v.lat === null) {
                    return;
                }
                const x = centerX + (v.lng - CONFIG.CITY_CENTER[0]) * CONFIG.MAP_SCALE;
                const y = centerY - (v.lat - CONFIG.CITY_CENTER[1]) * CONFIG.MAP_SCALE;

                ctx.beginPath();
                ctx.arc(x, y, 40, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(14, 165, 233, 0.2)";
                ctx.setLineDash([5, 5]);
                ctx.stroke();
                ctx.setLineDash([]);
                
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = "#eab308";
                ctx.fill();
                
                ctx.fillStyle = "#fbbf24";
                ctx.font = "10px monospace";
                ctx.fillText(`${v.load}kW`, x + 8, y + 3);
            });

            animationFrameId = requestAnimationFrame(render);
        };

        render();
        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(animationFrameId);
        };
    }, [vehicles, parkingSpots, outageHeatPoints, supportHeatPoints, outageMaxVal, supportMaxVal]);

    const handleClick = (e) => {
        if (mode !== "add-spot") {
            return;
        }
        const rect = canvasRef.current.getBoundingClientRect();
        // 点击坐标反算，同样基于当前动态计算的 centerX/centerY (即 canvas.width/2)
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const lng = (e.clientX - rect.left - centerX) / CONFIG.MAP_SCALE + CONFIG.CITY_CENTER[0];
        const lat = (centerY - (e.clientY - rect.top)) / CONFIG.MAP_SCALE + CONFIG.CITY_CENTER[1];
        onMapClick({ lng: lng, lat: lat });
    };

    return <canvas ref={canvasRef} onClick={handleClick} className={`absolute inset-0 z-0 ${mode === "add-spot" ? "cursor-crosshair" : "cursor-default"}`} />;
};

/**
 * 视图组件：真实高德地图
 */
const RealGaodeMap = ({ apiKey, vehicles, parkingSpots, outageHeatPoints, onMapClick, mode, outageMaxVal }) => {
    const mapContainerRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const heatmapLayerRef = useRef(null);

    useEffect(() => {
        if (!apiKey) {
            return;
        }
        const script = document.createElement("script");
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${apiKey}&plugin=AMap.HeatMap`;
        script.async = true;
        script.onload = () => {
            if (!window.AMap) {
                return;
            }
            const map = new window.AMap.Map(mapContainerRef.current, {
                zoom: 12,
                center: CONFIG.CITY_CENTER,
                mapStyle: "amap://styles/darkblue",
                viewMode: "3D",
                pitch: 40
            });
            mapInstanceRef.current = map;
            const heatmap = new window.AMap.HeatMap(map, {
                radius: 30,
                opacity: [0, 0.8],
                gradient: {
                    0.5: "blue",
                    0.65: "rgb(117,211,248)",
                    0.7: "rgb(0, 255, 0)",
                    0.9: "#ffea00",
                    1.0: "red"
                }
            });
            heatmapLayerRef.current = heatmap;
            map.on("click", (e) => {
                if (mode === "add-spot") {
                    onMapClick({ lng: e.lnglat.getLng(), lat: e.lnglat.getLat() });
                }
            });
        };
        document.head.appendChild(script);
        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.destroy();
            }
            document.head.removeChild(script);
        };
    }, [apiKey]);

    useEffect(() => {
        const map = mapInstanceRef.current;
        if (!map) {
            return;
        }
        map.clearMap();

        // 标记绘制
        vehicles.forEach((v) => {
            if (v.lng === null || v.lat === null) {
                return;
            }
            new window.AMap.Marker({
                position: [v.lng, v.lat],
                content: `<div class="w-4 h-4 rounded-full border-2 border-white bg-yellow-500 shadow-[0_0_10px_currentColor] flex items-center justify-center"><span class="text-[8px] text-white absolute -top-4 bg-black/50 px-1 rounded">${v.load}</span></div>`,
                map: map
            });
        });
        parkingSpots.forEach((p, idx) => {
            new window.AMap.Marker({
                position: [p.lng, p.lat],
                content: `<div class="flex flex-col items-center"><div class="w-6 h-6 bg-green-600 text-white text-xs flex items-center justify-center rounded border border-white">P${idx + 1}</div><div class="w-0.5 h-4 bg-white"></div></div>`,
                offset: new window.AMap.Pixel(-10, -30),
                map: map
            });
        });

        // 更新热力图数据和最大值配置
        if (heatmapLayerRef.current) {
            heatmapLayerRef.current.setDataSet({
                data: outageHeatPoints,
                max: outageMaxVal // 动态设置最大值
            });
        }
    }, [vehicles, parkingSpots, outageHeatPoints, outageMaxVal]);

    return <div ref={mapContainerRef} className={`absolute inset-0 z-0 ${mode === "add-spot" ? "cursor-crosshair" : ""}`} />;
};

/**
 * 主应用组件
 */
export default function EmergencyDispatchSystem() {
    const [useRealMap, setUseRealMap] = useState(false);
    const [apiKey, setApiKey] = useState("");
    const [vehicles, setVehicles] = useState([]);
    const [parkingSpots, setParkingSpots] = useState([]);
    const [outageHeatmap, setOutageHeatmap] = useState([]);
    const [supportHeatmap, setSupportHeatmap] = useState([]);

    // 热力图最大值控制 (Normalization Max Value)
    const [outageMaxVal, setOutageMaxVal] = useState(80);
    const [supportMaxVal, setSupportMaxVal] = useState(100);

    // 车辆管理
    const [newVehicleLoad, setNewVehicleLoad] = useState(500);

    const [lossValue, setLossValue] = useState(null);
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [interactionMode, setInteractionMode] = useState("view");
    const [currentTime, setCurrentTime] = useState(new Date());

    // 仅初始化一次网格
    useEffect(() => {
        algorithmEngine.initGrid(CONFIG.CITY_CENTER);
    }, []);

    useEffect(() => {
        const t = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(t);
    }, []);

    // --- 车辆管理逻辑 ---
    const addVehicle = () => {
        const newVehicle = {
            id: `EV-${1000 + vehicles.length + 1}`,
            status: "idle",
            load: newVehicleLoad,
            lng: null,
            lat: null
        };
        setVehicles([...vehicles, newVehicle]);
    };

    const clearVehicles = () => {
        setVehicles([]);
        setLossValue(null);
        setSupportHeatmap([]);
    };

    // --- 地图交互逻辑 ---
    const handleMapClick = (coord) => {
        if (interactionMode === "add-spot") {
            setParkingSpots((prev) => [...prev, { ...coord, id: `P-${prev.length + 1}` }]);
        }
    };

    const generateHeatmap = async () => {
        const data = await MockApiService.fetchOutageProbability();
        setOutageHeatmap(data);
        algorithmEngine.mapOutageToGrid(data);
        calculateCurrentLoss();
    };

    const calculateCurrentLoss = () => {
        algorithmEngine.calculateTotalSupport(vehicles);
        const loss = algorithmEngine.calculateLoss();
        setLossValue(loss.toFixed(4));
        setSupportHeatmap(algorithmEngine.getSupportHeatPoints());
    };

    const runOptimization = async () => {
        if (parkingSpots.length === 0) {
            return alert("请先设定停车点！");
        }
        if (vehicles.length === 0) {
            return alert("请先添加电力车！");
        }

        setIsOptimizing(true);
        await new Promise((r) => setTimeout(r, 1200));

        const optimizedFleet = algorithmEngine.findBestSpots(vehicles, parkingSpots);
        setVehicles(optimizedFleet);
        algorithmEngine.calculateTotalSupport(optimizedFleet);
        const newLoss = algorithmEngine.calculateLoss();
        setLossValue(newLoss.toFixed(4));
        setSupportHeatmap(algorithmEngine.getSupportHeatPoints());

        setIsOptimizing(false);
    };

    const resetSimulation = () => {
        setVehicles(vehicles.map((v) => ({ ...v, status: "idle", lng: null, lat: null })));
        setLossValue(null);
        setSupportHeatmap([]);
    };

    return (
        <div className="relative w-full h-screen bg-slate-950 overflow-hidden text-cyan-50 font-sans selection:bg-cyan-500 selection:text-white">
            {/* 地图层 */}
            {useRealMap ? (
                <RealGaodeMap
                    apiKey={apiKey}
                    vehicles={vehicles}
                    parkingSpots={parkingSpots}
                    outageHeatPoints={outageHeatmap}
                    outageMaxVal={outageMaxVal}
                    onMapClick={handleMapClick}
                    mode={interactionMode}
                />
            ) : (
                <TechRadarMap
                    vehicles={vehicles}
                    parkingSpots={parkingSpots}
                    outageHeatPoints={outageHeatmap}
                    supportHeatPoints={supportHeatmap}
                    outageMaxVal={outageMaxVal}
                    supportMaxVal={supportMaxVal}
                    onMapClick={handleMapClick}
                    mode={interactionMode}
                />
            )}

            {/* 装饰与头部 */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(14,165,233,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(14,165,233,0.02)_1px,transparent_1px)] bg-[size:50px_50px]"></div>
            <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-8 py-4 bg-gradient-to-b from-slate-950 via-slate-900/90 to-transparent">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-cyan-500/20 border border-cyan-500/50 rounded-md shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                        <Zap className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                            智能电网调度推演系统
                        </h1>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] text-cyan-600 tracking-[0.2em] uppercase">Smart Grid Dispatch & Simulation</span>
                            {useRealMap && <span className="text-[10px] px-1 border border-green-500 text-green-500 rounded">Online</span>}
                        </div>
                    </div>
                </div>
                <div className="bg-slate-900/50 backdrop-blur border border-cyan-500/20 rounded-full px-6 py-1">
                    <span className="text-sm text-cyan-300 font-mono flex items-center gap-2">
                        <Calculator className="w-4 h-4" /> 算法仿真优化模式
                    </span>
                </div>
                <div className="flex items-center gap-6">
                    <div className="font-mono text-cyan-300/80 bg-slate-900/50 px-4 py-1 rounded-full border border-cyan-900/50">
                        {currentTime.toLocaleTimeString()}
                    </div>
                    <button className="text-cyan-400 hover:text-white">
                        <Settings className="w-6 h-6" />
                    </button>
                </div>
            </header>

            {/* 左侧控制面板 */}
            <aside className="absolute top-24 bottom-8 left-8 w-96 flex flex-col gap-4 z-10 animate-in slide-in-from-left duration-500">

                {/* 1. 资源配置 (修改为数组管理模式) */}
                <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 shadow-2xl">
                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <Truck className="w-4 h-4" /> 资源配置 (Fleet)
                    </h3>

                    {/* 添加控制 */}
                    <div className="mb-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <div className="flex-1">
                                <div className="text-[10px] text-slate-400 mb-1">新增车辆载荷 (Load/kW)</div>
                                <input
                                    type="number"
                                    value={newVehicleLoad}
                                    onChange={(e) => setNewVehicleLoad(Number(e.target.value))}
                                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm font-mono focus:border-cyan-500 outline-none text-white"
                                />
                            </div>
                            <div className="pt-4">
                                <button
                                    onClick={addVehicle}
                                    className="px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/40 border border-cyan-500/50 text-cyan-400 rounded flex items-center gap-1 transition-colors"
                                >
                                    <PlusCircle className="w-4 h-4" /> 添加
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* 列表展示 */}
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
                        {/* 停车点 */}
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
                                    <MousePointer2 className="w-3 h-3" /> {interactionMode === "add-spot" ? "点击地图选点" : "开启选点模式"}
                                </button>
                                <button onClick={() => setParkingSpots([])} className="px-3 py-2 bg-slate-800 text-slate-400 border border-slate-700 rounded hover:text-red-400">
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* 模拟 */}
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">2. 模拟断电热力</span>
                            </div>
                            <button onClick={generateHeatmap} className="w-full py-2 bg-indigo-600/20 border border-indigo-500/50 text-indigo-300 rounded text-xs hover:bg-indigo-600/40 flex items-center justify-center gap-2">
                                <Activity className="w-3 h-3" /> 生成随机热力图
                            </button>
                        </div>

                        {/* 阈值控制 (修改逻辑) */}
                        <div className="p-3 bg-slate-950/50 rounded border border-slate-800">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-slate-300">3. 热力显示范围 (Max Value)</span>
                            </div>

                            <div className="mb-3">
                                <div className="flex justify-between text-[10px] text-red-400 mb-1">
                                    <span className="flex items-center gap-1">
                                        <Eye className="w-3 h-3" /> 断电热力峰值 (Outage Max)
                                    </span>
                                    <span>{outageMaxVal}</span>
                                </div>
                                <input
                                    type="range"
                                    min="10"
                                    max="200"
                                    step="5"
                                    value={outageMaxVal}
                                    onChange={(e) => setOutageMaxVal(Number(e.target.value))}
                                    className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                                    title="降低此值会使低热力区域变红（更灵敏），增加此值会使整体颜色变淡"
                                />
                            </div>

                            <div>
                                <div className="flex justify-between text-[10px] text-cyan-400 mb-1">
                                    <span className="flex items-center gap-1">
                                        <Zap className="w-3 h-3" /> 支援热力峰值 (Support Max)
                                    </span>
                                    <span>{supportMaxVal}</span>
                                </div>
                                <input
                                    type="range"
                                    min="10"
                                    max="200"
                                    step="5"
                                    value={supportMaxVal}
                                    onChange={(e) => setSupportMaxVal(Number(e.target.value))}
                                    className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                                />
                            </div>
                        </div>

                        {/* 计算 */}
                        <div className="mt-4 pt-4 border-t border-slate-700">
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
                                        <Play className="w-4 h-4 fill-current" /> 运行最优分配算法
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </aside>

            {!useRealMap && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center z-20">
                    <button onClick={() => setUseRealMap(true)} className="text-xs text-slate-500 hover:text-cyan-400 underline decoration-dashed">
                        切换到真实高德地图模式 (API Mode)
                    </button>
                </div>
            )}
            {useRealMap && !apiKey && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <div className="bg-slate-900 p-6 rounded-lg border border-cyan-500/30 w-96 shadow-2xl">
                        <h3 className="text-white font-bold mb-2">输入高德地图 Key</h3>
                        <input
                            type="text"
                            placeholder="Web端 API Key"
                            className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white mb-4 focus:border-cyan-500 outline-none"
                            onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                    setApiKey(e.target.value);
                                }
                            }}
                        />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setUseRealMap(false)} className="px-4 py-2 text-slate-400 text-sm">
                                取消
                            </button>
                            <button className="px-4 py-2 bg-cyan-600 text-white rounded text-sm">
                                确认
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}