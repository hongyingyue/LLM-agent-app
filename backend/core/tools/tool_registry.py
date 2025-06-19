from typing import Dict, Any, Callable, Optional
import inspect
import asyncio
from loguru import logger


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        logger.info("Initialized ToolRegistry")
        
    def register(self, name: str, func: Callable):
        """
        Register a new tool function
        """
        if not callable(func):
            logger.error(f"Failed to register tool {name}: not callable")
            raise ValueError(f"Tool {name} must be callable")
        
        logger.info(f"Registering tool: {name}")
        logger.debug(f"Tool function: {func.__name__}, signature: {inspect.signature(func)}")
        self.tools[name] = func
    
    async def run_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Run a registered tool with the given parameters
        """
        logger.info(f"Attempting to run tool: {tool_name}")
        logger.debug(f"Tool parameters: {parameters}")
        
        if tool_name not in self.tools:
            logger.error(f"Tool {tool_name} not found in registry")
            raise ValueError(f"Tool {tool_name} not found")
            
        tool = self.tools[tool_name]
        logger.debug(f"Found tool function: {tool.__name__}")
        
        try:
            # Check if tool is async
            if inspect.iscoroutinefunction(tool):
                logger.debug(f"Executing async tool: {tool_name}")
                result = await tool(**parameters)
            else:
                # Run sync function in thread pool
                logger.debug(f"Executing sync tool: {tool_name} in thread pool")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool(**parameters))
            
            logger.info(f"Tool {tool_name} executed successfully")
            logger.debug(f"Tool result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
            raise
    
    def get_tool_names(self) -> list[str]:
        """Get list of registered tool names"""
        names = list(self.tools.keys())
        logger.debug(f"Retrieved tool names: {names}")
        return names
    
    def get_tool_description(self, tool_name: str) -> Optional[str]:
        """Get tool description from docstring"""
        if tool_name not in self.tools:
            logger.warning(f"Tool {tool_name} not found when getting description")
            return None
            
        description = inspect.getdoc(self.tools[tool_name])
        logger.debug(f"Retrieved description for tool {tool_name}: {description}")
        return description
