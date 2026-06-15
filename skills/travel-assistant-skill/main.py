#!/usr/bin/env python3
"""旅伴  主流程"""
import sys
import os
import time
import argparse

# 确保可以 import 同目录模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "lib"))
sys.path.insert(0, os.path.join(BASE_DIR, "steps"))

from steps import step0_precheck, step1_xhs_search, step2_hotel_search
from steps import step3_route_plan, step4_budget, step5_web_report


def main():
    parser = argparse.ArgumentParser(description="旅伴 ")
    parser.add_argument("--city", required=True, help="旅行城市")
    parser.add_argument("--start_time", required=True, help="开始时间 YYYY-MM-DD_HH:MM")
    parser.add_argument("--end_time", required=True, help="结束时间 YYYY-MM-DD_HH:MM")
    parser.add_argument("--cost", required=True, type=int, help="总预算(元)")
    args = parser.parse_args()

    total_start = time.time()
    print("=" * 60)
    print(f"🚀 旅伴  启动")
    print(f"📍 {args.city} | {args.start_time} → {args.end_time} | ¥{args.cost}")
    print("=" * 60)

    # Step 0: 预检查
    print("\n━━ Step 0: 参数解析 & 预检查 ━━")
    ctx = step0_precheck.run(args.city, args.start_time, args.end_time, args.cost)

    # Step 1: 小红书搜索
    print("\n━━ Step 1: 小红书攻略搜索 ━━")
    xhs_result = step1_xhs_search.run(ctx)

    if not xhs_result.get("attractions"):
        print("❌ 未找到任何景点信息，无法继续规划")
        sys.exit(1)

    # Step 3 先行（路线规划，给酒店搜索提供位置信息）
    # 先做初步路线规划（不含酒店）
    print("\n━━ Step 3a: 初步路线规划（确定酒店搜索位置）━━")
    # 临时hotel_result
    temp_hotel = {"hotels_by_night": []}
    route_result = step3_route_plan.run(ctx, xhs_result, temp_hotel)

    # Step 2: 酒店搜索
    print("\n━━ Step 2: 飞猪酒店搜索 ━━")
    hotel_result = step2_hotel_search.run(
        ctx, xhs_result,
        daily_plan=route_result.get("daily_plan", []),
    )

    # Step 3: 完整路线规划（含酒店）
    print("\n━━ Step 3b: 完整路线规划（含酒店+交通）━━")
    route_result = step3_route_plan.run(ctx, xhs_result, hotel_result)

    # Step 4: 预算
    print("\n━━ Step 4: 预算分配 ━━")
    budget_plan = step4_budget.run(ctx, hotel_result, route_result, xhs_result)

    # Step 5: Web报告
    print("\n━━ Step 5: 生成Web报告 ━━")
    report_path = step5_web_report.run(ctx, xhs_result, hotel_result, route_result, budget_plan)

    # 完成
    elapsed = time.time() - total_start
    print("\n" + "=" * 60)
    print(f"🎉 旅行规划完成！耗时 {elapsed:.0f} 秒")
    print(f"📄 报告: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
