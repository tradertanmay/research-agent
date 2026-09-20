import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from agent.llm.base import BaseLLMClient

class ResearchPlan:
    def __init__(
        self,
        topic: str,
        summary: str,
        sub_questions: List[str],
        web_queries: List[str],
        academic_queries: List[str],
        wiki_queries: List[str],
    ):
        self.topic = topic
        self.summary = summary
        self.sub_questions = sub_questions
        self.web_queries = web_queries
        self.academic_queries = academic_queries
        self.wiki_queries = wiki_queries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "summary": self.summary,
            "sub_questions": self.sub_questions,
            "web_queries": self.web_queries,
            "academic_queries": self.academic_queries,
            "wiki_queries": self.wiki_queries,
        }

class ResearchPlanner:
    """Plans research decomposition, sub-questions, and targeted search queries."""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    async def create_plan(
        self,
        topic: str,
        depth: str = "standard",
        focus: str = "all"
    ) -> ResearchPlan:
        """Formulate a comprehensive research plan from a topic."""
        
        num_subq = 2 if depth == "quick" else (5 if depth == "deep" else 3)
        num_queries = 2 if depth == "quick" else (5 if depth == "deep" else 3)

        system_prompt = (
            "You are an expert Research Scientist and Intelligence Analyst. "
            "Your task is to deconstruct research topics into focused sub-questions "
            "and highly effective search engine queries. "
            "Always respond strictly with a valid JSON object."
        )

        user_prompt = f"""Deconstruct the following research topic:
Topic: "{topic}"
Research Depth: {depth} ({num_subq} sub-questions, {num_queries} queries per engine)
Primary Focus: {focus}

Return a strictly valid JSON object with the following structure:
{{
  "summary": "Brief 1-sentence statement of research scope",
  "sub_questions": [
    "Sub-question 1",
    "Sub-question 2"
  ],
  "web_queries": [
    "keyword dense search query 1",
    "keyword dense search query 2"
  ],
  "academic_queries": [
    "technical/scientific query 1",
    "technical/scientific query 2"
  ],
  "wiki_queries": [
    "core encyclopedic concept"
  ]
}}

Guidelines:
- Context Disambiguation: Determine the true domain of the topic. If terms like 'tax', 'cost', 'debt', or 'budget' appear with computing/AI terms (such as 'verifier', 'verification', 'alignment', 'inference', 'compute', 'attention', 'technical'), treat it in its COMPUTER SCIENCE / AI sense (e.g. 'verification tax in AI auditing', 'computational limits of verification in deep learning'), NOT as financial/government taxation.
- Make search queries keyword-rich and specific (avoid conversational filler like 'find me articles on...').
- Ensure sub-questions tackle distinct angles: technological state, mathematical/practical challenges, state-of-the-art literature.
- Output ONLY valid raw JSON, without any markdown backticks or commentary.
"""

        try:
            raw_response = await asyncio.wait_for(
                self.llm.generate(
                    prompt=user_prompt,
                    system=system_prompt,
                    temperature=0.3,
                ),
                timeout=12.0
            )
            plan_data = self._parse_json(raw_response)
            
            return ResearchPlan(
                topic=topic,
                summary=plan_data.get("summary", f"Investigation of {topic}"),
                sub_questions=plan_data.get("sub_questions", [topic]),
                web_queries=plan_data.get("web_queries", [topic]),
                academic_queries=plan_data.get("academic_queries", [topic]),
                wiki_queries=plan_data.get("wiki_queries", [topic]),
            )
        except Exception:
            # Resilient fast fallback if LLM takes too long or output fails
            return self._build_fallback_plan(topic, depth)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM text, stripping <think> tags."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try regex extract ```json ... ``` or { ... }
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        raise ValueError("Could not parse JSON from model response")

    def _build_fallback_plan(self, topic: str, depth: str) -> ResearchPlan:
        """Generate a heuristic research plan without LLM dependency."""
        words = topic.split()
        core_concept = " ".join(words[:4])
        return ResearchPlan(
            topic=topic,
            summary=f"In-depth research and state-of-the-art analysis of {topic}",
            sub_questions=[
                f"What are the core principles, state of the art, and recent breakthroughs in {topic}?",
                f"What are the key real-world challenges, limitations, and performance bottlenecks of {topic}?",
                f"What is the future outlook, commercialization trajectory, and open research questions for {topic}?",
            ],
            web_queries=[
                f"{topic} latest breakthroughs 2025 2026",
                f"{topic} technical challenges analysis",
                f"{topic} overview report",
            ],
            academic_queries=[
                f"{core_concept} survey review",
                f"{core_concept} benchmark performance",
            ],
            wiki_queries=[core_concept],
        )
