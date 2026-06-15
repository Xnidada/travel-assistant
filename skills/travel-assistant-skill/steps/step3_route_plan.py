"""Step 3: 高德地图 — 坐标获取 & 路径规划 & 地图数据"""
import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.amap_client import AmapClient
from lib.tsp_solver import TSPSolver
from config import POI_CACHE_DIR, AMAP_JSAPI_KEY, AMAP_JSAPI_SECURITY_CODE


def _cache_path(city: str, name: str) -> str:
    import re
    safe = re.sub(r'[^\w]', '_', name)
    return os.path.join(POI_CACHE_DIR, f"{city}_{safe}.json")


def _get_cached(city: str, name: str) -> dict | None:
    p = _cache_path(city, name)
    if os.path.isfile(p):
        try:
            d = json.load(open(p))
            ts = datetime.fromisoformat(d["timestamp"])
            if (datetime.now() - ts).days <= 7:
                return d["coordinates"]
        except Exception:
            pass
    return None


def _set_cached(city: str, name: str, coords: dict):
    os.makedirs(POI_CACHE_DIR, exist_ok=True)
    p = _cache_path(city, name)
    json.dump({"name": name, "city": city, "coordinates": coords,
               "timestamp": datetime.now().isoformat()}, open(p, "w"), ensure_ascii=False)


_CITY_CENTERS = {
    "武汉": (30.593, 114.305), "北京": (39.904, 116.407),
    "上海": (31.230, 121.473), "广州": (23.129, 113.264),
    "深圳": (22.543, 114.057), "成都": (30.572, 104.066),
    "杭州": (30.274, 120.155), "南京": (32.060, 118.796),
    "西安": (34.341, 108.939), "重庆": (29.563, 106.551),
    "长沙": (28.228, 112.939), "苏州": (31.299, 120.585),
    "厦门": (24.480, 118.089), "青岛": (36.067, 120.383),
    "大连": (38.914, 121.615), "三亚": (18.252, 109.512),
}


def _get_poi_coords(amap: AmapClient, city: str, name: str) -> dict:
    """获取一个地点的坐标（缓存优先）"""
    cached = _get_cached(city, name)
    if cached:
        return cached
    try:
        pois = amap.search_poi(name, city)
        if pois:
            loc = pois[0]["location"].split(",")
            coords = {"lng": float(loc[0]), "lat": float(loc[1])}
            _set_cached(city, name, coords)
            return coords
    except Exception:
        pass
    lat, lng = _CITY_CENTERS.get(city, (30.593, 114.305))
    return {"lat": lat, "lng": lng}


