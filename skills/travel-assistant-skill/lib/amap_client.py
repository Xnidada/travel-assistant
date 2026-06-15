"""高德地图 API 客户端封装"""
import time
import requests
from config import AMAP_WEBSERVICE_KEY, AMAP_MIN_INTERVAL


class AmapClient:
    BASE = "https://restapi.amap.com/v3"

    def __init__(self):
        self.key = AMAP_WEBSERVICE_KEY
        self.session = requests.Session()
        self._last = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last
        if elapsed < AMAP_MIN_INTERVAL:
            time.sleep(AMAP_MIN_INTERVAL - elapsed)
        self._last = time.time()

    # ── POI 搜索 ──
    def search_poi(self, keywords: str, city: str) -> list:
        self._rate_limit()
        r = self.session.get(f"{self.BASE}/place/text", params={
            "key": self.key, "keywords": keywords,
            "city": city, "output": "JSON",
            "extensions": "all", "citylimit": "true",
        })
        d = r.json()
        if d.get("status") == "1":
            return d.get("pois", [])
        raise RuntimeError(f"POI搜索失败: {d.get('info')}")

    # ── 公共交通路径规划 ──
    def plan_transit(self, origin: str, destination: str,
                     city: str, strategy: int = 0) -> dict | None:
        """
        origin/destination: "经度,纬度"
        strategy: 0最快捷 1最经济 2最少换乘 3最少步行
        """
        self._rate_limit()
        r = self.session.get(f"{self.BASE}/direction/transit/integrated", params={
            "key": self.key, "origin": origin, "destination": destination,
            "city": city, "output": "JSON", "extensions": "all",
            "strategy": strategy,
        })
        d = r.json()
        if d.get("status") == "1" and d.get("route", {}).get("transits"):
            return self._parse_transit(d)
        return None

    # ── 步行路径 ──
    def plan_walking(self, origin: str, destination: str) -> dict | None:
        self._rate_limit()
        r = self.session.get(f"{self.BASE}/direction/walking", params={
            "key": self.key, "origin": origin, "destination": destination,
            "output": "JSON",
        })
        d = r.json()
        if d.get("status") == "1" and d.get("route", {}).get("paths"):
            p = d["route"]["paths"][0]
            return {
                "distance": int(p["distance"]),
                "duration": int(p["duration"]),
                "cost": 0,
                "segments": [{
                    "type": "walking",
                    "instruction": f"步行{int(p['distance'])}米（约{int(p['duration'])//60}分钟）",
                    "distance": int(p["distance"]),
                    "duration": int(p["duration"]),
                }],
            }
        return None

    # ── 解析公共交通 ──
    def _parse_transit(self, data: dict) -> dict:
        transits = data["route"].get("transits", [])
        if not transits:
            return None
        best = transits[0]
        segments = []
        for seg in best.get("segments", []):
            # 步行
            w = seg.get("walking")
            if w and int(w.get("distance", 0)) > 0:
                segments.append({
                    "type": "walking",
                    "distance": int(w["distance"]),
                    "duration": int(w["duration"]),
                    "instruction": f"步行{int(w['distance'])}米（约{int(w['duration'])//60}分钟）",
                })
            # 公交
            bus = seg.get("bus")
            if bus and bus.get("buslines"):
                bl = bus["buslines"][0]
                segments.append({
                    "type": "bus",
                    "name": bl.get("name", ""),
                    "departure": bl.get("departure_stop", {}).get("name", ""),
                    "arrival": bl.get("arrival_stop", {}).get("name", ""),
                    "distance": int(bl.get("distance", 0)),
                    "duration": int(bl.get("duration", 0)),
                    "stops": int(bl.get("via_num", 0)),
                    "instruction": f"乘坐{bl.get('name','公交')}（{bl.get('departure_stop',{}).get('name','')}→{bl.get('arrival_stop',{}).get('name','')}）",
                })
            # 地铁
            subway = seg.get("subway")
            if subway and subway.get("buslines"):
                bl = subway["buslines"][0]
                segments.append({
                    "type": "subway",
                    "name": bl.get("name", ""),
                    "departure": bl.get("departure_stop", {}).get("name", ""),
                    "arrival": bl.get("arrival_stop", {}).get("name", ""),
                    "distance": int(bl.get("distance", 0)),
                    "duration": int(bl.get("duration", 0)),
                    "stops": int(bl.get("via_num", 0)),
                    "instruction": f"乘坐{bl.get('name','地铁')}（{bl.get('departure_stop',{}).get('name','')}→{bl.get('arrival_stop',{}).get('name','')}）",
                })
        return {
            "distance": int(data["route"].get("distance", 0)),
            "duration": int(best.get("duration", 0)),
            "cost": float(best.get("cost", 0)),
            "segments": segments,
            "walking_distance": sum(s["distance"] for s in segments if s["type"] == "walking"),
        }

    # ── 地理编码 ──
    def geocode(self, address: str, city: str = "") -> dict | None:
        self._rate_limit()
        r = self.session.get(f"{self.BASE}/geocode/geo", params={
            "key": self.key, "address": address,
            "city": city, "output": "JSON",
        })
        d = r.json()
        if d.get("status") == "1" and d.get("geocodes"):
            g = d["geocodes"][0]
            loc = g["location"].split(",")
            return {"lng": float(loc[0]), "lat": float(loc[1]),
                    "formatted": g.get("formatted_address", "")}
        return None
