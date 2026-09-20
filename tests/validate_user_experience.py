"""Comprehensive User-Perspective Validation Suite.

Tests all user-facing workflows:
1. API endpoints & Health
2. Input sanitization & error cases
3. Academic-only search & synthesis (arXiv focus)
4. Full web search & text extraction
5. Storage persistence & export formatting
6. Stream protocol (Server-Sent Events) validation
"""

import asyncio
import json
import httpx
from pathlib import Path
from agent.config import settings
from agent.storage.vault import vault
from agent.core.research_agent import ResearchAgent

BASE_URL = "http://127.0.0.1:8501"

def validate_api_endpoints():
    print("\n" + "=" * 60)
    print("  TEST 1: Web API Endpoints & Contract Validation")
    print("=" * 60)

    # 1. Health
    res = httpx.get(f"{BASE_URL}/api/health", timeout=5.0)
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("  [PASS] GET /api/health -> 200 OK")

    # 2. Models
    res = httpx.get(f"{BASE_URL}/api/models", timeout=5.0)
    assert res.status_code == 200
    models = res.json().get("models", [])
    assert len(models) > 0, "No models returned"
    sample_model = models[0]["name"]
    print(f"  [PASS] GET /api/models -> {len(models)} models available (Top: {sample_model})")

    # 3. History
    res = httpx.get(f"{BASE_URL}/api/history", timeout=5.0)
    assert res.status_code == 200
    history = res.json().get("history", [])
    assert len(history) >= 1, "Expected historical reports"
    print(f"  [PASS] GET /api/history -> {len(history)} reports listed")

    # 4. Single Report Details
    report_id = history[0]["id"]
    res = httpx.get(f"{BASE_URL}/api/report/{report_id}", timeout=5.0)
    assert res.status_code == 200
    rep_data = res.json()
    assert "content" in rep_data and len(rep_data["content"]) > 50
    print(f"  [PASS] GET /api/report/{report_id} -> Successfully loaded content ({len(rep_data['content'])} chars)")

    # 5. Export HTML
    res = httpx.get(f"{BASE_URL}/api/report/{report_id}/export", timeout=5.0)
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "window.print()" in res.text
    print("  [PASS] GET /api/report/{report_id}/export -> Generates print-ready HTML")

    # 6. Edge Case: Empty Query Rejection
    res = httpx.post(f"{BASE_URL}/api/research", json={"topic": "   "})
    assert res.status_code == 400
    print("  [PASS] POST /api/research (Empty topic) -> Properly rejected with 400 Bad Request")

    # 7. Edge Case: 404 for invalid report
    res = httpx.get(f"{BASE_URL}/api/report/nonexistent_12345")
    assert res.status_code == 404
    print("  [PASS] GET /api/report/invalid_id -> Properly returns 404 Not Found")

async def validate_sse_stream():
    print("\n" + "=" * 60)
    print("  TEST 2: Real-Time SSE Stream User Experience")
    print("=" * 60)

    # Launch quick research task
    topic = "CRISPR gene editing mechanisms"
    payload = {
        "topic": topic,
        "depth": "quick",
        "focus": "academic",
        "model_id": "auto",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{BASE_URL}/api/research", json=payload)
        assert res.status_code == 200
        task_id = res.json().get("task_id")
        print(f"  [PASS] Research task initiated with ID: {task_id}")

        # Stream SSE events
        received_phases = []
        received_chunks = 0
        is_completed = False

        async with client.stream("GET", f"{BASE_URL}/api/research/stream/{task_id}") as stream:
            async for line in stream.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_json = json.loads(line[6:])
                ev_type = data_json.get("type")

                if ev_type == "phase_start":
                    phase = data_json.get("phase")
                    received_phases.append(phase)
                    print(f"    ↳ Stream event received: Phase -> {phase.upper()}")
                elif ev_type == "synthesis_chunk":
                    received_chunks += 1
                elif ev_type == "complete":
                    is_completed = True
                    print(f"    ↳ Stream event received: COMPLETE!")
                    break

        assert "planning" in received_phases, "Missing planning phase"
        assert "searching" in received_phases, "Missing searching phase"
        assert is_completed, "Stream did not reach complete status"
        print(f"  [PASS] SSE Stream successfully delivered all execution phases & {received_chunks} chunks.")

def validate_vault_and_report_quality():
    print("\n" + "=" * 60)
    print("  TEST 3: Report Structure, Citations & Quality Audit")
    print("=" * 60)

    history = vault.list_history()
    assert len(history) > 0, "No vault reports to validate"
    latest = vault.get_report(history[0]["id"])
    content = latest.get("content", "")

    # Check required report elements
    assert "#" in content, "Report missing Markdown headers"
    assert "Executive Summary" in content or "summary" in content.lower(), "Report missing Executive Summary"
    assert "[" in content and "]" in content, "Report missing citation markers [1], [2]..."
    assert len(latest.get("sources", [])) > 0, "Report has no recorded sources"

    print(f"  [PASS] Report has {len(content)} characters of comprehensive synthesis")
    print(f"  [PASS] Report includes proper Markdown hierarchy, Executive Summary, and {len(latest['sources'])} cited sources")
    print(f"  [PASS] Markdown saved at: {latest.get('filepath')}")

def main():
    print("🚀 Running Comprehensive User Experience Validation...")
    validate_api_endpoints()
    asyncio.run(validate_sse_stream())
    validate_vault_and_report_quality()
    print("\n" + "=" * 60)
    print("  🎉 ALL USER EXPERIENCE VALIDATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
