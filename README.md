# PaperClaw - 领域论文专家智能体生成框架

> 基于 OpenClaw 的论文自动检索、总结、评估智能体框架。
> 可为任意研究领域生成专门的论文专家智能体。

<div align="center">

[![OpenClaw](https://img.shields.io/badge/OpenClaw-Agent-blue)](https://github.com/openclaw/openclaw)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

[中文](README.md) | [English](README_EN.md)
## 🎯 项目定位

PaperClaw 是一个**领域论文专家智能体生成框架**：

- **如果你已有明确的研究领域** → 使用 `skills/paper-expert-generator/` 快速生成专属智能体
- **如果你想了解如何工作** → 查看 `agents/surrogate-modeling/` 作为完整示例

---

## 📁 目录结构

```
PaperClaw/
├── skills/
│   └── paper-expert-generator/     # Skill：生成领域论文专家智能体
│       ├── SKILL.md               # 使用指南（8步工作流）
│       ├── scripts/
│       │   └── init_domain_agent.py   # 自动脚手架脚本
│       ├── references/
│       │   ├── domain-adaptation-guide.md  # 8个领域关键词/评分维度示例
│       │   └── agent-template-guide.md     # AGENT.md 撰写指南
│       └── assets/templates/      # 模板文件
│           ├── AGENT.md.template
│           ├── models.json
│           └── schedules.json
│
├── agents/
│   └── surrogate-modeling/        # Demo：3D几何代理建模领域专家
│       ├── agent/
│       │   ├── AGENT.md          # Agent 角色定义（Scientific ML + 3D几何）
│       │   ├── models.json       # LLM 配置
│       │   └── schedules.json    # 定时任务（每日20:00 + 周日10:00）
│       ├── skills/               # 5个核心技能
│       │   ├── arxiv-search/     # arXiv 批量搜索 + 去重
│       │   ├── semantic-scholar/ # 引用数据 API
│       │   ├── paper-review/     # 论文评估 + 安全写入
│       │   ├── daily-search/     # 每日自动检索
│       │   └── weekly-report/    # 周报生成
│       ├── docs/
│       │   ├── architecture.md   # 系统架构详解
│       │   └── evaluation_system.md  # 评分系统详解
│       └── examples/             # 示例数据（DeepONet评分报告）
│
└── [项目文档]
    ├── README.md                 # 本文档（中文）
    ├── README_EN.md              # 英文文档
    ├── INSTALLATION.md           # 安装指南
    ├── CONFIGURATION.md          # 配置说明
    └── QUICKSTART.md             # 快速入门
```

---

## 🚀 快速开始

### 方式一：为已有领域生成智能体（推荐）

如果你已有明确的研究领域，使用 `paper-expert-generator` skill：

```bash
# 1. 运行脚手架脚本
python skills/paper-expert-generator/scripts/init_domain_agent.py \
  --domain "bioinfo-ml" \
  --output ~/agents/bioinfo-ml \
  --paperclaw-skills ./skills

# 2. 根据 prompts 填写 AGENT.md 中的 {{占位符}}
# 3. 设置 API key
# 4. 启动 OpenClaw，指向新 agent
```

### 方式二：直接使用 Demo（了解工作流程）

查看 `agents/surrogate-modeling/` 作为完整示例：

```bash
cd agents/surrogate-modeling

# 每日检索（手动触发）
python skills/daily-search/scripts/daily_paper_search.py --top 3

# 周报生成
python skills/weekly-report/scripts/generate_weekly_report_v2.py
```

---

## 🏗️ 系统架构

### 单 Agent 内部架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PaperClaw Agent                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │daily-search│ │arxiv-search│ │paper-review│ │weekly-rpt│ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  workspace/papers/                                          │
│  ├── {paper}/metadata.json  ← 结构化评分数据                │
│  ├── {paper}/summary.md     ← 深度总结                      │
│  ├── {paper}/scores.md      ← 评分报告                      │
│  └── evaluated_papers.json  ← 去重索引                      │
└─────────────────────────────────────────────────────────────┘
```

### 从 Skill 到 Agent 的生成流程

```
┌────────────────────────┐      ┌──────────────────────────┐
│ paper-expert-generator │ ──→  │  Your Domain Agent       │
│        Skill           │      │  (bioinfo-ml/cv-3d/...)  │
└────────────────────────┘      └──────────────────────────┘
        │                                    │
        ├── init_domain_agent.py            ├── agent/AGENT.md
        ├── domain-adaptation-guide.md      ├── agent/models.json
        ├── agent-template-guide.md         ├── agent/schedules.json
        └── templates/                      └── skills/
                                              (5个技能，按需适配)
```

---

## 📊 核心功能

| 功能 | 说明 | 触发方式 |
|------|------|---------|
| 🔍 **每日检索** | 批量搜索 arXiv，自动去重，精选 Top 3 | 每天 20:00 (Asia/Singapore) |
| 📝 **深度总结** | 回答 10 个核心问题，生成 summary.md | 检索后自动执行 |
| 📊 **四维评分** | 领域定制维度 + Date-Citation 权衡 | 总结后自动执行 |
| 📰 **周报生成** | Top 3 精选论文报告，推送通知 | 每周日 10:00 |

---

## 🤖 评分体系

### 四维基础评分 + Date-Citation 影响力评分

```
最终评分 = 四维基础评分 × 0.9 + 影响力评分 × 0.1

四维基础评分 = (维度1 + 维度2 + 维度3 + 维度4) / 4
```

**Date-Citation 调整因子**（示例，可领域定制）：
- ≤3个月新论文：+0.2
- 3-24个月 + 引用≥50：+0.5
- >24个月 + 引用≥200：+0.5
- 引用密度≥10次/月：额外 +0.2

**领域定制评分维度示例**：
- **Scientific ML**（默认）：工程应用、架构创新、理论贡献、可靠性
- **生物信息学**：生物学合理性、计算可扩展性、基准质量、转化潜力
- **计算机视觉**：架构创新、基准性能、泛化能力、实用性

详见 `skills/paper-expert-generator/references/domain-adaptation-guide.md`

---

## 🛠️ 创建新领域智能体

参考 `skills/paper-expert-generator/SKILL.md` 的 8 步工作流：

1. **领域访谈** — 收集研究域、子方向、方法论、排除词
2. **关键词库** — 构建 arXiv `ti:` 查询
3. **评分维度** — 设计4个领域专属评分维度
4. **脚手架** — 运行 `init_domain_agent.py`
5. **写 AGENT.md** — 填充角色定位、关键词、4大任务
6. **改 SKILL.md** — 适配关键词列表和评分维度
7. **配置模型** — 填入 API credentials
8. **验证交付** — checklist 确认

---

## 🔄 更新日志

### v2.0.0 (2026-03-11) - 框架化重构

**🎯 架构升级**
- ✅ 新增 `paper-expert-generator` Skill，支持任意研究领域
- ✅ 目录重构：`skills/`（可复用组件） + `agents/`（领域示例）
- ✅ `surrogate-modeling` 作为首个 Demo Agent（Scientific ML + 3D几何）

### v1.1.0 (2026-03-04) - 架构优化

**🚀 核心改进**
- ✅ 消除正则解析依赖，从 JSON 直接读取结构化数据
- ✅ 安全并发写入（文件锁 + 去重检查）
- ✅ 强制思维链（`<think>` 标签）

### v1.0.0 (2026-03-01) - 初始版本

- ✅ arXiv 论文自动检索
- ✅ 论文深度总结（10个问题）
- ✅ 四维评分系统
- ✅ 周报自动生成

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**贡献方向**：
- 新的领域适配示例（添加到 `agents/`）
- `paper-expert-generator` Skill 的功能增强
- 更多领域的关键词库和评分维度（`domain-adaptation-guide.md`）

---

## 📄 许可证

MIT License

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star！**

</div>
