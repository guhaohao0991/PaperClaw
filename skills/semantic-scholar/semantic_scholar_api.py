#!/usr/bin/env python3
"""
Semantic Scholar API Client
用于获取论文引用数据、作者信息和论文详情

使用方法:
    python semantic_scholar_api.py search "query" --limit 10
    python semantic_scholar_api.py paper-by-title "Title"
    python semantic_scholar_api.py paper-by-arxiv "2405.13998"
    python semantic_scholar_api.py paper-by-id "paper_id"
    python semantic_scholar_api.py author "author_id"
    python semantic_scholar_api.py batch-papers "arxiv:2405.13998,arxiv:2309.00583"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import requests

# 配置
API_BASE_URL = "https://api.semanticscholar.org/graph/v1"
CACHE_DIR = Path("/home/gem/.openclaw/workspace/3d_surrogate_proj/cache/semantic_scholar")
CACHE_EXPIRY_DAYS = {
    "paper": 7,
    "author": 30,
    "citations": 1,
}

# 默认返回字段
DEFAULT_PAPER_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "publicationDate",
    "citationCount",
    "referenceCount",
    "publicationVenue",
    "abstract",
    "openAccessPdf",
    "externalIds",
    "venue",
    "journal",
    "isOpenAccess",
    "fieldsOfStudy",
]

DEFAULT_AUTHOR_FIELDS = [
    "authorId",
    "name",
    "hIndex",
    "citationCount",
    "paperCount",
    "affiliations",
]


class SemanticScholarAPI:
    """Semantic Scholar API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"x-api-key": api_key})
        
        # 创建缓存目录
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, cache_type: str, identifier: str) -> Path:
        """获取缓存文件路径"""
        safe_id = identifier.replace("/", "_").replace(":", "_")
        return CACHE_DIR / f"{cache_type}_{safe_id}.json"
    
    def _load_cache(self, cache_type: str, identifier: str) -> Optional[Dict]:
        """加载缓存"""
        cache_path = self._get_cache_path(cache_type, identifier)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # 检查缓存是否过期
            cached_time = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
            expiry_days = CACHE_EXPIRY_DAYS.get(cache_type, 7)
            if datetime.now() - cached_time > timedelta(days=expiry_days):
                return None
            
            return cached.get("data")
        except Exception:
            return None
    
    def _save_cache(self, cache_type: str, identifier: str, data: Dict):
        """保存缓存"""
        cache_path = self._get_cache_path(cache_type, identifier)
        cached = {
            "cached_at": datetime.now().isoformat(),
            "data": data,
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cached, f, ensure_ascii=False, indent=2)
    
    def _request_with_retry(
        self, 
        url: str, 
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict:
        """带重试机制的请求"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return {"error": "Not found", "status_code": 404}
                elif response.status_code == 429:
                    # Rate limit, wait and retry
                    wait_time = 2 ** attempt
                    print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "status_code": response.status_code,
                        "message": response.text[:200]
                    }
            
            except requests.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Timeout, retrying in {wait_time}s...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                return {"error": "Request timeout"}
            
            except Exception as e:
                return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}
    
    def search_papers(
        self, 
        query: str, 
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """搜索论文"""
        cache_key = f"search_{query}_{limit}"
        cached = self._load_cache("search", cache_key)
        if cached:
            return cached
        
        url = f"{API_BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": ",".join(fields or DEFAULT_PAPER_FIELDS),
        }
        
        result = self._request_with_retry(url, params)
        
        if "error" not in result:
            self._save_cache("search", cache_key, result)
        
        return result
    
    def get_paper_by_id(
        self, 
        paper_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """通过 Semantic Scholar ID 获取论文详情"""
        cached = self._load_cache("paper", paper_id)
        if cached:
            return cached
        
        url = f"{API_BASE_URL}/paper/{paper_id}"
        params = {
            "fields": ",".join(fields or DEFAULT_PAPER_FIELDS),
        }
        
        result = self._request_with_retry(url, params)
        
        if "error" not in result:
            self._save_cache("paper", paper_id, result)
        
        return result
    
    def get_paper_by_arxiv(
        self, 
        arxiv_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """通过 arXiv ID 获取论文详情"""
        # arXiv ID 格式: ARXIV:YYMM.NNNNN
        paper_id = f"ARXIV:{arxiv_id}"
        return self.get_paper_by_id(paper_id, fields)
    
    def get_paper_by_doi(
        self, 
        doi: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """通过 DOI 获取论文详情"""
        paper_id = f"DOI:{doi}"
        return self.get_paper_by_id(paper_id, fields)
    
    def get_paper_by_title(
        self, 
        title: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """通过标题搜索论文（返回最匹配的结果）"""
        # 先搜索
        search_result = self.search_papers(title, limit=1, fields=fields)
        
        if "error" in search_result:
            return search_result
        
        papers = search_result.get("data", [])
        if not papers:
            return {"error": "Paper not found", "title": title}
        
        # 返回第一个结果
        paper = papers[0]
        
        # 缓存结果
        if "paperId" in paper:
            self._save_cache("paper", paper["paperId"], paper)
        
        return paper
    
    def get_author(
        self, 
        author_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """获取作者详情"""
        cached = self._load_cache("author", author_id)
        if cached:
            return cached
        
        url = f"{API_BASE_URL}/author/{author_id}"
        params = {
            "fields": ",".join(fields or DEFAULT_AUTHOR_FIELDS),
        }
        
        result = self._request_with_retry(url, params)
        
        if "error" not in result:
            self._save_cache("author", author_id, result)
        
        return result
    
    def get_paper_citations(
        self, 
        paper_id: str,
        limit: int = 100,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """获取论文引用列表"""
        cache_key = f"{paper_id}_{limit}"
        cached = self._load_cache("citations", cache_key)
        if cached:
            return cached
        
        url = f"{API_BASE_URL}/paper/{paper_id}/citations"
        citation_fields = ["paperId", "title", "authors", "year", "citationCount"]
        params = {
            "limit": limit,
            "fields": ",".join(fields or citation_fields),
        }
        
        result = self._request_with_retry(url, params)
        
        if "error" not in result:
            self._save_cache("citations", cache_key, result)
        
        return result
    
    def get_paper_references(
        self, 
        paper_id: str,
        limit: int = 100,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """获取论文参考文献列表"""
        url = f"{API_BASE_URL}/paper/{paper_id}/references"
        ref_fields = ["paperId", "title", "authors", "year", "citationCount"]
        params = {
            "limit": limit,
            "fields": ",".join(fields or ref_fields),
        }
        
        return self._request_with_retry(url, params)
    
    def batch_get_papers(
        self, 
        paper_ids: List[str],
        fields: Optional[List[str]] = None
    ) -> Dict:
        """批量获取论文信息"""
        url = f"{API_BASE_URL}/paper/batch"
        params = {
            "fields": ",".join(fields or DEFAULT_PAPER_FIELDS),
        }
        
        response = self.session.post(
            url, 
            params=params, 
            json={"ids": paper_ids},
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text[:200]
            }


def format_output(data: Dict, output_format: str = "json") -> str:
    """格式化输出"""
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "summary":
        # 简洁摘要格式
        if "error" in data:
            return f"Error: {data['error']}"
        
        lines = []
        if "title" in data:
            lines.append(f"Title: {data['title']}")
        if "paperId" in data:
            lines.append(f"Paper ID: {data['paperId']}")
        if "year" in data:
            lines.append(f"Year: {data['year']}")
        if "citationCount" in data:
            lines.append(f"Citations: {data['citationCount']}")
        if "authors" in data:
            author_names = [a.get("name", "") for a in data["authors"]]
            lines.append(f"Authors: {', '.join(author_names[:5])}")
        if "venue" in data:
            lines.append(f"Venue: {data['venue']}")
        if "openAccessPdf" in data and data["openAccessPdf"]:
            lines.append(f"PDF: {data['openAccessPdf'].get('url', 'N/A')}")
        
        return "\n".join(lines)
    else:
        return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Scholar API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 搜索论文
  python semantic_scholar_api.py search "neural operator" --limit 5
  
  # 通过标题获取论文
  python semantic_scholar_api.py paper-by-title "Geometry-Informed Neural Operator"
  
  # 通过 arXiv ID 获取论文
  python semantic_scholar_api.py paper-by-arxiv "2405.13998"
  
  # 获取作者信息
  python semantic_scholar_api.py author "1699545"
  
  # 批量获取论文
  python semantic_scholar_api.py batch-papers "ARXIV:2405.13998,ARXIV:2309.00583"
        """
    )
    
    parser.add_argument(
        "--api-key",
        help="Semantic Scholar API Key (optional, increases rate limit)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="json",
        help="Output format"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="Search papers by query")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Number of results")
    
    # paper-by-id 命令
    id_parser = subparsers.add_parser("paper-by-id", help="Get paper by Semantic Scholar ID")
    id_parser.add_argument("paper_id", help="Semantic Scholar paper ID")
    
    # paper-by-title 命令
    title_parser = subparsers.add_parser("paper-by-title", help="Get paper by title")
    title_parser.add_argument("title", help="Paper title")
    
    # paper-by-arxiv 命令
    arxiv_parser = subparsers.add_parser("paper-by-arxiv", help="Get paper by arXiv ID")
    arxiv_parser.add_argument("arxiv_id", help="arXiv ID (e.g., 2405.13998)")
    
    # paper-by-doi 命令
    doi_parser = subparsers.add_parser("paper-by-doi", help="Get paper by DOI")
    doi_parser.add_argument("doi", help="DOI")
    
    # author 命令
    author_parser = subparsers.add_parser("author", help="Get author details")
    author_parser.add_argument("author_id", help="Semantic Scholar author ID")
    
    # citations 命令
    citations_parser = subparsers.add_parser("citations", help="Get paper citations")
    citations_parser.add_argument("paper_id", help="Semantic Scholar paper ID")
    citations_parser.add_argument("--limit", type=int, default=100, help="Number of results")
    
    # references 命令
    references_parser = subparsers.add_parser("references", help="Get paper references")
    references_parser.add_argument("paper_id", help="Semantic Scholar paper ID")
    references_parser.add_argument("--limit", type=int, default=100, help="Number of results")
    
    # batch-papers 命令
    batch_parser = subparsers.add_parser("batch-papers", help="Batch get papers by IDs (supports ARXIV: prefix)")
    batch_parser.add_argument("ids", help="Comma-separated paper IDs (e.g., ARXIV:2405.13998,ARXIV:2309.00583 or just IDs: 2405.13998,2309.00583)")
    batch_parser.add_argument("--prefix", default="ARXIV:", help="ID prefix to add if not present (default: ARXIV:)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 初始化 API 客户端
    api_key = args.api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    client = SemanticScholarAPI(api_key)
    
    # 执行命令
    result = {}
    
    if args.command == "search":
        result = client.search_papers(args.query, args.limit)
    
    elif args.command == "paper-by-id":
        result = client.get_paper_by_id(args.paper_id)
    
    elif args.command == "paper-by-title":
        result = client.get_paper_by_title(args.title)
    
    elif args.command == "paper-by-arxiv":
        result = client.get_paper_by_arxiv(args.arxiv_id)
    
    elif args.command == "paper-by-doi":
        result = client.get_paper_by_doi(args.doi)
    
    elif args.command == "author":
        result = client.get_author(args.author_id)
    
    elif args.command == "citations":
        result = client.get_paper_citations(args.paper_id, args.limit)
    
    elif args.command == "references":
        result = client.get_paper_references(args.paper_id, args.limit)
    
    elif args.command == "batch-papers":
        ids = [id.strip() for id in args.ids.split(",")]
        # 添加前缀（如果不存在）
        if hasattr(args, 'prefix') and args.prefix:
            ids = [id if ':' in id else f"{args.prefix}{id}" for id in ids]
        result = client.batch_get_papers(ids)
    
    # 输出结果
    print(format_output(result, args.format))


if __name__ == "__main__":
    main()
