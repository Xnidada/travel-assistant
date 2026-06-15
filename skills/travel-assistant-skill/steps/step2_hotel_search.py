# """Step 2: 飞猪酒店搜索 & 模型分析"""
# import sys
# import os
# from datetime import datetime, timedelta

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from lib.flyai_client import FlyaiClient
# from lib.ai_analyzer import analyzer


# def run(ctx: dict, xhs_result: dict, daily_plan: list = None) -> dict:
#     """
#     搜索酒店: 用 flyai search-hotels --poi-name 按景点位置搜索
#     每晚选出2-3个酒店
#     """
#     city = ctx["city"]
#     nights = ctx["nights"]
#     night_dates = ctx["night_dates"]
#     budget = ctx["budget"]
#     flyai = FlyaiClient()

#     attractions = xhs_result.get("attractions", [])
#     hotels_by_night = []

#     if nights == 0:
#         print("ℹ️  当天来回，无需住宿")
#         return {"hotels_by_night": []}

#     hotel_budget_per_night = (budget * 0.4) / nights
#     print(f"🏨 酒店搜索: {nights}晚, 每晚预算 ¥{hotel_budget_per_night:.0f}")

#     for i, night_date in enumerate(night_dates):
#         # 确定搜索位置: 下一天第一个景点，优先选知名景点
#         search_location = city  # 默认用城市名
#         if daily_plan and i + 1 < len(daily_plan):
#             next_day_points = daily_plan[i + 1].get("points", [])
#             if next_day_points:
#                 search_location = next_day_points[0].get("name", search_location)
#         elif attractions:
#             idx = (i + 1) * 2
#             if idx < len(attractions):
#                 search_location = attractions[idx]["name"]
#             else:
#                 search_location = attractions[0]["name"]

#         # 入住/退房日期
#         check_in = night_date
#         check_out_dt = datetime.strptime(night_date, "%Y-%m-%d") + timedelta(days=1)
#         check_out = check_out_dt.strftime("%Y-%m-%d")

#         print(f"   🔎 第{i+1}晚({night_date}): 搜索{search_location}附近酒店...")

#         # 用 flyai search-hotels --poi-name
#         raw_output = ""
#         try:
#             raw_output = flyai.search_hotels_by_poi(
#                 dest_name=city,
#                 poi_name=search_location,
#                 check_in=check_in,
#                 check_out=check_out,
#                 max_price=int(hotel_budget_per_night * 1.5),
#             )
#         except Exception as e:
#             print(f"   ⚠️  search-hotels失败: {e}")

#         if not raw_output.strip() or len(raw_output) < 50:
#             print(f"   ⚠️  飞猪无有效输出")
#             hotels_by_night.append({
#                 "night": night_date,
#                 "check_in": check_in,
#                 "check_out": check_out,
#                 "search_location": search_location,
#                 "hotels": [],
#             })
#             continue

#         # 用模型分析飞猪输出（截断过长输入）
#         print(f"   🤖 模型分析酒店结果...")
#         raw_for_ai = raw_output[:8000] if len(raw_output) > 8000 else raw_output

#         hotel_prompt = f"""以下是飞猪search-hotels返回的JSON数据，搜索的是"{city}{search_location}附近酒店"。
# 请从中提取正规酒店信息（排除青年旅舍/民宿/公寓），返回JSON数组:
# [
#   {{
#     "name": "酒店全名",
#     "type": "舒适型/高档型/豪华型",
#     "price_min": 最低价(数字),
#     "price_max": 最高价(数字),
#     "price_avg": 平均价(数字),
#     "distance": "距XX约X公里",
#     "walking_time": "步行X分钟",
#     "highlights": ["亮点1", "亮点2"],
#     "booking_link": "预订URL"
#   }}
# ]
# 要求:
# - 只提取正规酒店，排除青年旅舍/民宿/公寓/青旅
# - price从price字段中提取数字
# - booking_link使用detailUrl字段
# - distance/walking_time根据interestsPoi字段推断
# - 最多提取3个酒店（选性价比最好的）
# - 按价格从低到高排列"""

