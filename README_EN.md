# PaperClaw - Domain Paper Expert Agent Generator Framework

> An OpenClaw-based agent framework for automated paper search, summarization, and evaluation.
> Generate specialized paper expert agents for any research domain.

<div align="center">

[![OpenClaw](https://img.shields.io/badge/OpenClaw-Agent-blue)](https://github.com/openclaw/openclaw)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

[中文](README.md) | [English](README_EN.md)

---

## 🎯 Project Overview

PaperClaw is a **domain-specific paper expert agent generator framework**:

- **If you have a specific research domain** → Use `skills/paper-expert-generator/` to quickly create your own agent
- **If you want to understand how it works** → Check `agents/surrogate-modeling/` as a complete example

---

## 📁 Directory Structure

```
PaperClaw/
├── skills/
│   └── paper-expert-generator/     # Skill: Generate domain paper expert agents
│       ├── SKILL.md               # Usage guide (8-step workflow)
│       ├── scripts/
│       │   └── init_domain_agent.py   # Automated scaffolding script
│       ├── references/
│       │   ├── domain-adaptation-guide.md  # Keyword/scoring examples for 8 domains
│       │   └── agent-template-guide.md     # AGENT.md authoring guide
│       └── assets/templates/      # Template files
│           ├── AGENT.md.template
│           ├── models.json
│           └── schedules.json
│
├── agents/
│   └── surrogate-modeling/        # Demo: 3D Geometry Surrogate Modeling Expert
│       ├── agent/
│       │   ├── AGENT.md          # Agent role definition (Scientific ML + 3D Geometry)
│       │   ├── models.json       # LLM configuration
│       │   └── schedules.json    # Scheduled tasks (Daily 20:00 + Sunday 10:00)
│       ├── skills/               # 5 core skills
│       │   ├── arxiv-search/     # arXiv batch search + deduplication
│       │   ├── semantic-scholar/ # Citation data API
│       │   ├── paper-review/     # Paper evaluation + safe write
│       │   ├── daily-search/     # Daily automated search
│       │   └── weekly-report/    # Weekly report generation
│       ├── docs/
│       │   ├── architecture.md   # System architecture details
│       │   └── evaluation_system.md  # Scoring system details
│       └── examples/             # Sample data (DeepONet evaluation report)
│
└── [Project Documentation]
    ├── README.md                 # This document (Chinese)
    ├── README_EN.md              # This document (English)
    ├── INSTALLATION.md           # Installation guide
    ├── CONFIGURATION.md          # Configuration guide
    └── QUICKSTART.md             # Quick start guide
```

---

## 🚀 Quick Start

### Option 1: Generate Agent for Existing Domain (Recommended)

If you have a specific research domain, use the `paper-expert-generator` skill:

```bash
# 1. Run the scaffolding script
python skills/paper-expert-generator/scripts/init_domain_agent.py \
  --domain "bioinfo-ml" \
  --output ~/agents/bioinfo-ml \
  --paperclaw-skills ./skills

# 2. Fill in the {{placeholders}} in AGENT.md according to prompts
# 3. Set API key
# 4. Launch OpenClaw pointing to the new agent
```

### Option 2: Use the Demo (Understand the Workflow)

Explore `agents/surrogate-modeling/` as a complete working example:

```bash
cd agents/surrogate-modeling

# Daily search (manual trigger)
python skills/daily-search/scripts/daily_paper_search.py --top 3

# Weekly report generation
python skills/weekly-report/scripts/generate_weekly_report_v2.py
```

---

## 🏗️ System Architecture

### Single Agent Internal Architecture

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
│  ├── {paper}/metadata.json  ← Structured scoring data       │
│  ├── {paper}/summary.md     ← Deep summary                  │
│  ├── {paper}/scores.md      ← Scoring report                │
│  └── evaluated_papers.json  ← Deduplication index           │
└─────────────────────────────────────────────────────────────┘
```

### From Skill to Agent Generation Flow

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
                                              (5 skills, adapt as needed)
```

---

## 📊 Core Features

| Feature | Description | Trigger |
|---------|-------------|---------|
| 🔍 **Daily Search** | Batch arXiv search, auto-dedup, Top 3 selection | Daily 20:00 (Asia/Singapore) |
| 📝 **Deep Summary** | Answer 10 core questions, generate summary.md | Auto after search |
| 📊 **4D Scoring** | Domain-customized dimensions + Date-Citation weighting | Auto after summary |
| 📰 **Weekly Report** | Top 3 curated papers, push notification | Every Sunday 10:00 |

---

## 📐 Scoring System

### 4D Base Score + Date-Citation Impact Score

```
Final Score = Base Score × 0.9 + Impact Score × 0.1

Base Score = (Dimension1 + Dimension2 + Dimension3 + Dimension4) / 4
```

**Date-Citation Adjustment Factors** (example, customizable per domain):
- ≤3 months new papers: +0.2
- 3-24 months + citations≥50: +0.5
- u003e24 months + citations≥200: +0.5
- Citation density≥10/month: extra +0.2

**Domain-Customized Scoring Dimension Examples**:
- **Scientific ML** (default): Engineering Value, Architecture Innovation, Theoretical Contribution, Reliability
- **Bioinformatics**: Biological Validity, Computational Scalability, Benchmark Quality, Translational Potential
- **Computer Vision**: Architecture Innovation, Benchmark Performance, Generalization, Practical Utility

See `skills/paper-expert-generator/references/domain-adaptation-guide.md` for details.

---

## 🛠️ Creating a New Domain Agent

Follow the 8-step workflow in `skills/paper-expert-generator/SKILL.md`:

1. **Domain Interview** — Collect research domain, sub-directions, methods, exclusions
2. **Keyword Library** — Build arXiv `ti:` queries
3. **Scoring Dimensions** — Design 4 domain-specific scoring dimensions
4. **Scaffolding** — Run `init_domain_agent.py`
5. **Write AGENT.md** — Fill in role definition, keywords, 4 core tasks
6. **Adapt SKILL.md** — Customize keyword list and scoring dimensions
7. **Configure Model** — Input API credentials
8. **Validate u0026 Deliver** — Checklist confirmation

---

## 🔄 Changelog

### v2.0.0 (2026-03-11) - Framework Refactor

**🎯 Architecture Upgrade**
- ✅ Added `paper-expert-generator` Skill, supporting any research domain
- ✅ Directory restructure: `skills/` (reusable components) + `agents/` (domain examples)
- ✅ `surrogate-modeling` as the first Demo Agent (Scientific ML + 3D Geometry)

### v1.1.0 (2026-03-04) - Architecture Optimization

**🚀 Core Improvements**
- ✅ Eliminated regex parsing dependency, read structured data directly from JSON
- ✅ Safe concurrent write (file locking + dedup check)
- ✅ Mandatory reasoning chain (` (`<think>` tags)

### v1.0.0 (2026-03-01) - Initial Release

- ✅ arXiv paper automated search
- ✅ Paper deep summarization (10 questions)
- ✅ 4D scoring system
- ✅ Weekly report auto-generation

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

**Contribution Directions**:
- New domain adaptation examples (add to `agents/`)
- Feature enhancements for `paper-expert-generator` Skill
- More domain keyword libraries and scoring dimensions (`domain-adaptation-guide.md`)

---

## 📄 License

MIT License

---

<div align="center">

**If this project helps you, please give us a ⭐️ Star!**

</div>
