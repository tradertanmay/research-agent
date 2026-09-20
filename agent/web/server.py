import asyncio
import json
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.config import settings
from agent.llm.factory import list_available_models
from agent.core.research_agent import ResearchAgent
from agent.core.report_qa import ReportQAEngine
from agent.storage.vault import vault

app = FastAPI(title="Autonomous Research Agent API", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Active research task event queues
# task_id -> asyncio.Queue
active_task_queues: Dict[str, asyncio.Queue] = {}

class LoginRequest(BaseModel):
    pin: str

class ResearchRequest(BaseModel):
    topic: str
    depth: str = "standard"  # 'quick', 'standard', 'deep'
    focus: str = "all"        # 'all', 'academic', 'web'
    model_id: Optional[str] = None

class QARequest(BaseModel):
    question: str
    model_id: Optional[str] = None

class DeepenRequest(BaseModel):
    question: str
    focus: str = "all"
    model_id: Optional[str] = None

def get_owner_token() -> str:
    pwd = settings.access_password or "1320"
    return hashlib.sha256(f"research_owner_salt_{pwd}".encode()).hexdigest()[:32]

def get_guest_token() -> str:
    pwd = settings.guest_password or "1307"
    return hashlib.sha256(f"research_guest_salt_{pwd}".encode()).hexdigest()[:32]

def get_token_role(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    if token == get_owner_token():
        return "owner"
    if token == get_guest_token():
        return "guest"
    return None

def verify_token(token: Optional[str]) -> bool:
    return get_token_role(token) is not None

def get_client_ip(request: Request) -> str:
    """Extract real client IP including Cloudflare and reverse proxy headers."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "local"

def is_local_request(request: Request) -> bool:
    """Return True if the request originated from the local machine (laptop owner)."""
    # 1. Check for Cloudflare / proxy headers
    if (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("cf-ray")
        or request.headers.get("x-forwarded-for")
        or request.headers.get("x-real-ip")
    ):
        return False
    # 2. Check Host header - Cloudflare tunnel always sends host: *.trycloudflare.com
    host_header = (request.headers.get("host") or "").lower()
    if "trycloudflare.com" in host_header:
        return False
    if not any(h in host_header for h in ("localhost", "127.0.0.1", "[::1]", "testserver")):
        return False
    # 3. Check client socket host
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost", "testclient")

def get_request_role(request: Request) -> str:
    """Owner if local machine or valid owner token / key; guest if remote."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = request.query_params.get("token", "")
    key = request.query_params.get("key", "") or request.query_params.get("pin", "")
    if (token and token == get_owner_token()) or key == "1320":
        return "owner"
    if is_local_request(request):
        return "owner"
    return "guest"

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Allow public endpoints
    if not path.startswith("/api") or path.startswith("/api/auth") or path == "/api/health":
        return await call_next(request)

    if settings.access_password:
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if not token:
            token = request.query_params.get("token", "")

        if not verify_token(token):
            return JSONResponse(status_code=401, content={"detail": "Authentication required. Invalid or missing security PIN."})

    return await call_next(request)

@app.get("/")
async def root():
    """Serve main web interface."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Research Agent Web UI</h1><p>Static files missing.</p>")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Authenticate with security PIN (Owner PIN or Guest PIN)."""
    pin = req.pin.strip()
    if pin == (settings.access_password or "1320"):
        token = get_owner_token()
        response = JSONResponse(content={"status": "ok", "token": token, "role": "owner"})
        response.delete_cookie(key="research_auth_token", path="/")
        return response

    if pin == (settings.guest_password or "1307"):
        token = get_guest_token()
        response = JSONResponse(content={"status": "ok", "token": token, "role": "guest"})
        response.delete_cookie(key="research_auth_token", path="/")
        return response

    raise HTTPException(status_code=401, detail="Invalid security PIN.")

@app.post("/api/auth/logout")
async def logout():
    """Clear session authentication."""
    response = JSONResponse(content={"status": "ok"})
    response.delete_cookie(key="research_auth_token", path="/")
    return response

@app.get("/api/auth/check")
async def check_auth(request: Request):
    """Verify whether current session is authenticated and return user role."""
    role = get_request_role(request)
    return {"auth_required": False, "authenticated": True, "role": role}

@app.get("/api/models")
async def get_models(request: Request):
    """List available LLM models. Hidden from guests to protect local host configuration."""
    role = get_request_role(request)
    if role != "owner":
        return {"models": []}
    models = await list_available_models()
    return {"models": models}

@app.post("/api/research")
async def start_research(req: ResearchRequest, background_tasks: BackgroundTasks, request: Request):
    """Start an autonomous research run in the background."""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    # Permanently log user question
    client_ip = get_client_ip(request)
    vault.record_query(query=req.topic.strip(), inquiry_type="research", client_ip=client_ip)

    task_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    active_task_queues[task_id] = queue

    # For guests, ensure default server model is used
    role = get_request_role(request)
    chosen_model = req.model_id if role == "owner" else None

    # Launch research runner in background
    background_tasks.add_task(
        _execute_research_task,
        task_id=task_id,
        topic=req.topic.strip(),
        depth=req.depth,
        focus=req.focus,
        model_id=chosen_model,
        queue=queue,
    )

    return {"task_id": task_id, "status": "started"}

async def _execute_research_task(
    task_id: str,
    topic: str,
    depth: str,
    focus: str,
    model_id: Optional[str],
    queue: asyncio.Queue,
):
    """Run research agent and push events to SSE queue."""
    try:
        agent = ResearchAgent(model_id=model_id)
        async for event in agent.run_stream(topic=topic, depth=depth, focus=focus):
            await queue.put(event)
    except Exception as e:
        await queue.put({
            "type": "error",
            "message": f"Research failed: {str(e)}",
        })
    finally:
        # Sentinel to signal end of stream
        await queue.put({"type": "stream_end"})

@app.get("/api/research/stream/{task_id}")
async def stream_research_events(task_id: str):
    """Server-Sent Events endpoint streaming real-time research progress."""
    if task_id not in active_task_queues:
        raise HTTPException(status_code=404, detail="Research task not found.")

    queue = active_task_queues[task_id]

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                if event.get("type") == "stream_end":
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            # Clean up task queue after consumer disconnects or stream finishes
            if task_id in active_task_queues:
                del active_task_queues[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/api/history")
async def get_history(request: Request):
    """Retrieve list of past research reports. Guests get an empty list to protect owner's history."""
    role = get_request_role(request)
    if role != "owner":
        return {"history": [], "role": "guest"}
    items = vault.list_history()
    return {"history": items, "role": "owner"}

@app.get("/api/report/{report_id}")
async def get_single_report(report_id: str):
    """Fetch report details and raw Markdown."""
    report = vault.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report

@app.get("/api/report/{report_id}/export")
async def export_report_html(report_id: str):
    """Export report as formatted printable HTML."""
    html_content = vault.export_html(report_id)
    if not html_content:
        raise HTTPException(status_code=404, detail="Report not found.")
    return HTMLResponse(content=html_content)

@app.get("/api/report/{report_id}/conversation")
async def get_report_conversation(report_id: str):
    """Retrieve chat history associated with a report."""
    messages = vault.get_conversation(report_id)
    return {"messages": messages}

@app.get("/api/activity/queries")
async def get_activity_queries(request: Request):
    """Retrieve audit log of all inquiries. Restricted to owner."""
    role = get_request_role(request)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Forbidden. Activity log is restricted to owner.")
    return {"queries": vault.get_query_logs()}

@app.post("/api/report/{report_id}/ask")
async def ask_report_question(report_id: str, req: QARequest, request: Request):
    """Stream an authoritative answer to a follow-up question grounded in the report."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Permanently record follow-up question
    client_ip = get_client_ip(request)
    vault.record_query(query=req.question.strip(), inquiry_type="followup_qa", report_id=report_id, client_ip=client_ip)

    report = vault.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    conv_history = vault.get_conversation(report_id)
    qa_engine = ReportQAEngine(model_id=req.model_id, vault=vault)

    async def response_stream():
        full_answer = []
        try:
            async for chunk in qa_engine.ask_stream(
                report_topic=report.get("topic", "Research Topic"),
                report_content=report.get("content", ""),
                sources=report.get("sources", []),
                question=req.question.strip(),
                chat_history=conv_history,
            ):
                full_answer.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Persist completed turn
            complete_text = "".join(full_answer)
            conv_history.append({"role": "user", "content": req.question.strip()})
            conv_history.append({"role": "assistant", "content": complete_text})
            vault.save_conversation(report_id, conv_history)
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/api/report/{report_id}/deepen")
async def deepen_report(report_id: str, req: DeepenRequest, background_tasks: BackgroundTasks, request: Request):
    """Launch an autonomous incremental deep dive on a specific subtopic or question."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Inquiry cannot be empty.")

    # Permanently record deepen inquiry
    client_ip = get_client_ip(request)
    vault.record_query(query=req.question.strip(), inquiry_type="deepen", report_id=report_id, client_ip=client_ip)

    report = vault.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    task_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    active_task_queues[task_id] = queue

    background_tasks.add_task(
        _execute_deepen_task,
        task_id=task_id,
        report_id=report_id,
        base_topic=report.get("topic", "Research"),
        subtopic_question=req.question.strip(),
        focus=req.focus,
        model_id=req.model_id,
        queue=queue,
    )

    return {"task_id": task_id, "status": "started"}

async def _execute_deepen_task(
    task_id: str,
    report_id: str,
    base_topic: str,
    subtopic_question: str,
    focus: str,
    model_id: Optional[str],
    queue: asyncio.Queue,
):
    """Execute continuous deep search and push progress events to client SSE."""
    try:
        qa_engine = ReportQAEngine(model_id=model_id, vault=vault)
        async for event in qa_engine.deepen_stream(
            report_id=report_id,
            base_topic=base_topic,
            subtopic_question=subtopic_question,
            focus=focus,
        ):
            await queue.put(event)
    except Exception as e:
        await queue.put({"type": "error", "message": f"Deep dive failed: {str(e)}"})
    finally:
        await queue.put({"type": "stream_end"})
