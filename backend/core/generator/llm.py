import os
import litellm
from litellm import _should_retry, acompletion
from typing import List, Dict, Any, Optional, AsyncGenerator
from loguru import logger
from dotenv import load_dotenv
from ...types import Message
from ...configs.config import config
import json

load_dotenv()

# Set the API key from config
litellm.api_key = config.llm.api_key
if not litellm.api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")

class LLMInstance:
    def __init__(self, config=None):
        self.config = config if config is not None else config.llm
        self._initialize_llm()
        logger.info(f"INIT LLM: {self.config.model_name}")
    
    def _initialize_llm(self):
        """Initialize the LLM with the given configuration"""
        # LiteLLM doesn't require explicit initialization
        pass
    
    def generate(self, prompt: str, messages: List[Dict[str, str]] = None) -> str:
        """
        Generate a response based on the prompt and message history
        
        Args:
            prompt: The current prompt
            messages: Optional message history
            
        Returns:
            str: The generated response
        """
        if messages is None:
            messages = []
        
        # Add the current prompt to messages
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = litellm.completion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            return response.choices[0].message.content
        except Exception as e:
            if _should_retry(e):
                return self.generate(prompt, messages)
            logger.error(f"Error in generate: {str(e)}", exc_info=True)
            raise e

    async def chat(self, content: str) -> AsyncGenerator[str, None]:
        """
        Stream chat responses with the given content
        
        Args:
            content: The message content
            
        Yields:
            str: Chunks of the response
        """
        try:
            messages = [{"role": "user", "content": content}]
            response = await litellm.acompletion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            raise e

    async def stream_acomplete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion with the given messages
        """
        try:
            logger.debug(f"Starting stream completion with messages: {messages}")
            
            # Add function definitions for available tools
            functions = [
                {
                    "name": "search_duckduckgo",
                    "description": "Search the web using DuckDuckGo. Use this tool whenever you need to verify information, find recent developments, or when you're unsure about any details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
            
            response = await litellm.acompletion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                stream=True,
                functions=functions,
                function_call={"name": "search_duckduckgo"},  # Force the LLM to use search when appropriate
                **kwargs
            )
            
            logger.info("Starting to process LLM response stream")
            current_function_call = None
            
            async for chunk in response:
                if hasattr(chunk.choices[0].delta, 'function_call') and chunk.choices[0].delta.function_call:
                    function_call = chunk.choices[0].delta.function_call
                    if not current_function_call:
                        current_function_call = {"name": "", "arguments": ""}
                    
                    if hasattr(function_call, 'name'):
                        current_function_call["name"] = function_call.name
                    if hasattr(function_call, 'arguments'):
                        current_function_call["arguments"] += function_call.arguments
                    
                    if current_function_call["name"] and current_function_call["arguments"]:
                        try:
                            # Try to parse the arguments as JSON
                            args = json.loads(current_function_call["arguments"])
                            yield f"TOOL_CALL:{json.dumps({'name': current_function_call['name'], 'args': args})}\n"
                            current_function_call = None
                        except json.JSONDecodeError:
                            # If not complete JSON yet, continue collecting
                            continue
                elif chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"Received content chunk from LLM: {content}")
                    yield content
            logger.info("Finished processing LLM response stream")
            
        except Exception as e:
            logger.error(f"Error in stream_acomplete: {str(e)}", exc_info=True)
            if _should_retry(e):
                logger.info("Retrying stream completion...")
                async for chunk in self.stream_acomplete(messages, **kwargs):
                    yield chunk
            else:
                raise e

class LiteLLM:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LiteLLM, cls).__new__(cls)
            cls._instance.config = config.llm
            cls._instance.messages = []
        return cls._instance

    def __init__(self):
        self.config = config.llm
        self.messages = []

    def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Complete a chat completion with the given messages
        """
        try:
            response = litellm.completion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            if _should_retry(e):
                return self.complete(messages, **kwargs)
            raise e


class AsyncLiteLLM:
    def __init__(self):
        self.config = config.llm
        self.messages = []
        logger.info(f"Initialized AsyncLiteLLM with model: {self.config.model_name}")

    async def acomplete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Asynchronously complete a chat completion with the given messages
        """
        try:
            logger.debug(f"Sending completion request with messages: {messages}")
            response = await acompletion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                **kwargs
            )
            logger.debug(f"Received completion response: {response}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in acomplete: {str(e)}", exc_info=True)
            if _should_retry(e):
                logger.info("Retrying completion request...")
                return await self.acomplete(messages, **kwargs)
            raise e
    
    async def stream_acomplete(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion with the given messages
        """
        try:
            logger.debug(f"Starting stream completion with messages: {messages}")
            response = await litellm.acompletion(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                stream=True,
                **kwargs
            )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"Received stream chunk: {content}")
                    yield content
        except Exception as e:
            logger.error(f"Error in stream_acomplete: {str(e)}", exc_info=True)
            if _should_retry(e):
                logger.info("Retrying stream completion...")
                async for chunk in self.stream_acomplete(messages, **kwargs):
                    yield chunk
            else:
                raise e