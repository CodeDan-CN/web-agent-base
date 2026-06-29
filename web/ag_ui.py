import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from runtime.ag_ui.adapter import AGUIEventAdapter
from runtime.engine import RuntimeEngine
from runtime.failure_message import build_exception_failure_message, exception_reason
from runtime.models import RuntimeRequest
from schema.api.agent import AgentRunRequest

ag_ui_router = APIRouter(prefix="/agent", tags=["ag-ui"])


@ag_ui_router.post("/run/stream")
async def run_agent_stream(request: AgentRunRequest) -> StreamingResponse:
    """
    按 AG-UI 事件流运行 Agent。

    Args:
        request (AgentRunRequest): Agent 运行请求。

    Returns:
        StreamingResponse: SSE 事件流响应。
    """
    request_id = request.request_id or uuid4().hex
    runtime_request = RuntimeRequest(
        user_id=request.user_id,
        agent_id=request.agent_id,
        session_id=request.session_id,
        request_id=request_id,
        message=request.message,
        metadata=request.metadata,
    )
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def emit(event: dict) -> None:
        """
        写入事件队列。

        Args:
            event (dict): AG-UI 事件。
        """
        await queue.put(event)

    async def run_runtime() -> None:
        """
        后台运行 Runtime。
        """
        try:
            await RuntimeEngine().run(runtime_request, AGUIEventAdapter(emit))
        except Exception as exc:
            adapter = AGUIEventAdapter(emit)
            thread_id = runtime_request.session_id or ""
            message_id = adapter.new_message_id()
            failure_answer = build_exception_failure_message(exc)
            await emit(adapter.text_message_start(request_id, thread_id, message_id))
            await emit(
                adapter.text_message_content(
                    request_id,
                    thread_id,
                    message_id,
                    failure_answer,
                )
            )
            await emit(adapter.text_message_end(request_id, thread_id, message_id))
            await emit(adapter.run_error(request_id, thread_id, exception_reason(exc)))
        finally:
            await queue.put(None)

    async def event_generator():
        """
        SSE 事件生成器。
        """
        task = asyncio.create_task(run_runtime())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                payload = json.dumps(event, ensure_ascii=False)
                yield f"event: ag-ui\ndata: {payload}\n\n"
            await task
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
