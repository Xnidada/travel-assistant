"""Step 1: 小红书实时搜索 & 模型分析（增强容错 + 限流版）"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.xhs_client import XhsClient
from lib.ai_analyzer import analyzer

# ===== 新增：全局请求时间控制 =====
_last_request_time = 0
_REQUEST_INTERVAL = 3  # 至少间隔3秒


def _rate_limit():
    """确保两次请求之间至少间隔 _REQUEST_INTERVAL 秒"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _REQUEST_INTERVAL:
        sleep_time = _REQUEST_INTERVAL - elapsed
        print(f"   ⏳ 等待 {sleep_time:.1f} 秒以满足请求间隔...")
        time.sleep(sleep_time)
    _last_request_time = time.time()


# ===== 必须包含以下两个函数！不要用注释代替！=====
def _parse_like_count(count):
    """安全解析点赞数（支持 '1.2万'、'1200' 等格式）"""
    if isinstance(count, (int, float)):
        return int(count)
    if isinstance(count, str):
        count = count.strip()
        if not count:
            return 0
        # 处理 "1.2万" → 12000
        if "万" in count:
            try:
                num = float(count.replace("万", "").replace(",", ""))
                return int(num * 10000)
            except ValueError:
                pass
        # 直接数字
        try:
            return int(count.replace(",", ""))
        except ValueError:
            return 0
    return 0


