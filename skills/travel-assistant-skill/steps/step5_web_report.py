"""Step 5: Web报告生成"""
import sys
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEMPLATE_DIR, OUTPUT_DIR


def run(ctx: dict, xhs_result: dict, hotel_result: dict,
        route_result: dict, budget_plan: dict) -> str:
    """加载模板，填充数据，输出HTML"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template_path = os.path.join(TEMPLATE_DIR, "travel-report.html")
    if not os.path.isfile(template_path):
        print("❌ 模板文件不存在")
        return ""

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
        beijing_tz = ZoneInfo("Asia/Shanghai")
        now_beijing = datetime.now(beijing_tz)
    data = {
        "CITY": ctx["city"],
        "START_TIME": ctx["start_time"],
        "END_TIME": ctx["end_time"],
        "TOTAL_DAYS": str(ctx["total_days"]),
        "NIGHTS": str(ctx["nights"]),
        "BUDGET": str(ctx["budget"]),
        "GENERATE_TIME": now_beijing.strftime("%Y-%m-%d %H:%M:%S"),
    }

    map_data = route_result.get("map_data", {})
    data["AMAP_JSAPI_KEY"] = map_data.get("amap_key", "")
    data["AMAP_SECURITY_CODE"] = map_data.get("amap_security", "")
    data["MAP_CENTER_LAT"] = str(map_data.get("center_lat", 30.593))
    data["MAP_CENTER_LNG"] = str(map_data.get("center_lng", 114.305))
    data["MAP_ZOOM"] = str(map_data.get("zoom", 12))
    data["MAP_MARKERS_JSON"] = json.dumps(map_data.get("markers", []), ensure_ascii=False)
    data["MAP_POLYLINES_JSON"] = json.dumps(map_data.get("polylines", []), ensure_ascii=False)

    # 行程+交通合并HTML
    data["DAILY_ITINERARY_HTML"] = _build_itinerary_html(route_result, xhs_result)

    # 酒店HTML
    data["HOTELS_HTML"] = _build_hotels_html(hotel_result)

    # 交通详情已合并到行程，这里留空
    data["TRANSPORT_HTML"] = ""

    # 预算HTML（3项：住宿/交通/其他）
    data["BUDGET_HTML"] = _build_budget_html(budget_plan)

    data["WARNINGS_HTML"] = _build_warnings_html(xhs_result)
    data["FOODS_HTML"] = _build_foods_html(xhs_result)

    html = template
    for key, value in data.items():
        html = html.replace(f"{{{{{key}}}}}", value)

    out_file = os.path.join(
    OUTPUT_DIR,
    f"{ctx['city']}的{ctx['start_time']}到{ctx['end_time']}的旅游规划_生成时间{now_beijing.strftime('%Y%m%d_%H%M')}.html"
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 报告已生成: {out_file}")
    return out_file


def _build_route_inline(route: dict) -> str:
    """生成单条路线的内联HTML（用于行程卡片内）"""
    dist_km = route.get("distance", 0) / 1000
    dur_min = route.get("duration", 0) // 60
    cost = route.get("cost", 0)
    segments_html = ""
    for seg in route.get("segments", []):
        icon = {"walking": "🚶", "bus": "🚌", "subway": "🚇", "estimate": "📐"}.get(seg.get("type"), "→")
        segments_html += f'<span class="seg-chip">{icon} {seg.get("instruction","")}</span> '
    return f'''<div class="route-inline">
        <div class="route-arrow">↘ {route.get("from","")} → {route.get("to","")}</div>
        <div class="route-brief">📏{dist_km:.1f}km ⏱️{dur_min}分钟 💰¥{cost:.0f}</div>
        <div class="route-segs">{segments_html}</div>
    </div>'''


def _build_itinerary_html(route_result: dict, xhs_result: dict) -> str:
    """行程+交通合并展示"""
    daily_plan = route_result.get("daily_plan", [])
    attractions = {a["name"]: a for a in xhs_result.get("attractions", [])}
    day_colors = ["#1890ff", "#52c41a", "#fa8c16", "#f5222d", "#722ed1",
                  "#13c2c2", "#eb2f96", "#faad14"]

    html = ""
    global_seq = 1  # 全局序号
    for dp in daily_plan:
        day = dp["day"]
        color = day_colors[(day - 1) % len(day_colors)]
        routes = dp.get("routes", [])

        html += f'''<div class="day-card" style="border-left:4px solid {color}">
            <h3 style="color:{color}">第{day}天 ({dp["date"]})</h3>
            <div class="timeline">'''

        for pi, p in enumerate(dp["points"]):
            is_hotel = p.get("type") == "酒店"
            if is_hotel:
                icon = "🏨"
                seq_label = ""
            else:
                icon = "📍"
                seq_label = f'<span class="seq-num" style="background:{color}">{global_seq}</span>'
                global_seq += 1

            tips = attractions.get(p["name"], {}).get("tips", "")
            ticket = attractions.get(p["name"], {}).get("ticket_price", 0)
            tips_html = f'<div class="tips">💡 {tips}</div>' if tips else ""
            ticket_html = f'<span class="ticket-badge">🎫 ¥{ticket}</span>' if ticket else ""

            html += f'''<div class="timeline-item">
                <div class="timeline-dot" style="background:{color}"></div>
                <div class="timeline-content">
                    <h4>{seq_label}{icon} {p["name"]}</h4>
                    <span class="type-badge">{p.get("type","景点")}</span> {ticket_html}
                    {tips_html}
                </div>
            </div>'''

            # 在当前景点后插入到下一个地点的交通路线
            if pi < len(routes):
                html += f'<div class="timeline-route">{_build_route_inline(routes[pi])}</div>'

        html += '</div></div>'
    return html


def _build_hotels_html(hotel_result: dict) -> str:
    hotels_by_night = hotel_result.get("hotels_by_night", [])
    if not hotels_by_night:
        return "<p>当天来回，无需住宿</p>"

    html = ""
    for night_info in hotels_by_night:
        html += f'<div class="hotel-night"><h3>🏨 {night_info["night"]} 晚住宿</h3>'
        for h in night_info.get("hotels", []):
            link = h.get("booking_link", "")
            link_html = f'<a href="{link}" target="_blank" class="btn-book">预订</a>' if link else ""
            highlights = " · ".join(h.get("highlights", []))
            note = h.get("note", "")
            note_html = f'<span class="note-badge">{note}</span>' if note else ""
            html += f'''<div class="hotel-card">
                <h4>{h.get("name","")} {note_html}</h4>
                <div class="hotel-meta">
                    <span class="badge">{h.get("type","")}</span>
                    <span>💰 ¥{h.get("price_min","?")}-{h.get("price_max","?")} (均价¥{h.get("price_avg","?")})</span>
                    <span>📏 {h.get("distance","")}</span>
                    <span>🚶 {h.get("walking_time","")}</span>
                </div>
                <div class="hotel-highlights">{highlights}</div>
                {link_html}
            </div>'''
        html += '</div>'
    return html


def _build_budget_html(budget_plan: dict) -> str:
    """预算：只有住宿、交通、其他三项"""
    b = budget_plan
    items = [
        ("住宿", b.get("hotel", 0), b.get("breakdown", {}).get("hotel_percent", 0), "🏨"),
        ("交通", b.get("transport", 0), b.get("breakdown", {}).get("transport_percent", 0), "🚌"),
        ("其他", b.get("other", 0), b.get("breakdown", {}).get("other_percent", 0), "📦"),
    ]
    html = '<div class="budget-grid">'
    for name, amount, pct, icon in items:
        html += f'''<div class="budget-item">
            <div class="budget-icon">{icon}</div>
            <div class="budget-name">{name}</div>
            <div class="budget-amount">¥{amount}</div>
            <div class="budget-bar"><div class="budget-fill" style="width:{pct}%"></div></div>
            <div class="budget-pct">{pct}%</div>
        </div>'''
    html += f'''<div class="budget-total">
        <div class="budget-icon">💎</div>
        <div class="budget-name">总计</div>
        <div class="budget-amount">¥{b.get("total",0)}</div>
    </div></div>'''
    return html


def _build_warnings_html(xhs_result: dict) -> str:
    warnings = xhs_result.get("warnings", [])
    if not warnings:
        return ""
    html = '<div class="warnings-list">'
    for w in warnings:
        sev = w.get("severity", "medium")
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sev, "⚠️")
        html += f'<div class="warning-item severity-{sev}">{icon} {w.get("content","")}</div>'
    html += '</div>'
    return html


def _build_foods_html(xhs_result: dict) -> str:
    foods = xhs_result.get("foods", [])
    if not foods:
        return ""
    html = '<div class="foods-grid">'
    for f in foods:
        html += f'''<div class="food-card">
            <h4>🍜 {f.get("name","")}</h4>
            <p>{f.get("description","")}</p>
            <div class="food-meta">
                <span>📍 {f.get("location","")}</span>
                <span>💰 {f.get("price_range","")}</span>
            </div>
        </div>'''
    html += '</div>'
    return html
