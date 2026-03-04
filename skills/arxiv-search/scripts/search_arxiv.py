#!/usr/bin/env python3
"""
arXiv 论文批量搜索与去重工具 (增强版)
功能：
1. 单关键词搜索
2. 预设关键词批量搜索
3. 自动去重（ID去重 + 标题标准化去重）
4. 排除不相关领域
5. 相关性评分排序

使用方法:
  # 单关键词搜索
  python search_arxiv.py --query "neural operator PDE" --limit 5
  
  # 使用预设关键词批量搜索
  python search_arxiv.py --batch --limit 30
  
  # 批量搜索并按相关性排序输出 Top 10
  python search_arxiv.py --batch --limit 30 --top 10
"""
import argparse
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import re
import time
from datetime import datetime


# ==================== 预设配置 ====================

# 核心关键词：聚焦3D几何代理模型和PDE求解
ADVANCED_QUERIES = [
    "ti:geometry AND (ti:neural OR ti:operator OR ti:pde)",
    "ti:mesh AND (ti:neural OR ti:deep OR ti:learning)",
    "(ti:cfd OR ti:fluid) AND (ti:surrogate OR ti:neural OR ti:deep)",
    "ti:3d AND (ti:pde OR ti:physics OR ti:solver)",
    "(ti:fno OR ti:deeponet OR ti:\"neural operator\") AND (ti:geometry OR ti:mesh OR ti:domain)",
    "(ti:pressure OR ti:stress OR ti:flow) AND (ti:neural OR ti:deep OR ti:surrogate)",
    "(ti:aerodynamic OR ti:structural) AND (ti:surrogate OR ti:neural)",
    "ti:\"graph neural\" AND (ti:pde OR ti:physics OR ti:simulation)",
    "ti:transformer AND (ti:pde OR ti:physics OR ti:fluid)",
]

# 排除关键词：避免不相关领域
EXCLUDE_KEYWORDS = [
    "epidemic", "epidemiology", "disease modeling", "disease",
    "population dynamics", "social network",
    "finance", "economics", "stock", "trading",
    "nlp", "language model", "text", "sentiment",
    "drug", "protein", "molecule", "chemistry",
    "medical", "clinical", "patient"
]


# ==================== 核心函数 ====================