def _extract_note_summary(detail_raw: str, fid: str) -> str:
    """从 detail_raw 中提取笔记摘要，失败则抛出异常"""
    try:
        outer = json.loads(detail_raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}")

    # ✅ 检查 JSON-RPC 错误
    if "error" in outer:
        msg = outer["error"].get("message", "Unknown RPC error")
        raise ValueError(f"API failed: {msg}")

    # ✅ 检查 result 是否存在
    result = outer.get("result")
    if not result:
        raise ValueError("Missing 'result' field in response")

    # ✅ 检查 content 是否存在且非空
    content_list = result.get("content")
    if not content_list or not isinstance(content_list, list) or len(content_list) == 0:
        raise ValueError("Empty or missing 'content' in result")

    first_item = content_list[0]
    if not isinstance(first_item, dict):
        raise ValueError("First content item is not a dict")

    inner_text = first_item.get("text", "")
    if not inner_text or not inner_text.strip():
        raise ValueError("Empty 'text' in content")

    # 尝试解析 inner_text（它应该是一个 JSON 字符串）
    try:
        inner = json.loads(inner_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse inner text as JSON: {e}")

    note_data = inner.get("data", {}).get("note")
    if not note_data:
        raise ValueError("Missing note data in inner JSON")

    comments = inner.get("data", {}).get("comments", {}).get("list", []) or []

    title = note_data.get("title", "")
    desc = note_data.get("desc", "")
    author = note_data.get("user", {}).get("nickname", "匿名用户")
    likes = note_data.get("interactInfo", {}).get("likedCount", "0")

    note_summary = f"[笔记] 标题: {title}\n作者: {author} (点赞: {likes})\n内容: {desc}\n"

    # 提取高赞评论
    sorted_comments = sorted(
        comments,
        key=lambda c: _parse_like_count(c.get("likeCount", 0)),
        reverse=True
    )
    top_comments = []
    for cmt in sorted_comments[:5]:
        content = cmt.get("content", "").strip()
        if not content:
            continue
        sub_cmts = cmt.get("subComments", []) or []
        best_reply = ""
        if sub_cmts:
            try:
                best_sub = max(sub_cmts, key=lambda sc: _parse_like_count(sc.get("likeCount", 0)))
                reply_content = best_sub.get('content', '').strip()
                if reply_content:
                    best_reply = f"\n  ↳ 回复: {reply_content}"
            except Exception:
                pass
        top_comments.append(f"- {content}{best_reply}")

    if top_comments:
        note_summary += "热门评论:\n" + "\n".join(top_comments)

    return note_summary
    # 提取高赞评论
    sorted_comments = sorted(
        comments,
        key=lambda c: _parse_like_count(c.get("likeCount", 0)),
        reverse=True
    )
    top_comments = []
    for cmt in sorted_comments[:5]:
        content = cmt.get("content", "").strip()
        if not content:
            continue
        sub_cmts = cmt.get("subComments", []) or []
        best_reply = ""
        if sub_cmts:
            try:
                best_sub = max(sub_cmts, key=lambda sc: _parse_like_count(sc.get("likeCount", 0)))
                reply_content = best_sub.get('content', '').strip()
                if reply_content:
                    best_reply = f"\n  ↳ 回复: {reply_content}"
            except Exception:
                pass
        top_comments.append(f"- {content}{best_reply}")

    if top_comments:
        note_summary += "热门评论:\n" + "\n".join(top_comments)

    return note_summary


# ===== 主函数 =====
def run(ctx: dict) -> dict:
    city = ctx["city"]
    xhs = XhsClient()

    # 1. 搜索攻略（加限流）
    print(f"📖 搜索小红书: {city}旅游攻略 ...")
    try:
        _rate_limit()  # ←←← 关键：调用前限流
        search_raw = xhs.search_feeds(f"{city}旅游攻略")
    except Exception as e:
        print(f"❌ 小红书搜索失败: {e}")
        return {"attractions": [], "foods": [], "warnings": []}

    # 2. 解析搜索结果（无网络请求，无需限流）
    print("🔍 解析小红书搜索结果，提取笔记列表...")
    feeds = []
    try:
        outer = json.loads(search_raw)
        inner_text = outer["result"]["content"][0]["text"]
        inner = json.loads(inner_text)
        raw_feeds = inner.get("feeds", [])
        for item in raw_feeds:
            if item.get("modelType") == "note":
                note = item["noteCard"]
                feeds.append({
                    "feed_id": item["id"],
                    "xsec_token": item["xsecToken"],
                    "title": note["displayTitle"]
                })
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        print(f"⚠️  解析小红书搜索结果失败: {e}")

    print(f"   找到 {len(feeds)} 条候选笔记")

    if not feeds:
        return {"attractions": [], "foods": [], "warnings": []}

    # 3. 获取详情：最多尝试前15篇，直到成功5篇
    details_text_list = []
    max_attempts = min(15, len(feeds))
    success_count = 0

    for i in range(max_attempts):
        if success_count >= 5:
            break
            
        feed = feeds[i]
        fid = feed.get("feed_id", "")
        token = feed.get("xsec_token", "")
        if not fid or not token:
            continue

        # 单篇最多重试3次
        for retry in range(3):
            try:
                print(f"   📄 尝试获取笔记 {success_count+1}/5 ({i+1}/{max_attempts}): {feed.get('title', fid[:20])}... (重试 {retry+1}/3)")
                
                _rate_limit()  # ←←← 关键：每次 get_feed_detail 前限流
                detail_raw = xhs.get_feed_detail(fid, token)
                
                if not detail_raw or not detail_raw.strip():
                    raise ValueError("Empty response")

                summary = _extract_note_summary(detail_raw, fid)
                details_text_list.append(summary)
                success_count += 1
                break  # 成功则跳出重试循环

            except Exception as e:
                print(f"      ⚠️  第 {retry+1} 次失败: {e}")
                if retry < 2:
                    # 注意：重试前不 sleep(1)，因为下一次 _rate_limit() 会自动等待
                    pass
                else:
                    print(f"      ❌ 放弃笔记 {fid}，继续下一条")

    print(f"✅ 共获取 {len(details_text_list)} 篇有效笔记")
    if not details_text_list:
        print("⚠️  未获取到任何有效笔记内容")
        return {"attractions": [], "foods": [], "warnings": []}

    # 4. 模型分析
    print("🤖 模型分析笔记内容，提取景点/美食/避雷...")
    all_text = "\n\n---笔记分隔---\n\n".join(details_text_list)

    analysis_prompt = f"""以下是{city}的{len(details_text_list)}篇小红书旅游攻略笔记的完整内容。
请仔细分析并提取以下信息，返回JSON:
{{
  "attractions": [
    {{"name": "景点名", "description": "简述(20字内)", "visit_time": "建议游览时间(如2-3小时)", "ticket_price": 门票价格(数字,免费为0), "tips": "怎么玩好玩(具体建议)", "popularity": 热度1-10}}
  ],
  "foods": [
    {{"name": "美食名", "description": "描述", "location": "在哪吃", "price_range": "价格区间(如15-30元)"}}
  ],
  "warnings": [
    {{"content": "避雷建议内容", "severity": "high/medium/low"}}
  ]
}}

要求:
- 只提取明确提到的信息，不要编造
- popularity基于提及频率和推荐程度(1-10)
- tips要具体实用（如"傍晚去光线最好"、"租自行车环湖"、"提前预约"）
- 景点至少提取5个，最多15个
- 美食至少提取3个
- 避雷建议全部提取"""

    try:
        result = analyzer.analyze(all_text, analysis_prompt)
        if isinstance(result, list):
            result = {"attractions": result, "foods": [], "warnings": []}
    except Exception as e:
        print(f"❌ 模型分析笔记失败: {e}")
        result = {"attractions": [], "foods": [], "warnings": []}

    result.setdefault("attractions", [])
    result.setdefault("foods", [])
    result.setdefault("warnings", [])

    print(f"✅ 小红书分析完成: {len(result['attractions'])}个景点, {len(result['foods'])}个美食, {len(result['warnings'])}条避雷")
    return result