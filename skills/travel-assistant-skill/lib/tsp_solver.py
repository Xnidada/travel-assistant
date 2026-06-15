"""TSP 路径优化算法"""
import math


class TSPSolver:
    """旅行商问题求解: 最近邻 + 2-opt 优化"""

    def __init__(self, points: list):
        """
        points: [{"id", "name", "lat", "lng", "type", ...}]
        """
        self.points = points
        self.n = len(points)
        self.dist_matrix = None

    @staticmethod
    def haversine(lat1, lng1, lat2, lng2) -> float:
        """球面距离 (km)"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def build_dist_matrix(self):
        n = self.n
        m = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = self.haversine(
                    self.points[i]["lat"], self.points[i]["lng"],
                    self.points[j]["lat"], self.points[j]["lng"],
                )
                m[i][j] = m[j][i] = d
        self.dist_matrix = m

    def nearest_neighbor(self, start: int = 0) -> list:
        """最近邻贪心"""
        visited = [False] * self.n
        path = [start]
        visited[start] = True
        cur = start
        for _ in range(self.n - 1):
            best_j, best_d = -1, float("inf")
            for j in range(self.n):
                if not visited[j] and self.dist_matrix[cur][j] < best_d:
                    best_d = self.dist_matrix[cur][j]
                    best_j = j
            if best_j < 0:
                break
            visited[best_j] = True
            path.append(best_j)
            cur = best_j
        return path

    def two_opt(self, path: list, max_iter: int = 500) -> list:
        """2-opt 局部优化"""
        n = len(path)
        if n <= 3:
            return path
        improved = True
        it = 0
        while improved and it < max_iter:
            improved = False
            it += 1
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    d1 = (self.dist_matrix[path[i-1]][path[i]] +
                          self.dist_matrix[path[j]][path[j+1]])
                    d2 = (self.dist_matrix[path[i-1]][path[j]] +
                          self.dist_matrix[path[i]][path[j+1]])
                    if d2 < d1:
                        path[i:j+1] = reversed(path[i:j+1])
                        improved = True
        return path

    def solve(self, start_idx: int = 0) -> list:
        """返回优化后的点索引路径"""
        self.build_dist_matrix()
        path = self.nearest_neighbor(start_idx)
        path = self.two_opt(path)
        return path

    def allocate_days(self, path: list, max_per_day: int = 5,
                      max_hours: int = 10, time_per_point: int = 120,
                      travel_speed: float = 30.0) -> list:
        """
        按天分配景点
        返回: [{"points": [point_dict, ...], "total_time_min": int, "travel_dist_km": float}, ...]
        """
        days = []
        cur = {"points": [], "total_time_min": 0, "travel_dist_km": 0.0}

        for idx, pi in enumerate(path):
            pt = self.points[pi]
            # 估算到下一个点的旅行时间
            travel_min = 0
            if idx < len(path) - 1:
                d = self.dist_matrix[pi][path[idx + 1]]
                travel_min = (d / travel_speed) * 60
                cur["travel_dist_km"] += d

            point_time = time_per_point + travel_min

            if (len(cur["points"]) >= max_per_day or
                    cur["total_time_min"] + point_time > max_hours * 60):
                days.append(cur)
                cur = {"points": [], "total_time_min": 0, "travel_dist_km": 0.0}

            cur["points"].append(pt)
            cur["total_time_min"] += point_time

        if cur["points"]:
            days.append(cur)
        return days
