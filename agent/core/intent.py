import re
from typing import Dict, Any, List, Optional
from agent.llm.base import BaseLLMClient

# Recognised valid acronyms that are short but researchable
VALID_SHORT_ACRONYMS = {
    "ai", "agi", "dna", "rna", "gpu", "cpu", "tpu", "llm", "ev", "iot", "vr", "ar",
    "ssb", "crispr", "nft", "dao", "pci", "api", "sdk", "cli", "sql", "git"
}

# Greetings and conversational phrases
GREETINGS = {
    "hi", "hello", "hey", "howdy", "hola", "yo", "sup", "greetings",
    "good morning", "good evening", "good afternoon", "hi there", "hello there",
    "test", "testing"
}

# Obvious fragmented / incomplete prompts
QUESTION_WORDS = {"who", "what", "where", "when", "why", "how", "which", "whose", "whom"}
DANGLING_PREFIXES = {
    "who is", "what is", "where is", "when did", "why is", "how to", "how do", 
    "how does", "tell me", "tell me about", "explain", "can you", "i want", 
    "i want to know", "help", "who are", "what are", "which is"
}

GENERIC_AMBIGUOUS_WORDS = {
    "car", "cars", "phone", "phones", "computer", "computers", "food", "money", 
    "stuff", "thing", "things", "people", "science", "business", "technology", "news"
}

# Typo corrections for common research queries
TYPO_CORRECTIONS = {
    "verifer": "verifier",
    "verifcation": "verification",
    "papaers": "papers",
    "papaer": "paper",
    "resrch": "research",
    "artifical": "artificial",
    "inteligence": "intelligence",
    "machien": "machine",
    "learnign": "learning",
    "algoritm": "algorithm",
    "algoritms": "algorithms",
    "quatum": "quantum",
    "battey": "battery",
    "batteies": "batteries",
}

# Directives indicating the user wants papers or articles
META_DIRECTIVES_REGEX = re.compile(
    r"\b(search\s*(?:for\s*)?(?:research\s*)?(?:papers?|articles?|studies)|"
    r"find\s*(?:me\s*)?(?:papers?|articles?)|"
    r"look\s*up\s*(?:papers?|articles?|studies\s*on)?|"
    r"papers?\s*(?:on|about)|"
    r"research\s*(?:on|about)?)\b",
    re.IGNORECASE,
)

class QueryIntent:
    def __init__(
        self,
        is_researchable: bool,
        is_greeting: bool = False,
        prefer_academic: bool = False,
        clarification_message: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        refined_topic: Optional[str] = None,
    ):
        self.is_researchable = is_researchable
        self.is_greeting = is_greeting
        self.prefer_academic = prefer_academic
        self.clarification_message = clarification_message
        self.suggestions = suggestions or []
        self.refined_topic = refined_topic

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_researchable": self.is_researchable,
            "is_greeting": self.is_greeting,
            "prefer_academic": self.prefer_academic,
            "clarification_message": self.clarification_message,
            "suggestions": self.suggestions,
            "refined_topic": self.refined_topic,
        }

