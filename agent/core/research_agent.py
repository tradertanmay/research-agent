import asyncio
import uuid
import datetime
import re
from typing import AsyncIterator, Dict, Any, List, Optional
from agent.llm.factory import get_llm_client
from agent.llm.base import BaseLLMClient
from agent.search.base import SearchResult
from agent.search.web_search import WebSearchEngine
from agent.search.academic_search import AcademicSearchEngine
from agent.search.wiki_search import WikiSearchEngine
from agent.scraper.crawler import WebCrawler, CrawledDocument
from agent.core.planner import ResearchPlanner, ResearchPlan
from agent.core.synthesizer import ResearchSynthesizer, ResearchReport
from agent.core.intent import IntentAnalyzer
from agent.storage.vault import vault

class ResearchAgent:
    """Master Autonomous Research Agent coordinating planning, multi-source search,
    deep crawling, and report synthesis.
    """

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or "auto"
        self.llm: BaseLLMClient = get_llm_client(self.model_id)
        self.intent_analyzer = IntentAnalyzer(self.llm)
        self.planner = ResearchPlanner(self.llm)
        self.synthesizer = ResearchSynthesizer(self.llm)
        self.web_search = WebSearchEngine()
        self.academic_search = AcademicSearchEngine()
        self.wiki_search = WikiSearchEngine()
        self.crawler = WebCrawler(max_concurrent=5)

    async def run(
        self,
        topic: str,
        depth: str = "standard",
        focus: str = "all",
    ) -> Dict[str, Any]:
        """Execute a full research cycle and return the completed report."""
        final_result = None
        async for event in self.run_stream(topic, depth, focus):
            if event.get("type") == "complete":
                final_result = event.get("data")
        return final_result or {}

    async def run_stream(
        self,
        topic: str,
        depth: str = "standard",
        focus: str = "all",
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute research cycle yielding real-time events for SSE / terminal output."""
        task_id = str(uuid.uuid4())[:8]

        # ----------------------------------------------------
        # 0. QUERY INTENT UNDERSTANDING & SCOPE VALIDATION
        # ----------------------------------------------------
        intent = await self.intent_analyzer.analyze(topic)
        if not intent.is_researchable:
            yield {
                "type": "greeting" if intent.is_greeting else "clarification",
                "message": intent.clarification_message,
                "suggested_topics": intent.suggestions,
            }
            return

        # ----------------------------------------------------
        # 1. PLANNING PHASE
        # ----------------------------------------------------
        yield {
            "type": "phase_start",
            "phase": "planning",
            "message": f"Formulating research strategy for '{topic}'...",
        }

        plan: ResearchPlan = await self.planner.create_plan(topic, depth=depth, focus=focus)

        yield {
            "type": "plan_complete",
            "phase": "planning",
            "plan": plan.to_dict(),
            "message": f"Generated research plan with {len(plan.sub_questions)} key sub-questions.",
        }

        # ----------------------------------------------------
        # 2. MULTI-SOURCE SEARCH PHASE
        # ----------------------------------------------------
        yield {
            "type": "phase_start",
            "phase": "searching",
            "message": "Initiating queries across Web, Academic (arXiv), and Encyclopedic sources...",
        }

        search_tasks = []

        # Web queries
        if focus in ("all", "web"):
            for q in plan.web_queries:
                search_tasks.append(self.web_search.search(q, max_results=4))

        # Academic queries
        if focus in ("all", "academic"):
            for q in plan.academic_queries:
                search_tasks.append(self.academic_search.search(q, max_results=4))

        # Wikipedia background
        if focus in ("all", "web"):
            for q in plan.wiki_queries:
                search_tasks.append(self.wiki_search.search(q, max_results=2))

        search_results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten and deduplicate by URL
        seen_urls = set()
        deduped_sources: List[SearchResult] = []

        for res in search_results_lists:
            if isinstance(res, list):
                for item in res:
                    if item.url and item.url not in seen_urls:
                        seen_urls.add(item.url)
                        deduped_sources.append(item)

        # Resilient fallback: if no sources were discovered (e.g. strict academic filter with 0 hits), query web fallback
        if not deduped_sources:
            fallback_results = await self.web_search.search(f"{topic} research paper analysis", max_results=5)
            for item in fallback_results:
                if item.url and item.url not in seen_urls:
                    seen_urls.add(item.url)
                    deduped_sources.append(item)

        yield {
            "type": "search_complete",
            "phase": "searching",
            "count": len(deduped_sources),
            "sources": [s.to_dict() for s in deduped_sources],
            "message": f"Discovered {len(deduped_sources)} relevant sources across search indices.",
        }

        # ----------------------------------------------------
        # 3. DEEP CONTENT EXTRACTION / CRAWLING
        # ----------------------------------------------------
        yield {
            "type": "phase_start",
            "phase": "reading",
            "message": f"Deep crawling and reading content from top {min(len(deduped_sources), 8)} sources...",
        }

        # Target top 6-10 sources for in-depth scraping
        crawl_limit = 5 if depth == "quick" else (10 if depth == "deep" else 7)
        target_sources = deduped_sources[:crawl_limit]
        target_urls = [s.url for s in target_sources if not s.url.endswith(".pdf")]

        crawled_docs: List[CrawledDocument] = await self.crawler.fetch_all(target_urls)
        success_docs = [d for d in crawled_docs if d.success and len(d.text) > 100]

        yield {
            "type": "reading_complete",
            "phase": "reading",
            "count": len(success_docs),
            "message": f"Extracted clean readable content from {len(success_docs)} articles.",
        }

        # ----------------------------------------------------
        # 4. SYNTHESIS & REPORT GENERATION
        # ----------------------------------------------------
        yield {
            "type": "phase_start",
            "phase": "synthesizing",
            "message": "Analyzing evidence, cross-referencing facts, and generating cited report...",
        }

        accumulated_chunks = []
        try:
            async for chunk in self.synthesizer.synthesize_stream(
                topic=topic,
                sub_questions=plan.sub_questions,
                sources=target_sources,
                crawled_docs=success_docs,
            ):
                accumulated_chunks.append(chunk)
                yield {
                    "type": "synthesis_chunk",
                    "chunk": chunk,
                }
            full_report_content = "".join(accumulated_chunks)
        except Exception:
            # Fallback to non-streaming if provider stream errored
            full_report_content = await self.synthesizer.synthesize(
                topic=topic,
                sub_questions=plan.sub_questions,
                sources=target_sources,
                crawled_docs=success_docs,
            )

        # Ensure genuine clickable references are cleanly attached
        full_report_content = self.synthesizer.clean_and_attach_references(
            full_report_content, target_sources
        )

        # ----------------------------------------------------
        # 5. PERSISTENCE & COMPLETION
        # ----------------------------------------------------
        saved_record = vault.save_report(
            topic=topic,
            content=full_report_content,
            sources=[s.to_dict() for s in target_sources],
            model=self.llm.model_name,
            report_id=task_id,
        )

        yield {
            "type": "complete",
            "phase": "complete",
            "message": "Research successfully completed and saved to vault!",
            "data": {
                "id": task_id,
                "report_id": task_id,
                "topic": topic,
                "content": full_report_content,
                "sources": [s.to_dict() for s in target_sources],
                "filepath": saved_record["filepath"],
                "created_at": saved_record["created_at"],
                "model": self.llm.model_name,
            }
        }
