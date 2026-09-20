import json
import httpx
import sys

def main():
    base_url = "http://localhost:8080"
    client = httpx.Client(timeout=120.0)

    print("=== LIVE INTEGRATION TEST: DOCUMENT UPLOAD & RESEARCH ===")

    # 1. Upload sample lab report
    with open("tests/sample_lab_report.txt", "rb") as f:
        upload_res = client.post(f"{base_url}/api/upload", files={"file": ("sample_lab_report.txt", f, "text/plain")})
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["doc_id"]
    print(f"1. Upload successful: doc_id={doc_id}, chars={upload_res.json()['char_count']}")

    # 2. Launch research with doc_ids
    topic = "Solid-State Sodium Battery Chemistries and Solid Electrolyte Interphase Stability"
    payload = {
        "topic": topic,
        "depth": "quick",
        "focus": "all",
        "doc_ids": [doc_id],
    }
    start_res = client.post(f"{base_url}/api/research", json=payload)
    assert start_res.status_code == 200, f"Start research failed: {start_res.text}"
    task_id = start_res.json()["task_id"]
    print(f"2. Research started: task_id={task_id}")

    # 3. Stream SSE events
    events_seen = []
    final_report = None

    with client.stream("GET", f"{base_url}/api/research/stream/{task_id}") as stream:
        for line in stream.iter_lines():
            if line.startswith("data: "):
                raw_data = line[6:].strip()
                try:
                    event = json.loads(raw_data)
                    event_type = event.get("type")
                    if event_type not in events_seen:
                        events_seen.append(event_type)
                        print(f"   [SSE Event] {event_type}: {event.get('message', '')}")
                    if event_type == "complete":
                        final_report = event.get("data")
                        break
                except Exception:
                    pass

    print(f"3. Stream finished. Events recorded: {events_seen}")
    assert "uploaded_docs_loaded" in events_seen, "uploaded_docs_loaded event was not triggered!"
    assert "search_complete" in events_seen, "search_complete event missing!"
    assert "reading_complete" in events_seen, "reading_complete event missing!"
    assert final_report is not None, "Final report was not returned!"

    report_id = final_report.get("id")
    print(f"4. Report generated: id={report_id}, topic='{final_report.get('topic')}'")
    content = final_report.get("content", "")
    assert len(content) > 500, f"Report too short: {len(content)} chars"
    print(f"   Report length: {len(content)} characters")

    # Verify user document citation in references
    assert "sample_lab_report.txt" in content or "User Document" in content, "Uploaded document missing from citations!"
    print("   [PASS] Uploaded document successfully cited in report references.")

    # 5. Test follow-up Q&A
    qa_payload = {"question": "What is the solid electrolyte used in the benchmark test?"}
    qa_res = client.post(f"{base_url}/api/report/{report_id}/ask", json=qa_payload)
    assert qa_res.status_code == 200, f"Q&A failed: {qa_res.text}"
    print(f"5. Q&A endpoint verified: status=200")

    print("\n=== ALL LIVE INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    main()