class IntentAnalyzer:
    """Analyzes user queries before researching to ensure clarity and prevent meaningless searches."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client

    async def analyze(self, raw_query: str) -> QueryIntent:
        """Analyze query to check if it's researchable or needs clarification."""
        query = raw_query.strip()

        # 1. Apply typo corrections first
        corrected_query = query
        for typo, fix in TYPO_CORRECTIONS.items():
            corrected_query = re.sub(r"\b" + re.escape(typo) + r"\b", fix, corrected_query, flags=re.I)

        # 2. Detect if user requested academic papers explicitly
        has_paper_directive = bool(re.search(r"\b(papers?|arxiv|studies|literature|journal)\b", corrected_query, re.I))

        # 3. Strip meta-directives (e.g. "search papers", "find studies")
        cleaned_topic = META_DIRECTIVES_REGEX.sub("", corrected_query).strip(" .,!?:;")
        if not cleaned_topic:
            cleaned_topic = corrected_query.strip(" .,!?:;")

        normalized = re.sub(r"[^\w\s]", "", cleaned_topic).strip().lower()
        words = normalized.split()

        # 4. Extremely short / empty check
        if not words:
            return QueryIntent(
                is_researchable=False,
                clarification_message="Please enter a topic or question to research.",
                suggestions=[
                    "Breakthroughs in solid-state batteries in 2026",
                    "Rust vs Go for backend distributed services",
                    "CRISPR prime editing vs base editing mechanisms",
                ]
            )

        # 5. Check for greetings or conversational phrases
        if normalized in GREETINGS or (len(words) == 1 and words[0] in GREETINGS):
            return QueryIntent(
                is_researchable=False,
                is_greeting=True,
                clarification_message=(
                    "👋 Hello! I am your **Autonomous Deep Research Agent**.\n\n"
                    "Rather than small talk, I specialize in conducting deep investigations across the Web, "
                    "arXiv preprints, and Wikipedia, then synthesizing cited reports.\n\n"
                    "**To start, what topic would you like me to research?** You can click any topic below:"
                ),
                suggestions=[
                    "Breakthroughs in solid-state batteries in 2026",
                    "CRISPR prime editing vs base editing mechanisms",
                    "Rust vs Go for high-throughput distributed systems",
                    "Current state of humanoid robotics in 2026",
                ]
            )

        # 6. Check for single question words (e.g. "who", "what", "why")
        if len(words) == 1 and words[0] in QUESTION_WORDS:
            suggestions = self._get_question_word_suggestions(words[0])
            return QueryIntent(
                is_researchable=False,
                clarification_message=(
                    f"You entered **\"{query}\"**, which is an open question word. "
                    f"What specific person, technology, or discovery are you looking for?"
                ),
                suggestions=suggestions
            )

        # 7. Check for dangling prefixes (e.g. "who is", "tell me about")
        if normalized in DANGLING_PREFIXES:
            return QueryIntent(
                is_researchable=False,
                clarification_message=(
                    f"Your query **\"{query}\"** is incomplete. "
                    "Could you specify what or who you would like to investigate?"
                ),
                suggestions=[
                    f"{query} the current leader in humanoid robotics",
                    f"{query} commercial fusion energy milestones",
                    f"{query} room-temperature superconductor claims",
                ]
            )

        # 8. Check for overly generic single words (e.g. "cars", "phone")
        if len(words) == 1 and words[0] in GENERIC_AMBIGUOUS_WORDS:
            return QueryIntent(
                is_researchable=False,
                clarification_message=(
                    f"**\"{query}\"** is very broad. To produce a rigorous report, "
                    "what specific angle would you like to explore?"
                ),
                suggestions=[
                    f"Next-generation solid-state battery tech for {words[0]}",
                    f"Autonomous self-driving AI developments in {words[0]}",
                    f"Market trends and sustainability analysis for {words[0]} in 2026",
                ]
            )

        # 9. Very short query (< 3 chars) not in known acronyms
        if len(normalized) < 3 and normalized not in VALID_SHORT_ACRONYMS:
            return QueryIntent(
                is_researchable=False,
                clarification_message=(
                    f"**\"{query}\"** is too brief for an in-depth research investigation. "
                    "Please provide a more detailed question or topic."
                ),
                suggestions=[
                    "Quantum computing algorithms and encryption impacts",
                    "Advances in solid-state lithium battery tech",
                    "How large language models handle complex reasoning",
                ]
            )

        # Query is clear and researchable
        return QueryIntent(
            is_researchable=True,
            prefer_academic=has_paper_directive,
            refined_topic=cleaned_topic
        )

    def _get_question_word_suggestions(self, q_word: str) -> List[str]:
        """Provide contextual suggestions when user types who/what/why/how."""
        q = q_word.lower()
        if q == "who":
            return [
                "Who are the leaders in commercial fusion energy in 2026?",
                "Who invented CRISPR Cas9 gene editing technology?",
                "Who are the top competitors in humanoid robotics?",
                "Who are the pioneers of modern quantum computing?",
            ]
        elif q == "what":
            return [
                "What are the key differences between Rust and Go?",
                "What are the latest breakthroughs in solid-state batteries?",
                "What is quantum error correction and how does it work?",
                "What is the current state of AGI research in 2026?",
            ]
        elif q == "how":
            return [
                "How do mRNA vaccines work at a cellular level?",
                "How does nuclear fusion achieve net energy gain?",
                "How do transformer neural networks process attention?",
                "How are solid-state electrolytes manufactured?",
            ]
        elif q == "why":
            return [
                "Why are solid-state batteries difficult to commercialize?",
                "Why is quantum computing hard to scale to millions of qubits?",
                "Why is Rust preferred for memory-safe systems programming?",
            ]
        elif q == "where":
            return [
                "Where is nuclear fusion closest to commercial viability?",
                "Where are the largest semiconductor manufacturing facilities?",
            ]
        return [
            f"{q_word.capitalize()} are the latest advances in solid-state batteries?",
            f"{q_word.capitalize()} does quantum computing compare to classical computing?",
        ]