def normalize_title(title):
    """标准化标题用于去重（保留版本标识符如 ++、-2、-3）"""
    title = title.lower()
    # 保留版本标识符，只移除其他标点
    title = re.sub(r'[^\w\s\+\-]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def extract_arxiv_id(paper_id):
    """从 arXiv URL 提取 ID"""
    match = re.search(r'(\d{4}\.\d{4,5})', paper_id)
    if match:
        return match.group(1)
    return paper_id


def is_excluded(paper):
    """检查论文是否应被排除（基于标题和摘要）"""
    text = (paper.get('title', '') + ' ' + paper.get('summary', '')).lower()
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in text:
            return True, keyword
    return False, None


def search_arxiv(query, max_results=30):
    """搜索 arXiv 论文"""
    base_url = "http://export.arxiv.org/api/query?"
    
    # 判断是否为高级查询（包含 ti: 或 AND/OR）
    if 'ti:' in query or ' AND ' in query or ' OR ' in query:
        search_query = f"search_query={urllib.parse.quote(query)}"
    else:
        search_query = f"search_query=all:{urllib.parse.quote(query)}"
    
    url = base_url + search_query + f"&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    
    try:
        response = urllib.request.urlopen(url, timeout=30)
        xml_data = response.read().decode('utf-8')
        root = ET.fromstring(xml_data)
        
        papers = []
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            paper = {
                'id': entry.find('{http://www.w3.org/2005/Atom}id').text,
                'arxiv_id': extract_arxiv_id(entry.find('{http://www.w3.org/2005/Atom}id').text),
                'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip().replace('\n', ' '),
                'summary': entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()[:500],
                'published': entry.find('{http://www.w3.org/2005/Atom}published').text,
                'updated': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'authors': [author.find('{http://www.w3.org/2005/Atom}name').text 
                           for author in entry.findall('{http://www.w3.org/2005/Atom}author')],
                'categories': [cat.get('term') 
                              for cat in entry.findall('{http://www.w3.org/2005/Atom}category')],
                'pdf_url': None
            }
            
            # 获取 PDF 链接
            for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                if link.get('title') == 'pdf':
                    paper['pdf_url'] = link.get('href')
                    break
            
            papers.append(paper)
        
        return papers
    except Exception as e:
        print(f"❌ 搜索失败 '{query[:50]}...': {e}")
        return []


def deduplicate_papers(papers):
    """去重并记录去重信息"""
    seen_ids = set()
    seen_titles = set()
    seen_normalized = set()
    
    unique_papers = []
    duplicates = []
    excluded = []
    
    for paper in papers:
        arxiv_id = paper.get('arxiv_id', '')
        normalized_title = normalize_title(paper['title'])
        
        # 检查是否应排除
        is_excl, excl_keyword = is_excluded(paper)
        if is_excl:
            excluded.append({
                'title': paper['title'],
                'arxiv_id': arxiv_id,
                'reason': f"包含排除关键词: {excl_keyword}"
            })
            continue
        
        # 检查重复
        if arxiv_id in seen_ids:
            duplicates.append({
                'title': paper['title'],
                'arxiv_id': arxiv_id,
                'reason': f"重复ID: {arxiv_id}"
            })
            continue
        
        if paper['title'] in seen_titles:
            duplicates.append({
                'title': paper['title'],
                'arxiv_id': arxiv_id,
                'reason': f"重复标题"
            })
            continue
        
        if normalized_title in seen_normalized:
            duplicates.append({
                'title': paper['title'],
                'arxiv_id': arxiv_id,
                'reason': f"相似标题"
            })
            continue
        
        # 添加到唯一列表
        unique_papers.append(paper)
        seen_ids.add(arxiv_id)
        seen_titles.add(paper['title'])
        seen_normalized.add(normalized_title)
    
    return unique_papers, duplicates, excluded


def score_paper_relevance(paper):
    """评估论文相关性分数"""
    title = paper['title'].lower()
    summary = paper.get('summary', '').lower()
    
    score = 0
    
    # 核心关键词（高权重）
    geometry_keywords = ['3d geometry', '3d mesh', 'unstructured mesh', 'geometry-aware', 
                        'complex geometry', 'arbitrary geometry']
    for kw in geometry_keywords:
        if kw in title: score += 15
        if kw in summary: score += 5
    
    operator_keywords = ['neural operator', 'deep operator', 'operator learning', 
                        'deeponet', 'fourier neural operator', 'fno']
    for kw in operator_keywords:
        if kw in title: score += 12
        if kw in summary: score += 4
    
    pde_keywords = ['pde solver', 'neural pde', 'pde surrogate', 'physics-informed',
                   'pinn', 'partial differential']
    for kw in pde_keywords:
        if kw in title: score += 10
        if kw in summary: score += 3
    
    # 应用场景关键词（中高权重）
    application_keywords = ['cfd', 'fluid dynamics', 'aerodynamics', 'pressure field',
                           'stress field', 'heat transfer', 'structural mechanics']
    for kw in application_keywords:
        if kw in title: score += 8
        if kw in summary: score += 3
    
    # 技术关键词（中权重）
    tech_keywords = ['transformer', 'graph neural network', 'gnn', 'pointnet',
                    'attention', 'equivariant']
    for kw in tech_keywords:
        if kw in title: score += 5
        if kw in summary: score += 2
    
    # 加分项
    if any(word in summary for word in ['experiment', 'benchmark', 'dataset', 'validation']):
        score += 5
    
    if any(word in summary for word in ['code', 'github', 'implementation', 'open source']):
        score += 3
    
    return max(score, 0)


def batch_search(max_results_per_query=30, delay=3):
    """使用预设关键词批量搜索"""
    all_papers = []
    
    print(f"📚 开始批量搜索，共 {len(ADVANCED_QUERIES)} 个查询...")
    print("=" * 60)
    
    for i, query in enumerate(ADVANCED_QUERIES, 1):
        print(f"[{i}/{len(ADVANCED_QUERIES)}] 搜索: {query[:60]}...")
        papers = search_arxiv(query, max_results_per_query)
        print(f"    找到 {len(papers)} 篇论文")
        all_papers.extend(papers)
        
        if i < len(ADVANCED_QUERIES):
            time.sleep(delay)  # 避免请求过快
    
    print("=" * 60)
    print(f"📊 总计收集 {len(all_papers)} 篇论文（去重前）")
    
    return all_papers


def main():
    parser = argparse.ArgumentParser(
        description='arXiv 论文批量搜索与去重工具'
    )
    parser.add_argument("--query", type=str, help="搜索关键词")
    parser.add_argument("--batch", action="store_true", help="使用预设关键词批量搜索")
    parser.add_argument("--limit", type=int, default=30, help="每个查询的最大结果数")
    parser.add_argument("--top", type=int, default=0, help="按相关性输出 Top N 论文")
    parser.add_argument("--delay", type=int, default=3, help="批量搜索时的请求间隔（秒）")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    # 参数验证
    if not args.query and not args.batch:
        parser.error("必须指定 --query 或 --batch")
    
    # 执行搜索
    if args.batch:
        all_papers = batch_search(args.limit, args.delay)
    else:
        print(f"🔍 搜索: {args.query}")
        all_papers = search_arxiv(args.query, args.limit)
        print(f"📊 找到 {len(all_papers)} 篇论文")
    
    # 去重
    unique_papers, duplicates, excluded = deduplicate_papers(all_papers)
    
    print(f"\n📊 去重结果:")
    print(f"   - 唯一论文: {len(unique_papers)}")
    print(f"   - 重复移除: {len(duplicates)}")
    print(f"   - 排除过滤: {len(excluded)}")
    
    # 相关性评分排序
    for paper in unique_papers:
        paper['relevance_score'] = score_paper_relevance(paper)
    
    unique_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    # 输出 Top N
    if args.top > 0:
        top_papers = unique_papers[:args.top]
        print(f"\n🏆 Top {len(top_papers)} 相关论文:")
        print("-" * 60)
        for i, paper in enumerate(top_papers, 1):
            print(f"{i}. [{paper['relevance_score']}分] {paper['title'][:60]}...")
            print(f"   arXiv: {paper['arxiv_id']} | 发表: {paper['published'][:10]}")
            if args.verbose:
                print(f"   摘要: {paper['summary'][:100]}...")
            print()
    
    # 详细信息
    if args.verbose and duplicates:
        print(f"\n📋 移除的重复论文 (前10):")
        for dup in duplicates[:10]:
            print(f"   - {dup['reason']}: {dup['title'][:50]}...")
    
    if args.verbose and excluded:
        print(f"\n🚫 排除的论文 (前10):")
        for excl in excluded[:10]:
            print(f"   - {excl['reason']}: {excl['title'][:50]}...")
    
    # 输出到文件
    if args.output:
        output_data = {
            "search_time": datetime.now().isoformat(),
            "query": args.query if args.query else "batch_search",
            "total_collected": len(all_papers),
            "unique_count": len(unique_papers),
            "duplicates_removed": len(duplicates),
            "excluded_count": len(excluded),
            "papers": unique_papers if args.top == 0 else unique_papers[:args.top]
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存至: {args.output}")
    else:
        # 默认输出 JSON 到 stdout
        print(json.dumps(unique_papers[:args.top] if args.top > 0 else unique_papers[:10], 
                        indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()