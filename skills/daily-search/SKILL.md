# Daily Paper Search Skill

## 功能描述
每日自动检索 arXiv 最新论文，与已评估数据库去重，精选 Top N 论文待评估，发送每日检索摘要。

## 核心流程

```
┌─────────────────────────────────────────────────────────────┐
│  20:00 Asia/Singapore 自动触发                              │
│       ↓                                                     │
│  1. 批量搜索 arXiv (9组预设关键词，每组30篇)                │
│       ↓                                                     │
│  2. 搜索结果去重 (ID + 标准化标题)                          │
│       ↓                                                     │
│  3. 与 evaluated_papers.json 去重                           │
│       ↓                                                     │
│  4. 相关性评分排序                                          │
│       ↓                                                     │
│  5. 选择 Top 3 精选论文                                     │
│       ↓                                                     │
│  6. 下载 PDF + 创建元数据                                   │
│       ↓                                                     │
│  7. 生成待评估任务清单                                      │
│       ↓                                                     │
│  8. 发送如流消息摘要                                        │
│       ↓                                                     │
│  9. Agent 执行 paper-review 深度评估                        │
└─────────────────────────────────────────────────────────────┘
```

## 使用方法

### 手动执行

```bash
# 完整流程（搜索 + 下载 + 发送消息）
python skills/daily-search/scripts/daily_paper_search.py

# 精选 5 篇论文（默认 3 篇）
python skills/daily-search/scripts/daily_paper_search.py --top 5

# 仅搜索，不下载 PDF
python skills/daily-search/scripts/daily_paper_search.py --skip-download

# 干跑模式（仅搜索，不下载不发送）
python skills/daily-search/scripts/daily_paper_search.py --dry-run
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--top N` | 精选论文数量（默认 3） |
| `--skip-download` | 跳过 PDF 下载 |
| `--dry-run` | 干跑模式，仅搜索不执行实际操作 |
| `--workspace PATH` | 指定工作空间路径 |

## 输出文件

执行后将生成以下文件：

| 文件 | 路径 | 说明 |
|------|------|------|
| 搜索日志 | `search_logs/YYYY-MM-DD_search_log.json` | 当日搜索统计和去重详情 |
| 待评估清单 | `pending_evaluation_YYYY-MM-DD.json` | Agent 待执行的评估任务 |
| 论文元数据 | `papers/{short_title}/metadata.json` | 每篇精选论文的基础信息 |
| 论文 PDF | `papers/{short_title}/*.pdf` | 下载的论文 PDF |

## 后续评估流程

每日检索完成后，Agent 需要执行以下步骤完成论文评估：

### 步骤 1: 查看待评估清单

```bash
cat workspace/pending_evaluation_YYYY-MM-DD.json
```

### 步骤 2: 对每篇论文执行深度评估

对于清单中的每篇论文，按照 `paper-review` 技能流程执行：

1. **获取 Semantic Scholar 数据**
```bash
python skills/semantic-scholar/semantic_scholar_api.py paper-by-arxiv "[arxiv_id]" --format json > papers/{short_title}/metadata.json
```

2. **阅读论文并撰写总结**
   - 生成 `papers/{short_title}/summary.md`

3. **进行四维评分**
   - 生成 `papers/{short_title}/scores.md`
   - 使用 `<think>` 标签记录推理过程

4. **更新已评估论文数据库**
```bash
python skills/paper-review/scripts/update_registry.py \
  --id "[arxiv_id]" \
  --title "[论文标题]" \
  --short_title "[short_title]" \
  --score "[最终评分]"
```

### 步骤 3: 确认评估完成

检查 `evaluated_papers.json` 确认论文已添加：
```bash
cat workspace/papers/evaluated_papers.json | python -m json.tool | tail -20
```

## 定时任务配置

### OpenClaw Cron 配置

在 Agent 配置中添加定时任务：

```json
{
  "name": "Daily Paper Search",
  "schedule": {
    "kind": "cron",
    "expr": "0 20 * * *",
    "tz": "Asia/Singapore"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "执行每日论文检索任务：运行 daily_paper_search.py 搜索最新论文，然后对精选的 Top 3 论文执行完整的 paper-review 流程（总结、评分、更新数据库）"
  },
  "sessionTarget": "isolated"
}
```

### 系统 Crontab 配置（备选）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务 (20:00 Asia/Singapore = 12:00 UTC)
0 12 * * * cd /home/gem/.openclaw && python skills/daily-search/scripts/daily_paper_search.py >> /var/log/daily_paper_search.log 2>&1
```

## 去重机制说明

### 三层去重策略

1. **搜索结果内部去重** (`search_arxiv.py`)
   - arXiv ID 去重
   - 标准化标题去重（保留版本标识符如 ++、-2）
   - 排除不相关领域

2. **与已评估数据库去重** (`daily_paper_search.py`)
   - 读取 `evaluated_papers.json`
   - 比对 arXiv ID
   - 比对标题（不区分大小写）

3. **写入时去重** (`update_registry.py`)
   - 最后一道防线
   - 防止并发写入重复

## 注意事项

1. **API 限制**: arXiv API 有请求频率限制，脚本已设置 3 秒延迟
2. **网络依赖**: PDF 下载和如流消息发送需要网络连接
3. **评估时间**: 深度评估每篇论文需要 Agent 投入时间，建议每日精选 3 篇
4. **存储空间**: PDF 文件会占用存储空间，定期清理旧论文

## 更新日志

### v1.0 (2026-03-04)
- ✅ 初始版本
- ✅ 批量搜索与去重
- ✅ PDF 下载
- ✅ 如流消息发送
- ✅ 待评估任务清单生成