def _plan_route(amap: AmapClient, p1: dict, p2: dict, city: str) -> dict:
    """查询两地点间的公共交通路线"""
    origin = f"{p1['lng']},{p1['lat']}"
    dest = f"{p2['lng']},{p2['lat']}"
    route = None
    try:
        route = amap.plan_transit(origin, dest, city, strategy=0)
    except Exception:
        pass
    if route is None:
        try:
            route = amap.plan_walking(origin, dest)
        except Exception:
            pass
    if route is None:
        d = TSPSolver.haversine(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        route = {
            "distance": int(d * 1000),
            "duration": int((d / 30) * 3600),
            "cost": 5 if d > 3 else 2,
            "segments": [{
                "type": "estimate",
                "instruction": f"约{d:.1f}公里（估算）",
                "distance": int(d * 1000),
                "duration": int((d / 30) * 3600),
            }],
        }
    route["from"] = p1.get("name", "")
    route["to"] = p2.get("name", "")
    return route


def run(ctx: dict, xhs_result: dict, hotel_result: dict) -> dict:
    """坐标获取 + TSP路线优化 + 公共交通查询"""
    city = ctx["city"]
    amap = AmapClient()
    attractions = xhs_result.get("attractions", [])
    hotels_by_night = hotel_result.get("hotels_by_night", [])
    total_days = ctx["total_days"]
    start_dt = ctx["start_dt"]

    # ── 3a. 获取所有景点坐标 ──
    print("获取景点坐标...")
    for a in attractions:
        name = a["name"]
        coords = _get_poi_coords(amap, city, name)
        a["coordinates"] = coords
        cached = _get_cached(city, name)
        tag = "缓存" if cached else "新查"
        print(f"   📍 {name}: ({coords['lat']:.4f}, {coords['lng']:.4f}) [{tag}]")

    # ── 3b. 获取酒店坐标（仅用于地图标记） ──
    all_hotels = []
    for night_info in hotels_by_night:
        for h in night_info.get("hotels", []):
            name = h.get("name", "")
            if name:
                h["coordinates"] = _get_poi_coords(amap, city, name)
                all_hotels.append(h)

    # ── 3c. TSP路线优化（纯景点，不含酒店） ──
    print("🧭 优化路线顺序...")
    tsp_points = []
    for a in attractions:
        c = a.get("coordinates", {})
        if c.get("lat") and c.get("lng"):
            tsp_points.append({
                "id": f"attr_{len(tsp_points)}",
                "name": a["name"],
                "lat": c["lat"], "lng": c["lng"],
                "type": a.get("type", "景点"),
                "visit_time": a.get("visit_time", "2-3小时"),
                "ticket_price": a.get("ticket_price", 0),
                "tips": a.get("tips", ""),
                "popularity": a.get("popularity", 5),
            })

    if not tsp_points:
        print("⚠️  无有效景点坐标，跳过路线规划")
        return {"daily_plan": [], "map_data": {}}

    solver = TSPSolver(tsp_points)
    path = solver.solve(start_idx=0)

    max_per_day = max(3, len(tsp_points) // total_days + 1)
    daily_raw = solver.allocate_days(
        path, max_per_day=max_per_day,
        max_hours=10, time_per_point=120,
    )

    # 确保天数匹配
    while len(daily_raw) < total_days and len(daily_raw) > 0:
        max_day = max(daily_raw, key=lambda d: len(d["points"]))
        if len(max_day["points"]) <= 2:
            break
        mid = len(max_day["points"]) // 2
        new_day = {
            "points": max_day["points"][mid:],
            "total_time_min": max_day["total_time_min"] // 2,
            "travel_dist_km": max_day["travel_dist_km"] / 2,
        }
        max_day["points"] = max_day["points"][:mid]
        max_day["total_time_min"] //= 2
        max_day["travel_dist_km"] /= 2
        daily_raw.append(new_day)

    # ── 3d. 每日行程（纯景点+景点间交通，不含酒店） ──
    print("🚌 查询公共交通方案...")
    daily_plan = []

    for day_idx in range(min(total_days, len(daily_raw))):
        day_data = daily_raw[day_idx]
        day_date = (start_dt + timedelta(days=day_idx)).strftime("%Y-%m-%d")
        points = list(day_data["points"])
        routes = []

        # 景点间路线
        for pi in range(len(points) - 1):
            p1 = points[pi]
            p2 = points[pi + 1]
            print(f"   {p1['name']} → {p2['name']}...", end=" ")
            r = _plan_route(amap, p1, p2, city)
            routes.append(r)
            print("✓")

        daily_plan.append({
            "day": day_idx + 1,
            "date": day_date,
            "points": points,
            "routes": routes,
            "total_time_min": day_data["total_time_min"],
            "travel_dist_km": day_data["travel_dist_km"],
        })

    # ── 3e. 地图数据（景点带序号，酒店只标位置不画路线） ──
    center_lat, center_lng = _CITY_CENTERS.get(city, (30.593, 114.305))
    all_lats = [p["lat"] for dp in daily_plan for p in dp["points"]]
    all_lngs = [p["lng"] for dp in daily_plan for p in dp["points"]]
    # 也把酒店坐标纳入中心计算
    for h in all_hotels:
        hc = h.get("coordinates", {})
        if hc.get("lat"):
            all_lats.append(hc["lat"])
            all_lngs.append(hc["lng"])
    if all_lats:
        center_lat = sum(all_lats) / len(all_lats)
        center_lng = sum(all_lngs) / len(all_lngs)

    map_data = {
        "center_lat": center_lat,
        "center_lng": center_lng,
        "zoom": 12,
        "amap_key": AMAP_JSAPI_KEY,
        "amap_security": AMAP_JSAPI_SECURITY_CODE,
        "markers": [],
        "polylines": [],
    }

    day_colors = ["#1890ff", "#52c41a", "#fa8c16", "#f5222d", "#722ed1",
                  "#13c2c2", "#eb5f96", "#faad14"]

    # 景点标记（带序号）+ 路线
    seq = 1
    for dp in daily_plan:
        day = dp["day"]
        color = day_colors[(day - 1) % len(day_colors)]
        coords_list = []
        for p in dp["points"]:
            map_data["markers"].append({
                "name": p["name"], "lat": p["lat"], "lng": p["lng"],
                "type": p.get("type", "景点"), "day": day, "color": color,
                "seq": seq,
            })
            seq += 1
            coords_list.append([p["lng"], p["lat"]])
        if len(coords_list) >= 2:
            map_data["polylines"].append({
                "path": coords_list, "color": color, "day": day,
            })

    # 酒店标记（只标位置，不画路线）
    added_names = set()
    for h in all_hotels:
        name = h.get("name", "")
        if name and name not in added_names:
            added_names.add(name)
            hc = h.get("coordinates", {})
            if hc.get("lat"):
                map_data["markers"].append({
                    "name": name, "lat": hc["lat"], "lng": hc["lng"],
                    "type": "酒店", "day": 0, "color": "#ff4d4f", "seq": 0,
                })

    print(f"✅ 路线规划完成: {len(daily_plan)}天行程")
    return {"daily_plan": daily_plan, "map_data": map_data, "selected_hotels": all_hotels}
