"""
Tools module for the backend.
"""
from .search_tool import search_duckduckgo
from .tool_registry import ToolRegistry

def initialize_tools(tool_registry: ToolRegistry):
    """Initialize and register all available tools"""
    tool_registry.register("search_duckduckgo", search_duckduckgo)
