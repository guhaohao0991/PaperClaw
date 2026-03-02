#!/usr/bin/env python3
"""
周报生成与发送脚本 v2.2
功能：
1. 从 evaluated_papers.json 读取基础信息和最终评分
2. 从 papers/{short_title}/scores.md 读取四维评分详情
3. 从 papers/{short_title}/summary.md 读取完整总结
4. 从 papers/{short_title}/metadata.json 读取关键词等元信息
5. 按综合评分排序，筛选 Top 3 精选论文
6. 为每篇精选论文创建独立知识库文档
7. 生成 Markdown 周报
8. 创建周报知识库文档
9. 发送如流消息（包含知识库链接）

数据源设计（2026-03-02 优化）：
- evaluated_papers.json: 基础信息 + 最终评分（去重检查用）
- papers/{short_title}/scores.md: 四维评分详情
- papers/{short_title}/summary.md: 完整论文总结
- papers/{short_title}/metadata.json: 关键词等元信息
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加技能路径
sys.path.insert(0, '/home/gem/.openclaw/skills/ku-doc-manage/scripts')
sys.path.insert(0, '/home/gem/.openclaw/skills/so-send-message/scripts')

from ku_api_client import KuApiClient
from send_message import GroupMessageSender


class WeeklyReportGenerator:
    """周报生成器 v2.0"""
    
    def __init__(self):
        self.workspace_dir = Path("/home/gem/.openclaw/workspace/3d_surrogate_proj")
        # 使用统一的数据文件（包含完整评分数据）
        self.papers_file = self.workspace_dir / "papers" / "evaluated_papers.json"
        self.reports_dir = self.workspace_dir / "weekly_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 知识库配置
        self.ku_repo_id = "qv-vZnw7HE"
        self.ku_parent_doc_id = "jnGipY319RaSyz"
        
        # 如流消息接收人
        self.recipients = ["guhaohao"]
        
    def load_evaluated_papers(self):
        """加载已评估论文（从统一数据文件 - 获取基础信息和最终评分）"""
        if not self.papers_file.exists():
            print(f"❌ 论文数据文件不存在: {self.papers_file}")
            return []
        
        with open(self.papers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        papers = data.get('papers', [])
        print(f"✅ 加载 {len(papers)} 篇论文（基础信息）")
        return papers
    
    def filter_week_papers(self, papers, days=7):
        """筛选最近N天的论文"""
        week_start = datetime.now() - timedelta(days=days)
        
        week_papers = []
        for paper in papers:
            try:
                eval_date_str = paper.get('evaluated_date', '')
                if not eval_date_str:
                    continue
                eval_date = datetime.fromisoformat(eval_date_str)
                if eval_date >= week_start:
                    week_papers.append(paper)
            except (ValueError, TypeError) as e:
                print(f"⚠️  日期解析失败: {paper.get('short_title', 'Unknown')} - {e}")
                continue
        
        return week_papers
    
    def sort_and_select_top(self, papers, top_n=3):
        """按综合评分排序并选择Top N"""
        sorted_papers = sorted(papers, key=lambda x: x.get('scores', {}).get('final_score', 0), reverse=True)
        return sorted_papers[:top_n]
    
    def read_summary_file(self, short_title):
        """读取论文的完整 summary.md 内容"""
        summary_file = self.workspace_dir / "papers" / short_title / "summary.md"
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️  读取 summary.md 失败 {short_title}: {e}")
                return None
        return None
    
    def read_scores_file(self, short_title):
        """读取论文的 scores.md 内容（四维评分详情）"""
        scores_file = self.workspace_dir / "papers" / short_title / "scores.md"
        if scores_file.exists():
            try:
                with open(scores_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️  读取 scores.md 失败 {short_title}: {e}")
                return None
        return None
    
    def read_metadata_file(self, short_title):
        """读取论文的 metadata.json 内容（关键词等元信息）"""
        metadata_file = self.workspace_dir / "papers" / short_title / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  读取 metadata.json 失败 {short_title}: {e}")
                return None
        return None
    
    def generate_report_markdown(self, papers, all_week_papers, report_date, summary_doc_urls=None):
        """生成Markdown格式的周报"""
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_end = report_date
        
        # 生成论文列表（Top 3）- 从多个文件读取数据
        paper_list = []
        for i, paper in enumerate(papers, 1):
            short_title = paper.get('short_title', '')
            
            # 从 scores.md 读取四维评分详情
            scores_content = self.read_scores_file(short_title)
            
            # 从 metadata.json 读取关键词
            metadata = self.read_metadata_file(short_title)
            keywords = metadata.get('keywords', []) if metadata else paper.get('keywords', [])
            
            # 从 evaluated_papers.json 获取基础信息和最终评分
            scores = paper.get('scores', {})
            final_score = scores.get('final_score', 0)
            
            paper_entry = f"""### {i}. {paper.get('title', 'Unknown')}

