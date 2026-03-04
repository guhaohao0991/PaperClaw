#!/usr/bin/env python3
"""
论文注册表安全更新工具
功能：使用文件锁安全更新 evaluated_papers.json，防止并发写入冲突
使用方法:
  python update_registry.py --id "2401.12345" --title "Paper Title" --short_title "ShortName" --score 8.5
"""
import json
import os
from datetime import datetime
import argparse


def get_lock():
    """跨平台文件锁获取"""
    try:
        import fcntl
        return fcntl, fcntl.LOCK_EX, fcntl.LOCK_UN
    except ImportError:
        # Windows fallback: 返回 None，使用无锁模式
        return None, None, None


def update_registry(arxiv_id, title, short_title, final_score, workspace_path=None):
    """
    安全更新论文注册表
    
    Args:
        arxiv_id: arXiv ID
        title: 论文完整标题
        short_title: 简短标题（用于文件夹命名）
        final_score: 最终综合评分
        workspace_path: 工作空间路径（可选，默认使用标准路径）
    """
    # 确定注册表路径
    if workspace_path:
        registry_path = os.path.join(workspace_path, 'papers', 'evaluated_papers.json')
    else:
        # 默认路径
        registry_path = os.path.expanduser(
            '~/.openclaw/workspace/3d_surrogate_proj/papers/evaluated_papers.json'
        )
    
    new_paper = {
        "arxiv_id": arxiv_id,
        "title": title,
        "short_title": short_title,
        "scores": {"final_score": float(final_score)},
        "evaluated_date": datetime.now().isoformat()
    }

    # 确保目录存在
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    fcntl_module, LOCK_EX, LOCK_UN = get_lock()
    
    try:
        # 文件不存在时创建初始结构
        if not os.path.exists(registry_path):
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump({"papers": [], "last_updated": ""}, f, ensure_ascii=False, indent=2)
            print(f"📝 已创建新的注册表文件: {registry_path}")
        
        with open(registry_path, 'r+', encoding='utf-8') as f:
            # 尝试获取排他锁（仅 Linux/macOS）
            if fcntl_module:
                fcntl_module.flock(f, LOCK_EX)
            
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print("⚠️  注册表文件损坏，重新初始化")
                data = {"papers": []}
            
            # 去重检查：基于 arXiv ID
            existing_ids = {p.get('arxiv_id') for p in data.get('papers', [])}
            if arxiv_id in existing_ids:
                print(f"⚠️  论文已存在，跳过重复添加: {arxiv_id} - {title[:50]}...")
                if fcntl_module:
                    fcntl_module.flock(f, LOCK_UN)
                return False
            
            # 去重检查：基于标准化标题
            existing_titles = {p.get('title', '').lower().strip() for p in data.get('papers', [])}
            if title.lower().strip() in existing_titles:
                print(f"⚠️  同标题论文已存在，跳过: {title[:50]}...")
                if fcntl_module:
                    fcntl_module.flock(f, LOCK_UN)
                return False
            
            # 添加新论文
            data["papers"].append(new_paper)
            data["last_updated"] = datetime.now().isoformat()
            
            # 写入更新
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()
            
            # 释放锁
            if fcntl_module:
                fcntl_module.flock(f, LOCK_UN)
                
        print(f"✅ 已安全更新论文记录: {title[:60]}...")
        print(f"   arXiv ID: {arxiv_id}")
        print(f"   综合评分: {final_score}")
        return True
        
    except Exception as e:
        print(f"❌ 更新注册表失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='安全更新论文注册表（带文件锁和去重检查）'
    )
    parser.add_argument("--id", required=True, help="arXiv ID")
    parser.add_argument("--title", required=True, help="论文完整标题")
    parser.add_argument("--short_title", required=True, help="简短标题（文件夹名）")
    parser.add_argument("--score", required=True, type=float, help="最终综合评分")
    parser.add_argument("--workspace", default=None, help="工作空间路径（可选）")
    
    args = parser.parse_args()
    
    success = update_registry(
        arxiv_id=args.id,
        title=args.title,
        short_title=args.short_title,
        final_score=args.score,
        workspace_path=args.workspace
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()