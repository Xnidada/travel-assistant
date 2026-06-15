"""Step 4: 预算分配（住宿/交通/其他）"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(ctx: dict, hotel_result: dict, route_result: dict, xhs_result: dict) -> dict:
    """基于真实数据计算预算，只有住宿/交通/其他三项"""
    budget = ctx["budget"]
    hotels_by_night = hotel_result.get("hotels_by_night", [])
    daily_plan = route_result.get("daily_plan", [])

    # 住宿: 每晚选第一个酒店的价格
    hotel_total = 0
    for night_info in hotels_by_night:
        hotels = night_info.get("hotels", [])
        if hotels:
            h = hotels[0]
            avg = h.get("price_avg", 0)
            if avg == 0:
                avg = (h.get("price_min", 0) + h.get("price_max", 0)) / 2
            hotel_total += avg

    # 交通: 各段公共交通费用累计
    transport_total = 0
    for day in daily_plan:
        for route in day.get("routes", []):
            transport_total += route.get("cost", 0)

    # 其他 = 总预算 - 住宿 - 交通
    other_total = budget - round(hotel_total) - round(transport_total)
    if other_total < 0:
        other_total = 0

    plan = {
        "total": budget,
        "hotel": round(hotel_total),
        "transport": round(transport_total),
        "other": other_total,
        "breakdown": {},
    }

    for k in ["hotel", "transport", "other"]:
        plan["breakdown"][f"{k}_percent"] = round(plan[k] / budget * 100) if budget > 0 else 0

    print(f"💰 预算分配: 住宿¥{plan['hotel']}({plan['breakdown']['hotel_percent']}%) "
          f"交通¥{plan['transport']}({plan['breakdown']['transport_percent']}%) "
          f"其他¥{plan['other']}({plan['breakdown']['other_percent']}%)")
    return plan
