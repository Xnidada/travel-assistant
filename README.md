# 🗺️ 旅伴 Travel Assistant

> AI 驱动的智能旅行规划助手 —— 整合小红书攻略、飞猪酒店、高德地图，一键生成实用行程

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🔍 **小红书攻略搜索** | 自动抓取真实用户分享的旅行经验和避雷信息 |
| 🏨 **飞猪酒店搜索** | 按价格、位置筛选性价比最优住宿 |
| 🗺️ **智能路线规划** | 基于 TSP 算法优化每日行程路线，减少折返 |
| 💰 **预算自动分配** | 合理分配交通、住宿、餐饮、门票等开支 |
| 📊 **可视化报告** | 生成交互式 HTML 旅行规划报告，含地图标注 |

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- Bash
- [OpenClaw](https://github.com/openclaw/openclaw) 已安装并配置

### 第一步：安装依赖技能（Skills）

本项目依赖以下 OpenClaw 技能，请通过 [ClawHub](https://clawhub.com) 安装：

```bash
# 安装 ClawHub CLI（如果尚未安装）
npm install -g clawhub

# 安装所需的技能
clawhub install amap-lbs-skill      # 高德地图 LBS 服务
clawhub install amap-jsapi-skill    # 高德 JS API 参考文档
clawhub install flyai               # 飞猪旅行搜索
clawhub install xiaohongshu         # 小红书数据抓取
```

安装完成后，技能将位于 `~/.openclaw/skills/` 目录下。

### 第二步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 第三步：配置 API 密钥

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env`，填入你的 API 密钥：
   - 📍 [高德地图开放平台](https://console.amap.com/dev/key/app) — 申请 Web 服务 Key 和 JS API Key
   - 🛒 [飞猪开放平台](https://open.taobao.com/) — 酒店搜索（需申请 `flyai` CLI）

3. 配置模型 API（可选）：
```bash
export MAAS_API_KEY="your_api_key"
export MAAS_API_URL="your_api_url"
```

### 第四步：运行

```bash
cd skills/travel-assistant-skill

./travel --city 武汉 --start_time 2026-07-01_09:00 --end_time 2026-07-02_18:00 --cost 1500
```

**参数说明：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `--city` | 目的地城市 | 武汉、成都、上海 |
| `--start_time` | 出发时间 | `2026-07-01_09:00` |
| `--end_time` | 返回时间 | `2026-07-02_18:00` |
| `--cost` | 总预算（元） | 1500 |

规划完成后，报告将生成在 `outs/` 目录下，用浏览器打开 HTML 文件即可查看。

## 📁 项目结构

```
├── AGENTS.md                        # AI Agent 行为配置
├── SOUL.md                          # AI 助手人格定义
├── IDENTITY.md                      # 身份信息
├── .env.example                     # 环境变量模板
├── requirements.txt                 # Python 依赖
│
└── skills/
    └── travel-assistant-skill/      # 🎯 核心规划引擎
        ├── travel                   # Bash 启动脚本
        ├── main.py                  # 主程序入口
        ├── config.py                # 配置管理（读取环境变量）
        ├── lib/
        │   ├── amap_client.py       # 高德地图 API 客户端
        │   ├── xhs_client.py        # 小红书数据抓取
        │   ├── flyai_client.py      # 飞猪酒店搜索
        │   ├── ai_analyzer.py       # AI 行程分析与生成
        │   └── tsp_solver.py        # TSP 路径优化算法
        ├── steps/
        │   ├── step0_precheck.py    # 环境预检查
        │   ├── step1_xhs_search.py  # 小红书攻略搜索
        │   ├── step2_hotel_search.py # 酒店搜索
        │   ├── step3_route_plan.py  # 路线规划
        │   ├── step4_budget.py      # 预算分配
        │   └── step5_web_report.py  # HTML 报告生成
        └── templates/
            └── travel-report.html   # 报告 HTML 模板
```

## 🔗 依赖技能说明

本项目依赖以下由社区维护的 OpenClaw 技能，**请勿将这些技能包含在本仓库中**：

| 技能 | 用途 | 安装命令 |
|------|------|----------|
| `amap-lbs-skill` | 高德地图 POI 搜索、路线规划 | `clawhub install amap-lbs-skill` |
| `amap-jsapi-skill` | 高德地图 JS API 文档参考 | `clawhub install amap-jsapi-skill` |
| `flyai` | 飞猪酒店/机票搜索 | `clawhub install flyai` |
| `xiaohongshu` | 小红书攻略数据抓取 | `clawhub install xiaohongshu` |

## ⚙️ 工作流程

```
用户输入 (城市/时间/预算)
    │
    ▼
┌─────────────┐
│ Step 0 预检查 │  验证 API Key、依赖技能是否安装
└──────┬──────┘
       ▼
┌─────────────┐
│ Step 1 小红书 │  搜索攻略 → 提取景点、美食、避雷信息
└──────┬──────┘
       ▼
┌─────────────┐
│ Step 2 飞猪   │  搜索酒店 → 按价格/位置排序推荐
└──────┬──────┘
       ▼
┌─────────────┐
│ Step 3 路线   │  高德坐标 → TSP 优化 → 每日行程
└──────┬──────┘
       ▼
┌─────────────┐
│ Step 4 预算   │  分配交通/住宿/餐饮/门票
└──────┬──────┘
       ▼
┌─────────────┐
│ Step 5 报告   │  生成 HTML 可视化报告
└─────────────┘
```

## ⚠️ 注意事项

- **酒店价格仅供参考**，实际价格以预订时为准
- **小红书抓取**依赖登录状态，如遇问题请检查 cookies 配置
- **高德 API** 有调用频率限制，程序已内置限流机制（1.2s 间隔）
- 请勿将 `.env` 文件提交到公开仓库

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  🗺️ 让每一次旅行都有靠谱的规划<br>
  <sub>Built with ❤️ by Travel Companion</sub>
</p>
