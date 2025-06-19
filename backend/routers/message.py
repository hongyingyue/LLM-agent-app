from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from typing import Optional, List, Dict, Any
import json
from loguru import logger
from ..core.agents.chat_agent import ChatAgent

router = APIRouter()

class MessageRequest(BaseModel):
    session_id: str
    content: str

class ThinkingStep(BaseModel):
    type: str  # "thinking" or "tool_call"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None

@router.options("/")
async def options_message():
    """Handle OPTIONS request for CORS preflight"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
            "Access-Control-Max-Age": "3600",
        }
    )

@router.post("/")
async def send_message(request: MessageRequest):
    try:
        logger.debug(f"Starting message processing for session {request.session_id}")
        message_id = str(uuid4())
        agent = ChatAgent()  # Get the singleton instance
        llm_instance = agent.get_session(request.session_id)  # Get or create session
        logger.debug(f"Retrieved/created session for {request.session_id}")
        
        async def generate():
            current_step = None
            buffer = ""
            
            try:
                logger.debug(f"Starting message generation for session {request.session_id}")
                async for chunk in llm_instance.chat(request.content):
                    if chunk.startswith("THINKING:"):
                        if current_step:
                            yield f"data: {json.dumps(current_step.dict())}\n\n"
                        current_step = ThinkingStep(type="thinking", content=chunk[9:].strip())
                    elif chunk.startswith("TOOL_CALL:"):
                        if current_step:
                            yield f"data: {json.dumps(current_step.dict())}\n\n"
                        tool_data = json.loads(chunk[10:])
                        logger.debug(f"Tool call detected: {tool_data['name']}")
                        current_step = ThinkingStep(
                            type="tool_call",
                            tool_name=tool_data["name"],
                            tool_args=tool_data["args"],
                            content=f"Calling tool: {tool_data['name']}"
                        )
                    elif chunk.startswith("TOOL_RESULT:"):
                        if current_step and current_step.type == "tool_call":
                            current_step.tool_result = chunk[12:].strip()
                            logger.debug(f"Tool result received for {current_step.tool_name}")
                            yield f"data: {json.dumps(current_step.dict())}\n\n"
                    else:
                        buffer += chunk
                        if buffer.endswith("\n"):
                            if current_step:
                                yield f"data: {json.dumps(current_step.dict())}\n\n"
                            current_step = ThinkingStep(type="thinking", content=buffer.strip())
                            buffer = ""
                
                if buffer:
                    if current_step:
                        yield f"data: {json.dumps(current_step.dict())}\n\n"
                    yield f"data: {json.dumps(ThinkingStep(type='thinking', content=buffer.strip()).dict())}\n\n"
                logger.debug(f"Message generation completed for session {request.session_id}")
            except Exception as e:
                logger.error(f"Error in message generation: {str(e)}", exc_info=True)
                error_step = ThinkingStep(type="thinking", content=f"Error: {str(e)}")
                yield f"data: {json.dumps(error_step.dict())}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept",
            }
        )
    except Exception as e:
        logger.error(f"Error processing message request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))