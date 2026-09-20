import json
import re
import datetime
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from agent.config import settings

class VaultManager:
    """Manages persistent storage for research sessions and reports."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.vault_dir
        self.reports_dir = self.base_dir / "reports"
        self.conversations_dir = self.base_dir / "conversations"
        self.history_file = self.base_dir / "history.json"
        self.queries_log_file = self.base_dir / "user_queries.json"
        self.queries_markdown_file = self.base_dir / "user_queries.md"
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def _load_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def save_report(
        self,
        topic: str,
        content: str,
        sources: List[Dict[str, Any]],
        model: str,
        report_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save report to Markdown file and register in history index."""
        report_id = report_id or str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now().isoformat()

        # Clean slug for filename
        slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", topic.lower()).strip("_")[:40]
        filename = f"{slug}_{report_id}.md"
        filepath = self.reports_dir / filename

        # Add header metadata to markdown file
        full_md = (
            f"<!--\n"
            f"Research ID: {report_id}\n"
            f"Topic: {topic}\n"
            f"Model: {model}\n"
            f"Date: {timestamp}\n"
            f"Sources: {len(sources)}\n"
            f"-->\n\n"
            f"{content}\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_md)

        # Update history
        record = {
            "id": report_id,
            "topic": topic,
            "filename": filename,
            "filepath": str(filepath),
            "model": model,
            "sources_count": len(sources),
            "sources": sources,
            "created_at": timestamp,
        }

        history = self._load_history()
        # Prepend to make latest appear first
        history.insert(0, record)
        self._save_history(history)

        return record

    def list_history(self) -> List[Dict[str, Any]]:
        """Return all historical research reports."""
        return self._load_history()

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Fetch report details and raw markdown content."""
        history = self._load_history()
        for item in history:
            if item.get("id") == report_id:
                filepath = Path(item["filepath"])
                if filepath.exists():
                    with open(filepath, "r", encoding="utf-8") as f:
                        item["content"] = f.read()
                    return item
        return None

    def get_conversation(self, report_id: str) -> List[Dict[str, Any]]:
        """Retrieve stored chat conversation thread for a report."""
        conv_file = self.conversations_dir / f"{report_id}.json"
        if conv_file.exists():
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_conversation(self, report_id: str, messages: List[Dict[str, Any]]) -> None:
        """Persist chat conversation thread for a report."""
        conv_file = self.conversations_dir / f"{report_id}.json"
        with open(conv_file, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

    def record_query(
        self,
        query: str,
        inquiry_type: str = "research",  # "research", "followup_qa", "deepen"
        report_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Permanently record every question, prompt, or follow-up inquiry asked by any user."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": timestamp,
            "query": query.strip(),
            "type": inquiry_type,
            "report_id": report_id,
            "client_ip": client_ip or "local",
        }

        # 1. Update JSON logs
        logs = self.get_query_logs()
        logs.insert(0, entry)
        try:
            with open(self.queries_log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # 2. Append to human-readable Markdown log
        type_badge = {
            "research": "🔍 NEW RESEARCH",
            "followup_qa": "💬 FOLLOW-UP Q&A",
            "deepen": "🔬 DEEPEN SEARCH",
        }.get(inquiry_type, inquiry_type.upper())

        md_line = f"- **`[{timestamp}]`** `{type_badge}` *(from {entry['client_ip']})*: **{query.strip()}**"
        if report_id:
            md_line += f" *(Report: `{report_id}`)*"
        md_line += "\n"

        try:
            if not self.queries_markdown_file.exists():
                with open(self.queries_markdown_file, "w", encoding="utf-8") as f:
                    f.write("# 📝 User Inquiries & Questions Log\n\nAll questions, prompts, and research queries asked by users:\n\n")
            with open(self.queries_markdown_file, "a", encoding="utf-8") as f:
                f.write(md_line)
        except Exception:
            pass

        return entry

    def get_query_logs(self) -> List[Dict[str, Any]]:
        """Retrieve full log of all questions asked by users."""
        if self.queries_log_file.exists():
            try:
                with open(self.queries_log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def append_addendum(
        self,
        report_id: str,
        subtopic_title: str,
        addendum_content: str,
        new_sources: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Append a newly researched addendum and new citations to an existing report."""
        report = self.get_report(report_id)
        if not report:
            return None

        filepath = Path(report["filepath"])
        current_text = report.get("content", "")

        # Separate body from references
        parts = re.split(r"\n##\s*(?:References|Annotated Sources|Bibliography)", current_text, flags=re.I)
        body = parts[0].strip()

        # Merge and deduplicate sources
        existing_sources = report.get("sources", [])
        seen_urls = {s.get("url") for s in existing_sources if s.get("url")}
        merged_sources = list(existing_sources)

        for src in new_sources:
            url = src.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged_sources.append(src)

        # Build refreshed references section
        ref_lines = ["\n\n## References & Annotated Sources\n"]
        for idx, src in enumerate(merged_sources, 1):
            title = src.get("title", "Untitled")
            url = src.get("url", "#")
            src_type = (src.get("source") or "web").upper()
            authors = src.get("authors") or []
            pub_date = src.get("published_date")
            snippet = (src.get("snippet") or "").replace("\n", " ")[:140].strip()

            author_str = f" *({', '.join(authors[:4])})*" if authors else ""
            date_str = f" — *{pub_date}*" if pub_date else ""
            badge = f" `[{src_type}]`"

            pdf_link = ""
            if "arxiv.org/abs/" in url:
                pdf_url = url.replace("/abs/", "/pdf/")
                if not pdf_url.endswith(".pdf"):
                    pdf_url += ".pdf"
                pdf_link = f" • [[📄 PDF]]({pdf_url})"
            elif "arxiv.org/pdf/" in url:
                pdf_link = f" • [[📄 PDF]]({url})"

            ref_lines.append(f"[{idx}] [{title}]({url}){badge}{pdf_link}{author_str}{date_str}\n   > {snippet}...")

        full_refs = "\n\n".join(ref_lines)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        addendum_block = (
            f"\n\n---\n\n"
            f"## 🔬 Deep Dive Addendum: {subtopic_title}\n"
            f"*Researched & Appended on {timestamp}*\n\n"
            f"{addendum_content.strip()}"
        )

        updated_markdown = f"{body}{addendum_block}{full_refs}\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(updated_markdown)

        # Update history record
        history = self._load_history()
        for item in history:
            if item.get("id") == report_id:
                item["sources_count"] = len(merged_sources)
                item["sources"] = merged_sources
                break
        self._save_history(history)

        report["content"] = updated_markdown
        report["sources"] = merged_sources
        report["sources_count"] = len(merged_sources)
        return report

    def export_html(self, report_id: str) -> Optional[str]:
        """Export report as a standalone printable HTML document."""
        report = self.get_report(report_id)
        if not report:
            return None

        # Basic HTML template for standalone printing
        content = report.get("content", "")
        # Escape or convert basic lines
        escaped_title = report.get("topic", "Research Report")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{escaped_title} - Research Report</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            color: #1a202c;
            background: #ffffff;
        }}
        pre, code {{ background: #f7fafc; padding: 2px 5px; border-radius: 4px; font-family: monospace; }}
        pre {{ padding: 16px; overflow-x: auto; border: 1px solid #e2e8f0; }}
        blockquote {{ border-left: 4px solid #3182ce; padding-left: 16px; color: #4a5568; margin-left: 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 10px 14px; text-align: left; }}
        th {{ background: #edf2f7; font-weight: 600; }}
        a {{ color: #2b6cb0; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .meta-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 24px; font-size: 0.9em; color: #64748b; }}
        @media print {{
            body {{ margin: 0; padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <button onclick="window.print()" style="padding: 8px 16px; background: #2b6cb0; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">🖨️ Print / Save as PDF</button>
        <span style="font-size: 0.85em; color: #718096;">Generated by Autonomous Research Agent</span>
    </div>
    <div class="meta-box">
        <strong>Topic:</strong> {report.get('topic')}<br>
        <strong>Model:</strong> {report.get('model')} | <strong>Date:</strong> {report.get('created_at', '')[:10]} | <strong>Sources:</strong> {report.get('sources_count', 0)}
    </div>
    <div id="content"></div>
    <script>
        document.getElementById('content').innerHTML = marked.parse({json.dumps(content)});
    </script>
</body>
</html>"""
        return html

vault = VaultManager()