**综合评分**: {final_score:.2f}/10

**四维评分详情**:
{scores_content if scores_content else '*评分详情暂缺*'}

**关键词**:  
{', '.join(keywords)}

**arXiv链接**: [{paper.get('arxiv_id', 'N/A')}](https://arxiv.org/abs/{paper.get('arxiv_id', '')})

---"""
            paper_list.append(paper_entry)
        
        # 生成评分表格（Top 5）- 从 scores.md 读取评分详情
        table_rows = []
        for paper in all_week_papers[:5]:
            short_title = paper.get('short_title', '')
            scores_content = self.read_scores_file(short_title)
            
            # 从 evaluated_papers.json 获取最终评分
            scores = paper.get('scores', {})
            final_score = scores.get('final_score', 0)
            
            title = paper.get('title', 'Unknown')
            if len(title) > 30:
                title = title[:30] + "..."
            
            # 如果有 scores.md 内容，解析四维评分
            if scores_content:
                # 简单解析 scores.md 中的评分（假设格式为 "- 工程应用价值: X/10"）
                import re
                eng_match = re.search(r'工程应用价值:\s*(\d+(?:\.\d+)?)', scores_content)
                arch_match = re.search(r'网络架构创新:\s*(\d+(?:\.\d+)?)', scores_content)
                theo_match = re.search(r'理论贡献:\s*(\d+(?:\.\d+)?)', scores_content)
                rel_match = re.search(r'结果可靠性:\s*(\d+(?:\.\d+)?)', scores_content)
                imp_match = re.search(r'影响力评分:\s*(\d+(?:\.\d+)?)', scores_content)
                
                eng = eng_match.group(1) if eng_match else "N/A"
                arch = arch_match.group(1) if arch_match else "N/A"
                theo = theo_match.group(1) if theo_match else "N/A"
                rel = rel_match.group(1) if rel_match else "N/A"
                imp = imp_match.group(1) if imp_match else "N/A"
            else:
                eng = arch = theo = rel = imp = "N/A"
            
            row = f"| {title} | {eng} | {arch} | {theo} | {rel} | {imp} | {final_score:.2f} |"
            table_rows.append(row)
        
        # 生成附录
        appendix = "\n## 📎 附录：精选论文完整总结\n\n"
        appendix += "> 以下三篇精选论文的完整总结已上传至知识库，点击链接查看：\n\n"
        
        if summary_doc_urls:
            for i, doc_info in enumerate(summary_doc_urls, 1):
                appendix += f"{i}. **{doc_info['title']}**: [查看完整总结]({doc_info['url']})\n\n"
        else:
            appendix += "*知识库文档链接将在创建后添加*\n\n"
        
        report = f"""# 📊 三维几何代理模型研究周报

**报告周期**: {week_start} - {week_end}  
**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**报告人**: Surrogate-Modeling Expert Agent

---

## 📌 本周概览

- **评估论文总数**: {len(all_week_papers)}
- **精选推荐论文**: Top {len(papers)}

---

## 🌟 本周精选论文 Top 3

{chr(10).join(paper_list)}

## 📊 四维评分分布（Top 5）

| 论文 | 工程应用 | 架构创新 | 理论贡献 | 可靠性 | 影响力 | 综合评分 |
|------|---------|---------|---------|--------|--------|---------|
{chr(10).join(table_rows)}

---

## 💡 研究建议

### 值得跟进的方向
1. 几何感知神经算子在复杂几何域上的应用
2. Transformer架构在PDE求解中的创新设计
3. 物理信息神经网络与代理模型的融合

### 工具与资源
- 推荐关注 arXiv cs.LG 和 cs.NA 分类
- 开源代码库持续跟踪

{appendix}
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*Surrogate-Modeling Expert Agent*"""
        
        return report
    
    def generate_summary_markdown(self, paper):
        """为单篇精选论文生成完整总结文档的Markdown内容"""
        short_title = paper.get('short_title', '')
        paper_title = paper.get('title', 'Unknown')
        
        # 从 evaluated_papers.json 获取基础信息和最终评分
        scores = paper.get('scores', {})
        final_score = scores.get('final_score', 0)
        
        # 从 scores.md 读取四维评分详情
        scores_content = self.read_scores_file(short_title)
        
        # 从 summary.md 读取完整总结
        summary_content = self.read_summary_file(short_title)
        
        # 从 metadata.json 读取关键词等元信息
        metadata = self.read_metadata_file(short_title)
        keywords = metadata.get('keywords', []) if metadata else []
        
        summary_doc = f"""# {paper_title}

**arXiv ID**: {paper.get('arxiv_id', 'N/A')}  
**综合评分**: {final_score:.2f}/10  
**评估日期**: {paper.get('evaluated_date', 'N/A')}

---

## 四维评分详情

{scores_content if scores_content else '*评分详情暂缺*'}

---

## 关键词

{', '.join(keywords)}

---

## 完整论文总结

{summary_content if summary_content else '*完整总结暂缺*'}

---

*本文档由 Surrogate-Modeling Expert Agent 自动生成*  
*生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""
        
        return summary_doc
    
    def create_ku_document(self, title, content):
        """创建知识库文档"""
        try:
            client = KuApiClient()
            
            result = client.create_doc(
                repository_guid=self.ku_repo_id,
                creator_username="guhaohao",
                title=title,
                content=content,
                parent_doc_guid=self.ku_parent_doc_id,
                create_mode=2
            )
            
            if result.get('returnCode') == 200:
                doc_url = result.get('result', {}).get('url', '')
                print(f"✅ 知识库文档创建成功: {doc_url}")
                return doc_url
            else:
                error_msg = result.get('returnMessage', str(result))
                print(f"⚠️  知识库文档创建失败: {error_msg}")
                return None
                
        except Exception as e:
            print(f"⚠️  创建知识库文档异常: {e}")
            return None
    
    def send_ruliu_message(self, content, doc_url=None):
        """发送如流消息"""
        try:
            sender = GroupMessageSender()
            
            if doc_url:
                content += f"\n\n📎 **知识库链接**: {doc_url}"
            
            for user in self.recipients:
                result = sender.send_app_message(
                    to_users=user,
                    msg_type="text",
                    content=content
                )
                
                if result.get('code') == 'ok':
                    print(f"✅ 消息发送成功: {user}")
                else:
                    print(f"❌ 消息发送失败 {user}: {result}")
                    
        except Exception as e:
            print(f"❌ 发送如流消息异常: {e}")
    
    def generate_and_send(self):
        """生成周报并发送"""
        print("=" * 60)
        print("📊 开始生成周报 v2.0...")
        print("=" * 60)
        
        # 1. 加载论文数据
        print("\n📖 加载已评估论文...")
        papers = self.load_evaluated_papers()
        if not papers:
            print("❌ 没有找到已评估的论文")
            return
        
        # 2. 筛选本周论文
        print("\n📅 筛选本周论文...")
        week_papers = self.filter_week_papers(papers, days=7)
        print(f"✅ 本周评估 {len(week_papers)} 篇论文")
        
        if not week_papers:
            print("⚠️  本周没有评估新论文，使用历史数据")
            week_papers = papers
        
        # 3. 排序并选择Top 3精选论文
        print("\n🏆 筛选 Top 3 精选论文...")
        top_papers = self.sort_and_select_top(week_papers, top_n=3)
        print(f"✅ 已选择 Top {len(top_papers)} 精选论文")
        
        for i, paper in enumerate(top_papers, 1):
            print(f"   {i}. {paper.get('title', 'Unknown')[:50]}... - {paper.get('scores', {}).get('final_score', 0):.2f}分")
        
        # 4. 为每篇精选论文创建独立的知识库文档
        print("\n📚 为精选论文创建知识库文档...")
        report_date = datetime.now().strftime("%Y-%m-%d")
        summary_doc_urls = []
        
        for i, paper in enumerate(top_papers, 1):
            paper_title = paper.get('title', 'Unknown')
            short_title = paper.get('short_title', '')
            
            print(f"   [{i}/{len(top_papers)}] 创建文档: {paper_title[:50]}...")
            
            # 生成论文完整总结文档
            summary_content = self.generate_summary_markdown(paper)
            doc_title = f"[{report_date}] {short_title} - 论文总结"
            
            # 创建知识库文档
            doc_url = self.create_ku_document(doc_title, summary_content)
            
            if doc_url:
                summary_doc_urls.append({
                    'title': paper_title,
                    'url': doc_url
                })
            else:
                # 如果创建失败，使用本地文件路径
                summary_doc_urls.append({
                    'title': paper_title,
                    'url': f"../papers/{short_title}/summary.md"
                })
        
        print(f"✅ 已创建 {len(summary_doc_urls)} 个论文总结文档")
        
        # 5. 生成周报Markdown（包含知识库链接）
        print("\n📝 生成周报内容...")
        report_content = self.generate_report_markdown(top_papers, week_papers, report_date, summary_doc_urls)
        
        # 保存本地副本
        report_path = self.reports_dir / f"{report_date}_weekly_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"✅ 周报已保存: {report_path}")
        
        # 6. 创建周报知识库文档
        print("\n📚 创建周报知识库文档...")
        doc_title = f"周报 - {report_date}"
        doc_url = self.create_ku_document(doc_title, report_content)
        
        # 7. 发送如流消息
        print("\n💬 发送如流消息...")
        
        # 生成简短消息
        short_message = f"""📊 **三维几何代理模型研究周报** - {report_date}

**报告周期**: {(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")} - {report_date}
**评估论文总数**: {len(week_papers)}
**精选推荐**: Top {len(top_papers)}

🏆 **本周Top 3精选论文**:
"""
        
        for i, paper in enumerate(top_papers[:3], 1):
            short_message += f"\n{i}. **{paper.get('title', 'Unknown')[:50]}...**\n"
            short_message += f"   综合评分: {paper.get('scores', {}).get('final_score', 0):.2f}/10\n"
        
        short_message += f"\n📎 **周报链接**: {doc_url if doc_url else '知识库文档创建失败'}\n"
        
        # 添加精选论文总结链接
        if summary_doc_urls:
            short_message += "\n📄 **精选论文完整总结**:\n"
            for i, doc_info in enumerate(summary_doc_urls, 1):
                short_message += f"{i}. [{doc_info['title'][:40]}...]({doc_info['url']})\n"
        
        self.send_ruliu_message(short_message, doc_url)
        
        print("\n" + "=" * 60)
        print("✅ 周报生成和发送完成！")
        print("=" * 60)
        
        return report_path, doc_url, summary_doc_urls


def main():
    """主函数"""
    generator = WeeklyReportGenerator()
    generator.generate_and_send()


if __name__ == "__main__":
    main()
