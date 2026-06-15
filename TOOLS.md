# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Travel Assistant Configuration

**重要规则：** 当收到 travel 命令时，直接调用 travel-assistant-skill，不要自行编写计划。

### travel-assistant-skill 调用方式
```bash
cd /root/.openclaw/skills/travel-assistant-skill
./travel --city <城市> --start_time YYYY-MM-DD_HH:MM --end_time YYYY-MM-DD_HH:MM --cost <预算>
```

### 已知问题
- 小红书登录状态异常（需要管理员配置）
- 技能仍然可以生成基本报告

### 输出位置
- 报告生成在：/root/.openclaw/skills/travel-assistant-skill/outs/
- 文件名格式：<城市>_旅行规划_YYYYMMDD_HHMM.html

## What Goes Here

Things like:

- API endpoint overrides
- Custom model names
- Default city or timezone
- Anything environment-specific

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
