from typing import List, Dict, Any, AsyncGenerator, Optional
from uuid import uuid4
from datetime import datetime
from loguru import logger
from ..generator.llm import LLMInstance
from ...configs.config import LLMConfig
from ...configs.prompt import PromptManager, AgentRole
from ..tools.tool_registry import ToolRegistry
from ..tools import initialize_tools
from ...types import Message, ToolCall
import threading
import logging
import json

logger = logging.getLogger(__name__)

class ChatAgent:
    _instance = None
    _lock = threading.Lock()
    _sessions: Dict[str, LLMInstance] = {}
    _message_history: Dict[str, List[Dict[str, str]]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChatAgent, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.tool_registry = ToolRegistry()
            initialize_tools(self.tool_registry)
            self.messages = []
            self.tool_calls = []
            self.session_id = None
            self.llm = LLMInstance(LLMConfig())
            self.prompt_manager = PromptManager(self.llm.config.model_name)
    
    def get_session(self, session_id: str, config: Optional[LLMConfig] = None) -> LLMInstance:
        """
        Get or create an LLM instance for a specific session
        
        Args:
            session_id: Unique identifier for the session
            config: Optional configuration for the LLM instance
            
        Returns:
            LLMInstance: The LLM instance for the session
        """
        if session_id not in self._sessions:
            with self._lock:
                if session_id not in self._sessions:
                    if config is None:
                        config = LLMConfig()
                    self._sessions[session_id] = LLMInstance(config)
                    self._message_history[session_id] = []
        return self._sessions[session_id]
    
    def remove_session(self, session_id: str):
        """Remove a session and its associated LLM instance"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._message_history:
                del self._message_history[session_id]
    
    def update_session_config(self, session_id: str, config: LLMConfig):
        """Update the configuration for an existing session"""
        if session_id in self._sessions:
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id] = LLMInstance(config)
    
    def add_message(self, session_id: str, message: Dict[str, str]):
        """Add a message to the session's history"""
        if session_id in self._message_history:
            self._message_history[session_id].append(message)
    
    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Get the message history for a session"""
        return self._message_history.get(session_id, [])
    
    def clear_messages(self, session_id: str):
        """Clear the message history for a session"""
        if session_id in self._message_history:
            self._message_history[session_id] = []

    def _format_messages(self) -> List[Dict[str, str]]:
        """Format messages for LLM input"""
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
        logger.debug(f"Formatted messages for LLM: {formatted_messages}")
        return formatted_messages

    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCall]:
        """Handle tool calls and store results"""
        results = []
        logger.info(f"Processing {len(tool_calls)} tool calls")
        
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            parameters = tool_call["parameters"]
            logger.info(f"Processing tool call: {tool_name}")
            logger.debug(f"Tool parameters: {json.dumps(parameters, indent=2)}")
            
            # Create tool call record
            tool_call_record = ToolCall(
                id=uuid4(),
                message_id=uuid4(),  # This should be linked to the message that triggered the tool call
                tool_name=tool_name,
                parameters=parameters,
                result=None,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            try:
                # Execute tool
                logger.info(f"Executing tool: {tool_name}")
                result = await self.tool_registry.run_tool(tool_name, parameters)
                tool_call_record.result = str(result)
                tool_call_record.status = "completed"
                logger.info(f"Tool {tool_name} executed successfully")
                logger.debug(f"Tool result: {json.dumps(result, indent=2)}")
            except Exception as e:
                logger.error(f"Tool call failed for {tool_name}: {str(e)}", exc_info=True)
                tool_call_record.result = str(e)
                tool_call_record.status = "failed"
            
            results.append(tool_call_record)
        
        logger.info(f"Completed processing {len(results)} tool calls")
        return results

    async def chat(self, content: str, role: AgentRole = AgentRole.ASSISTANT, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Process a chat message and stream the response
        
        Args:
            content: The message content
            role: The role the agent should take (default: ASSISTANT)
            session_id: Optional session ID to use a specific LLM instance
        """
        try:
            # Use session-specific LLM if session_id is provided
            llm_instance = self.get_session(session_id) if session_id else self.llm
            self.session_id = session_id

            logger.info(f"Starting chat processing for session {self.session_id}")
            logger.debug(f"Received content: {content}")

            # Add user message
            user_message = Message(
                id=uuid4(),
                session_id=self.session_id,
                role="user",
                content=content,
                created_at=datetime.utcnow(),
                tool_calls=[]
            )
            self.messages.append(user_message)
            logger.info(f"Added user message to history. Total messages: {len(self.messages)}")

            # Get LLM response with streaming
            logger.debug("Starting LLM streaming")
            try:
                # Get appropriate prompts
                system_prompt = self.prompt_manager.get_chat_prompt(include_tools=True)
                role_prompt = self.prompt_manager.get_role_prompt(role)
                
                # Combine prompts with explicit instruction to use search
                combined_system_prompt = f"""{system_prompt}

{role_prompt}

IMPORTANT: For this specific query, you MUST use the search tool to find up-to-date information. Do not rely on your training data alone."""
                
                # Prepare messages
                messages = [
                    {"role": "system", "content": combined_system_prompt}
                ] + self._format_messages()
                
                logger.info(f"Starting LLM chat with {len(messages)} messages")
                logger.debug(f"System prompt: {combined_system_prompt}")
                
                async for chunk in llm_instance.stream_acomplete(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                ):
                    # Check if the chunk contains a tool call
                    if chunk.startswith("TOOL_CALL:"):
                        try:
                            logger.info("Detected tool call in LLM response")
                            tool_data = json.loads(chunk[10:])
                            tool_name = tool_data["name"]
                            tool_args = tool_data["args"]
                            
                            logger.info(f"Executing tool: {tool_name}")
                            logger.debug(f"Tool arguments: {json.dumps(tool_args, indent=2)}")
                            
                            # Execute the tool
                            result = await self.tool_registry.run_tool(tool_name, tool_args)
                            
                            logger.info(f"Tool {tool_name} execution completed")
                            logger.debug(f"Tool result: {json.dumps(result, indent=2)}")
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "function",
                                "name": tool_name,
                                "content": json.dumps(result)
                            })
                            
                            # Yield the tool result
                            yield f"\nSearch results:\n{json.dumps(result, indent=2)}\n"
                            
                            # Continue the conversation with the search results
                            continue
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse tool call data: {str(e)}")
                            logger.debug(f"Raw tool call data: {chunk}")
                        except Exception as e:
                            logger.error(f"Error executing tool: {str(e)}", exc_info=True)
                    else:
                        logger.debug(f"Received chunk from LLM: {chunk}")
                        yield chunk
            except Exception as e:
                logger.error(f"Error during LLM streaming: {str(e)}", exc_info=True)
                yield f"Error during LLM processing: {str(e)}"
                return

            # Add assistant message
            assistant_message = Message(
                id=uuid4(),
                session_id=self.session_id,
                role="assistant",
                content=chunk,
                created_at=datetime.utcnow(),
                tool_calls=[]
            )
            self.messages.append(assistant_message)
            logger.info(f"Added assistant message to history. Total messages: {len(self.messages)}")
            logger.info(f"Completed message processing for session {self.session_id}")

        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"

    def register_tool(self, name: str, func: callable):
        """Register a new tool with the agent"""
        logger.info(f"Registering tool: {name}")
        self.tool_registry.register(name, func)

    def get_history(self) -> List[Message]:
        """Get chat history"""
        return self.messages

    def clear_history(self):
        """Clear chat history"""
        logger.info(f"Clearing history for session {self.session_id}")
        self.messages = []
        self.tool_calls = []
