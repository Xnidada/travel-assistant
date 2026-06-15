"""Step 0: 参数解析 & 预检查"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.xhs_client import XhsClient


def run(city: str, start_time: str, end_time: str, cost: int) -> dict:
    """解析参数并预检查"""
    # 解析时间
    try:
        start_dt = datetime.strptime(start_time, "%Y-%m-%d_%H:%M")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d_%H:%M")
    except ValueError:
        raise ValueError("时间格式应为 YYYY-MM-DD_HH:MM，如 2026-04-16_12:00")

    if start_dt >= end_dt:
        raise ValueError("开始时间必须早于结束时间")

    # 计算总天数（用于显示，向上取整到整天）
    delta = end_dt - start_dt
    total_days = delta.days + (1 if delta.seconds > 0 else 0)
    if total_days < 1:
        total_days = 1

    # ✅ 核心逻辑：住宿晚数 = 日历日差（自动排除最后一天）
    nights = (end_dt.date() - start_dt.date()).days
    nights = max(0, nights)  # 确保非负

    # 检查小红书登录
    print("🔍 检查小红书登录状态...")
    xhs = XhsClient()
    xhs_ok = False
    try:
        xhs_ok = xhs.check_login()
    except Exception as e:
        print(f"⚠️  小红书检查异常: {e}")

    if not xhs_ok:
        print("❌ 小红书状态异常，请联系管理员")
        # 不终止，允许继续但标记状态

    # 生成每晚住宿的日期（从 start_date 开始，连续 nights 天）
    night_dates = []
    for i in range(nights):
        night_date = start_dt.date() + timedelta(days=i)
        night_dates.append(str(night_date))

    result = {
        "city": city,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "start_time": start_time,
        "end_time": end_time,
        "total_days": total_days,
        "nights": nights,
        "night_dates": night_dates,
        "budget": cost,
        "xhs_ok": xhs_ok,
    }

    print(f"✅ 参数解析完成: {city} | {start_time} → {end_time} | {total_days}天{nights}晚 | 预算¥{cost}")
    return result