#         try:
#             hotels = analyzer.analyze(raw_for_ai, hotel_prompt)
#             if isinstance(hotels, dict):
#                 hotels = hotels.get("hotels") or hotels.get("data") or []
#             if not isinstance(hotels, list):
#                 hotels = []
#         except Exception as e:
#             print(f"   ❌ 模型分析酒店失败: {e}")
#             hotels = []

#         # 按预算过滤，取2-3个
#         filtered = []
#         for h in hotels:
#             avg = h.get("price_avg", 0)
#             if avg == 0:
#                 avg = (h.get("price_min", 0) + h.get("price_max", 0)) / 2
#             h["price_avg"] = int(avg)
#             if avg <= hotel_budget_per_night * 1.5:
#                 filtered.append(h)

#         # 如果全超预算，取最便宜的2个
#         if not filtered and hotels:
#             hotels.sort(key=lambda x: x.get("price_avg", 9999))
#             filtered = hotels[:2]
#             for h in filtered:
#                 h["note"] = "超出预算，仅供参考"

#         # 最多3个
#         filtered = filtered[:3]

#         # 如果0个酒店且poi不是城市名，用城市名重试
#         if not filtered and search_location != city:
#             print(f"   🔄 用城市名重试...")
#             try:
#                 raw_output2 = flyai.search_hotels_by_poi(
#                     dest_name=city, poi_name=city,
#                     check_in=check_in, check_out=check_out,
#                     max_price=int(hotel_budget_per_night * 1.5),
#                 )
#                 if raw_output2 and len(raw_output2) > 50:
#                     raw_for_ai2 = raw_output2[:8000]
#                     try:
#                         hotels2 = analyzer.analyze(raw_for_ai2, hotel_prompt)
#                         if isinstance(hotels2, dict):
#                             hotels2 = hotels2.get("hotels") or hotels2.get("data") or []
#                         if isinstance(hotels2, list):
#                             for h in hotels2:
#                                 avg = h.get("price_avg", 0)
#                                 if avg == 0:
#                                     avg = (h.get("price_min", 0) + h.get("price_max", 0)) / 2
#                                 h["price_avg"] = int(avg)
#                             filtered = [h for h in hotels2 if h.get("price_avg", 9999) <= hotel_budget_per_night * 1.5][:3]
#                     except Exception:
#                         pass
#             except Exception:
#                 pass

#         print(f"   ✅ 找到 {len(filtered)} 个酒店")
#         hotels_by_night.append({
#             "night": night_date,
#             "check_in": check_in,
#             "check_out": check_out,
#             "search_location": search_location,
#             "hotels": filtered,
#         })

#     total = sum(len(n["hotels"]) for n in hotels_by_night)
#     print(f"✅ 酒店搜索完成: {total} 个酒店选项")
#     return {"hotels_by_night": hotels_by_night}


"""Step 2: 飞猪酒店搜索 & 直接解析（无需AI）"""
import sys
import os
import json
import re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.flyai_client import FlyaiClient

def _parse_price(price_str: str) -> int:
    """从 '¥113' 或 '113元' 中提取数字"""
    match = re.search(r'\d+', price_str)
    return int(match.group()) if match else 0


