import datetime
import re
from typing import List, Dict, Any, AsyncIterator, Optional
from agent.llm.base import BaseLLMClient
from agent.search.base import SearchResult
from agent.scraper.crawler import CrawledDocument

class ResearchReport:
    def __init__(
        self,
        id: str,
        topic: str,
        content: str,
        sources: List[Dict[str, Any]],
        model: str,
        created_at: str,
    ):
        self.id = id
        self.topic = topic
        self.content = content
        self.sources = sources
        self.model = model
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "content": self.content,
            "sources": self.sources,
            "model": self.model,
            "created_at": self.created_at,
        }

class ResearchSynthesizer:
    """Synthesizes gathered evidence and generates a cited research report."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def format_references(self, sources: List[SearchResult]) -> str:
        """Generate verified, clickable, properly formatted references from actual sources."""
        if not sources:
            return ""
        lines = ["## References & Annotated Sources\n"]
        for idx, src in enumerate(sources, 1):
            author_str = f" *({', '.join(src.authors)})*" if src.authors else ""
            date_str = f" — *{src.published_date}*" if src.published_date else ""
            badge = f" `[{src.source.upper()}]`"
            clean_snippet = src.snippet.replace("\n", " ")[:140].strip()
            
            # Enrich arXiv papers with direct PDF download link
            pdf_link = ""
            if "arxiv.org/abs/" in src.url:
                pdf_url = src.url.replace("/abs/", "/pdf/")
                if not pdf_url.endswith(".pdf"):
                    pdf_url += ".pdf"
                pdf_link = f" • [[📄 PDF]]({pdf_url})"
            elif "arxiv.org/pdf/" in src.url:
                pdf_link = f" • [[📄 PDF]]({src.url})"

            lines.append(f"[{idx}] [{src.title}]({src.url}){badge}{pdf_link}{author_str}{date_str}\n   > {clean_snippet}...")
        return "\n\n".join(lines)

    def clean_and_attach_references(self, content: str, sources: List[SearchResult]) -> str:
        """Strip <think> blocks and attach guaranteed genuine, clickable references."""
        # 1. Strip think tags
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # 2. If model generated a partial or placeholder references section, remove it
        parts = re.split(r"\n##\s*(?:References|Annotated Sources|Bibliography)", cleaned, flags=re.I)
        body = parts[0].strip()

        # 3. Attach guaranteed accurate references
        return f"{body}\n\n{self.format_references(sources)}"

    async def synthesize(
        self,
        topic: str,
        sub_questions: List[str],
        sources: List[SearchResult],
        crawled_docs: List[CrawledDocument],
    ) -> str:
        """Synthesize gathered research findings into a complete structured Markdown report."""
        prompt, system = self._build_synthesis_prompt(topic, sub_questions, sources, crawled_docs)
        
        raw_text = await self.llm.generate(
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=6000,
        )
        return self.clean_and_attach_references(raw_text, sources)

    async def synthesize_stream(
        self,
        topic: str,
        sub_questions: List[str],
        sources: List[SearchResult],
        crawled_docs: List[CrawledDocument],
    ) -> AsyncIterator[str]:
        """Stream synthesis tokens directly from the LLM."""
        prompt, system = self._build_synthesis_prompt(topic, sub_questions, sources, crawled_docs)
        
        async for chunk in self.llm.generate_stream(
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=6000,
        ):
            yield chunk

    def _build_synthesis_prompt(
        self,
        topic: str,
        sub_questions: List[str],
        sources: List[SearchResult],
        crawled_docs: List[CrawledDocument],
    ) -> tuple[str, str]:
        system_prompt = (
            "You are an Elite Research Director and Academic Synthesis Author. "
            "Your objective is to produce comprehensive, highly rigorous, objective, and deeply cited "
            "investigative research reports. You cite evidence meticulously using numbered brackets like [1], [2], [3], "
            "corresponding strictly to the numbered sources provided. Never fabricate facts or URLs."
        )

        # Build numbered evidence catalog
        evidence_lines = []
        doc_map = {doc.url: doc for doc in crawled_docs if doc.success}

        for idx, src in enumerate(sources, 1):
            body_text = ""
            if src.url in doc_map and doc_map[src.url].text:
                body_text = doc_map[src.url].text[:2500]
            else:
                body_text = src.snippet

            authors_str = f" | Authors: {', '.join(src.authors)}" if src.authors else ""
            date_str = f" | Date: {src.published_date}" if src.published_date else ""

            evidence_lines.append(
                f"Source [{idx}]:\n"
                f"Title: {src.title}\n"
                f"URL: {src.url}\n"
                f"Type: {src.source}{authors_str}{date_str}\n"
                f"Content Summary:\n{body_text}\n"
                f"{'-'*40}"
            )

        evidence_str = "\n\n".join(evidence_lines)
        questions_str = "\n".join(f"- {q}" for q in sub_questions)

        user_prompt = f"""Synthesize an authoritative research report on:
"{topic}"

Key Questions to Address:
{questions_str}

Available Evidence Sources:
{evidence_str}

CRITICAL RULES:
1. Ground your entire analysis in the specific domain of "{topic}". If "{topic}" is a computer science / AI concept (e.g. "verifier tax"), analyze it strictly as a computer science / AI concept, NOT as financial/accounting taxation.
2. In your body paragraphs, cite the relevant numbered sources using bracket notation [1], [2], [3] for every key finding or claim.
3. STRUCTURE:
   # Comprehensive Research Report: [Precise Title]
   ## Executive Summary
   ## Detailed Analysis Sections (answer each sub-question thoroughly with [1], [2] citations and comparative tables)
   ## Technical Challenges, Bottlenecks & Limitations
   ## Future Outlook & Research Directions
4. Do NOT output placeholder text like '[Title](URL)' or fake domains. All references will be verified against the sources above.
"""

        return user_prompt, system_prompt
