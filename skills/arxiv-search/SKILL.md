# arXiv Paper Search Skill

## 功能描述
从 arXiv 检索学术论文，支持关键词搜索、批量下载和自动筛选。

## 使用方法

### 1. 基础搜索
调用内置的搜索脚本：

```bash
# 搜索特定关键词的最新论文
python skills/arxiv-search/scripts/search_arxiv.py --query "neural operator PDE" --limit 5
```

### 2. 批量关键词搜索（含去重机制）
使用预设的高级查询进行批量搜索：

```bash
# 使用预设关键词批量搜索，每个查询最多30篇
python skills/arxiv-search/scripts/search_arxiv.py --batch --limit 30

# 批量搜索并输出相关性最高的 Top 10
python skills/arxiv-search/scripts/search_arxiv.py --batch --limit 30 --top 10

# 批量搜索并保存结果到文件
python skills/arxiv-search/scripts/search_arxiv.py --batch --limit 30 --output search_results.json
```

### 脚本功能说明

`search_arxiv.py` 内置以下功能：

| 功能 | 说明 |
|------|------|
| 去重机制 | 基于 arXiv ID + 标准化标题去重（保留版本标识符如 ++、-2） |
| 排除过滤 | 自动排除不相关领域（流行病学、金融、NLP等） |
| 相关性评分 | 基于关键词匹配自动评分排序 |
| 批量搜索 | 预设 9 组高级查询覆盖核心研究方向 |

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--query` | 搜索关键词 |
| `--batch` | 使用预设关键词批量搜索 |
| `--limit` | 每个查询的最大结果数（默认30） |
| `--top` | 按相关性输出 Top N 论文 |
| `--delay` | 批量搜索时的请求间隔秒数（默认3） |
| `--output` | 输出 JSON 文件路径 |
| `--verbose` | 显示详细信息（去重、排除详情） |

### 3. 下载论文 PDF
```bash
# 下载单篇论文
python3 << 'EOF'
import urllib.request
import os
import re

def download_paper(pdf_url, title, save_dir):
    """下载论文 PDF"""
    # 清理标题作为文件名
    safe_title = re.sub(r'[^\w\s-]', '', title)
    safe_title = re.sub(r'[-\s]+', '_', safe_title)[:100]
    
    os.makedirs(save_dir, exist_ok=True)
    pdf_path = os.path.join(save_dir, f"{safe_title}.pdf")
    
    try:
        urllib.request.urlretrieve(pdf_url, pdf_path)
        print(f"Downloaded: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"Error downloading {title}: {e}")
        return None
EOF
```

### 4. 智能筛选论文
```bash
# 基于标题和摘要筛选高质量论文
python3 << 'EOF'
import json
import re

def score_paper_relevance(paper, keywords):
    """评估论文相关性分数"""
    title = paper['title'].lower()
    summary = paper['summary'].lower()
    
    score = 0
    
    # 核心关键词（高权重）
    geometry_keywords = ['3d geometry', '3d mesh', 'unstructured mesh', 'geometry-aware']
    for kw in geometry_keywords:
        if kw in title: score += 15
        if kw in summary: score += 5
    
    operator_keywords = ['neural operator', 'deep operator', 'operator learning']
    for kw in operator_keywords:
        if kw in title: score += 12
        if kw in summary: score += 4
    
    pde_keywords = ['pde solver', 'neural pde', 'pde surrogate', 'physics-informed']
    for kw in pde_keywords:
        if kw in title: score += 10
        if kw in summary: score += 3
    
    # 应用场景关键词（中高权重）
    application_keywords = ['cfd', 'fluid dynamics', 'aerodynamics', 'pressure field']
    for kw in application_keywords:
        if kw in title: score += 8
        if kw in summary: score += 3
    
    # 技术关键词（中权重）
    tech_keywords = ['transformer', 'graph neural network', 'gnn', 'pointnet']
    for kw in tech_keywords:
        if kw in title: score += 5
        if kw in summary: score += 2
    
    # 负面关键词（扣分）
    exclude_keywords = ['epidemic', 'epidemiology', 'disease', 'population dynamics',
                        'social network', 'finance', 'economics', 'nlp', 'language model']
    for kw in exclude_keywords:
        if kw in title: score -= 20
        if kw in summary: score -= 5
    
    # 加分项
    if any(word in summary for word in ['experiment', 'benchmark', 'dataset', 'validation']):
        score += 5
    
    if any(word in summary for word in ['code', 'github', 'implementation', 'open source']):
        score += 3
    
    return max(score, 0)  # 确保分数非负

def select_top_papers(papers, top_n=3):
    """选择最相关的论文"""
    scored = [(paper, score_paper_relevance(paper, [])) for paper in papers]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [paper for paper, score in scored[:top_n]]
EOF
```

## 注意事项
1. arXiv API 有请求频率限制，批量搜索时需要添加延迟（建议 3 秒）
2. 论文标题可能包含特殊字符，需要清理后才能作为文件名
3. 某些论文可能没有 PDF 链接，需要检查 `pdf_url` 是否存在
4. 建议保存搜索日志，方便追踪和去重