def run(ctx: dict, xhs_result: dict, daily_plan: list = None) -> dict:
    """
    搜索酒店: 用 flyai search-hotels --poi-name 按景点位置搜索
    每晚选出2-3个酒店（直接解析，不使用AI）
    """
    city = ctx["city"]
    nights = ctx["nights"]
    night_dates = ctx["night_dates"]
    budget = ctx["budget"]
    flyai = FlyaiClient()

    attractions = xhs_result.get("attractions", [])
    hotels_by_night = []

    if nights == 0:
        print("ℹ️  当天来回，无需住宿")
        return {"hotels_by_night": []}

    hotel_budget_per_night = (budget * 0.4) / nights
    print(f"🏨 酒店搜索: {nights}晚, 每晚预算 ¥{hotel_budget_per_night:.0f}")

    for i, night_date in enumerate(night_dates):
        # 确定搜索位置
        search_location = city
        if daily_plan and i + 1 < len(daily_plan):
            next_day_points = daily_plan[i + 1].get("points", [])
            if next_day_points:
                search_location = next_day_points[0].get("name", search_location)
        elif attractions:
            idx = (i + 1) * 2
            if idx < len(attractions):
                search_location = attractions[idx]["name"]
            else:
                search_location = attractions[0]["name"]

        check_in = night_date
        check_out_dt = datetime.strptime(night_date, "%Y-%m-%d") + timedelta(days=1)
        check_out = check_out_dt.strftime("%Y-%m-%d")

        print(f"   🔎 第{i+1}晚({night_date}): 搜索{search_location}附近酒店...")

        raw_output = ""
        try:
            raw_output = flyai.search_hotels_by_poi(
                dest_name=city,
                poi_name=search_location,
                check_in=check_in,
                check_out=check_out,
                max_price=int(hotel_budget_per_night * 1.5),
            )
        except Exception as e:
            print(f"   ⚠️  search-hotels失败: {e}")

        hotels = []
        if raw_output.strip() and len(raw_output) > 50:
            try:
                data = json.loads(raw_output)
                item_list = data.get("data", {}).get("itemList", [])
                
                for item in item_list:
                    name = item.get("name", "").strip()
                    star = item.get("star", "")
                
                    
                    price_str = item.get("price", "¥0")
                    price = _parse_price(price_str)
                    
                    # 构建酒店对象
                    hotel = {
                        "name": name,
                        "type": star if star else "经济型",
                        "price_min": price,
                        "price_max": price,
                        "price_avg": price,
                        "distance": item.get("interestsPoi", ""),
                        "walking_time": "",  # 飞猪未提供步行时间，可留空或估算
                        "highlights": [item.get("brandName")] if item.get("brandName") else [],
                        "booking_link": item.get("detailUrl", ""),
                    }
                    hotels.append(hotel)

                # 按价格排序
                hotels.sort(key=lambda x: x["price_avg"])

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"   ⚠️  解析飞猪JSON失败: {e}")
                hotels = []

        # 按预算过滤
        filtered = [
            h for h in hotels
            if h["price_avg"] <= hotel_budget_per_night * 1.5
        ]

        # 如果无符合预算，取最便宜的2个
        if not filtered and hotels:
            filtered = hotels[:2]
            for h in filtered:
                h["note"] = "超出预算，仅供参考"

        # 最多取3个
        filtered = filtered[:3]

        # 如果仍无结果且之前用的是POI，尝试用城市名重试
        if not filtered and search_location != city:
            print(f"   🔄 用城市名'{city}'重试...")
            try:
                raw_output2 = flyai.search_hotels_by_poi(
                    dest_name=city, poi_name=city,
                    check_in=check_in, check_out=check_out,
                    max_price=int(hotel_budget_per_night * 1.5),
                )
                if raw_output2 and len(raw_output2) > 50:
                    data = json.loads(raw_output2)
                    item_list = data.get("data", {}).get("itemList", [])
                    retry_hotels = []
                    for item in item_list:
                        name = item.get("name", "").strip()
                        star = item.get("star", "")
                        price = _parse_price(item.get("price", "¥0"))
                        hotel = {
                            "name": name,
                            "type": star if star else "经济型",
                            "price_min": price,
                            "price_max": price,
                            "price_avg": price,
                            "distance": item.get("interestsPoi", ""),
                            "walking_time": "",
                            "highlights": [item.get("brandName")] if item.get("brandName") else [],
                            "booking_link": item.get("detailUrl", ""),
                        }
                        retry_hotels.append(hotel)
                    retry_hotels.sort(key=lambda x: x["price_avg"])
                    filtered = [
                        h for h in retry_hotels
                        if h["price_avg"] <= hotel_budget_per_night * 1.5
                    ][:3]
                    if not filtered and retry_hotels:
                        filtered = retry_hotels[:2]
                        for h in filtered:
                            h["note"] = "超出预算，仅供参考"
            except Exception as e:
                print(f"   ⚠️  城市名重试失败: {e}")

        print(f"   ✅ 找到 {len(filtered)} 个酒店")
        hotels_by_night.append({
            "night": night_date,
            "check_in": check_in,
            "check_out": check_out,
            "search_location": search_location,
            "hotels": filtered,
        })

    total = sum(len(n["hotels"]) for n in hotels_by_night)
    print(f"✅ 酒店搜索完成: {total} 个酒店选项")
    return {"hotels_by_night": hotels_by_night}