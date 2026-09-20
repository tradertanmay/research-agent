import asyncio
import re
from typing import AsyncIterator, Dict, Any, List, Optional
from agent.llm.ollama_client import OllamaClient
from agent.search.academic_search import AcademicSearchEngine
from agent.search.web_search import WebSearchEngine
from agent.scraper.crawler import WebCrawler, CrawledDocument
from agent.storage.vault import VaultManager

class ReportQAEngine:
    """Handles grounded Q&A and continuous incremental research on existing reports."""

    def __init__(self, model_id: Optional[str] = None, vault: Optional[VaultManager] = None):
        self.llm = OllamaClient(model_name=model_id or "auto")
        self.academic_search = AcademicSearchEngine()
        self.web_search = WebSearchEngine()
        self.crawler = WebCrawler(timeout=10, max_concurrent=4)
        self.vault = vault or VaultManager()

    async def ask_stream(
        self,
        report_topic: str,
        report_content: str,
        sources: List[Dict[str, Any]],
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Stream an authoritative answer to a follow-up question grounded in the report and sources."""
        # Trim report content if exceedingly long (local context budget)
        trimmed_report = report_content[:12000]

        # Summarize available sources
        sources_summary = []
        for idx, src in enumerate(sources[:12], 1):
            title = src.get("title", "Untitled")
            src_type = src.get("source", "web")
            url = src.get("url", "")
            snippet = (src.get("snippet") or "")[:150]
            sources_summary.append(f"[{idx}] {title} ({src_type.upper()}) - {url}\n    Excerpt: {snippet}")

        sources_text = "\n".join(sources_summary) if sources_summary else "None listed."

        # Format history
        history_lines = []
        if chat_history:
            for msg in chat_history[-6:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines) if history_lines else "None."

        system_prompt = (
            "You are an Elite Research Specialist and Technical Consultant. "
            "You are answering a user's follow-up questions regarding a specific research report and its cited sources. "
            "RULES:\n"
            "1. Ground your answers strictly in the provided report context and cited evidence sources.\n"
            "2. Cite evidence using bracket notation like [1], [2] or author/paper names whenever referring to findings.\n"
            "3. Format clearly using Markdown (bolding, lists, code blocks, or comparison tables).\n"
            "4. Be direct, comprehensive, and insightful. Do not evade technical details."
        )

        user_prompt = f"""REPORT TOPIC: "{report_topic}"

REPORT CONTENT:
{trimmed_report}

AVAILABLE CITED SOURCES:
{sources_text}

PRIOR CONVERSATION:
{history_text}

USER FOLLOW-UP QUESTION:
"{question}"

Please provide a clear, comprehensive, and rigorously grounded answer:"""

        in_think_block = False
        async for chunk in self.llm.generate_stream(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=2500,
        ):
            # Guard against raw <think> tags from thinking models
            if "<think>" in chunk:
                in_think_block = True
                chunk = chunk.replace("<think>", "")
            if in_think_block:
                if "</think>" in chunk:
                    in_think_block = False
                    chunk = chunk.split("</think>", 1)[1]
                else:
                    continue
            if chunk:
                yield chunk

    async def deepen_stream(
        self,
        report_id: str,
        base_topic: str,
        subtopic_question: str,
        focus: str = "all",
    ) -> AsyncIterator[Dict[str, Any]]:
        """Conduct targeted autonomous research to deepen a report with fresh evidence and append an addendum."""
        yield {
            "type": "deepen_start",
            "phase": "planning",
            "message": f"Formulating targeted queries to deepen research on: '{subtopic_question}'...",
        }

        # 1. Plan focused queries
        plan_prompt = f"""You are an autonomous research planner.
Base Research Topic: "{base_topic}"
Subtopic / Follow-up Inquiry to Deepen: "{subtopic_question}"

Generate 4 focused, highly specific search queries to uncover new technical evidence, academic papers, or industry breakthroughs.
Provide exactly 2 Web search queries and 2 Academic search queries.
Format:
WEB: query 1
WEB: query 2
ACADEMIC: query 1
ACADEMIC: query 2
"""
        raw_plan = await self.llm.generate(prompt=plan_prompt, temperature=0.2, max_tokens=300)
        
        web_queries = []
        academic_queries = []
        for line in raw_plan.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("WEB:"):
                web_queries.append(line[4:].strip().strip('"'))
            elif line.upper().startswith("ACADEMIC:"):
                academic_queries.append(line[9:].strip().strip('"'))

        if not web_queries:
            web_queries = [f"{base_topic} {subtopic_question}", f"{subtopic_question} analysis"]
        if not academic_queries:
            academic_queries = [f"{base_topic} {subtopic_question}", f"{subtopic_question} arxiv paper"]

        # 2. Search phase
        yield {
            "type": "deepen_progress",
            "phase": "searching",
            "message": f"Executing deep searches across arXiv and web for: '{subtopic_question}'...",
        }

        search_tasks = []
        if focus in ("all", "web"):
            for q in web_queries[:2]:
                search_tasks.append(self.web_search.search(q, max_results=3))
        if focus in ("all", "academic"):
            for q in academic_queries[:2]:
                search_tasks.append(self.academic_search.search(q, max_results=3))

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        new_sources = []
        seen_urls = set()

        for res in search_results:
            if isinstance(res, list):
                for s in res:
                    if s.url and s.url not in seen_urls:
                        seen_urls.add(s.url)
                        new_sources.append(s)

        if not new_sources:
            fallback_res = await self.web_search.search(f"{base_topic} {subtopic_question}", max_results=3)
            for s in fallback_res:
                if s.url and s.url not in seen_urls:
                    seen_urls.add(s.url)
                    new_sources.append(s)

        yield {
            "type": "deepen_progress",
            "phase": "reading",
            "count": len(new_sources),
            "message": f"Discovered {len(new_sources)} new sources. Extracting content...",
        }

        # 3. Read content
        target_urls = [s.url for s in new_sources if not s.url.endswith(".pdf")][:5]
        crawled_docs: List[CrawledDocument] = await self.crawler.fetch_all(target_urls)
        doc_map = {d.url: d.text[:2000] for d in crawled_docs if d.success and d.text}

        # 4. Synthesize Addendum
        yield {
            "type": "deepen_progress",
            "phase": "synthesizing",
            "message": "Synthesizing deep dive addendum with new findings...",
        }

        evidence_blocks = []
        for idx, s in enumerate(new_sources, 1):
            text = doc_map.get(s.url, s.snippet)
            authors = f" | Authors: {', '.join(s.authors)}" if s.authors else ""
            date = f" | Date: {s.published_date}" if s.published_date else ""
            evidence_blocks.append(f"New Source [{idx}]: {s.title} ({s.source.upper()}){authors}{date}\nURL: {s.url}\nExcerpt: {text}\n")

        evidence_str = "\n".join(evidence_blocks)

        synth_prompt = f"""You are authoring a Deep Dive Addendum to expand an existing research report.
Base Topic: "{base_topic}"
Specific Inquiry: "{subtopic_question}"

New Evidence Gathered:
{evidence_str}

REQUIREMENTS:
1. Provide a detailed, rigorous analysis answering "{subtopic_question}".
2. Cite the new sources using bracket notation [1], [2], etc.
3. Include:
   - ### Core Findings & Mechanism Details
   - ### Comparative Insights & Trade-offs
   - ### Implications for "{base_topic}"
4. Be precise, technical, and objective.
"""
        addendum_chunks = []
        in_think = False
        async for chunk in self.llm.generate_stream(
            prompt=synth_prompt,
            system="You are a principal technical author adding deep dive sections to research dossiers.",
            temperature=0.3,
            max_tokens=3000,
        ):
            if "<think>" in chunk:
                in_think = True
                chunk = chunk.replace("<think>", "")
            if in_think:
                if "</think>" in chunk:
                    in_think = False
                    chunk = chunk.split("</think>", 1)[1]
                else:
                    continue
            if chunk:
                addendum_chunks.append(chunk)
                yield {
                    "type": "deepen_chunk",
                    "chunk": chunk,
                }

        full_addendum = "".join(addendum_chunks).strip()
        # Clean any accidental <think> remaining
        full_addendum = re.sub(r"<think>.*?</think>", "", full_addendum, flags=re.DOTALL).strip()

        # 5. Persist to Vault
        new_source_dicts = [s.to_dict() for s in new_sources]
        updated_report = self.vault.append_addendum(
            report_id=report_id,
            subtopic_title=subtopic_question,
            addendum_content=full_addendum,
            new_sources=new_source_dicts,
        )

        yield {
            "type": "deepen_complete",
            "report_id": report_id,
            "subtopic": subtopic_question,
            "addendum": full_addendum,
            "new_sources_count": len(new_sources),
            "updated_content": updated_report["content"] if updated_report else "",
            "message": f"Successfully expanded report with {len(new_sources)} new cited sources.",
        }
