"""
Prompt management system for the Zero-Agent project.
This module contains all the prompts used throughout the application.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class AgentRole(str, Enum):
    """Enum for different agent roles"""
    ASSISTANT = "assistant"
    SEARCHER = "searcher"
    ANALYZER = "analyzer"
    PLANNER = "planner"

@dataclass
class ToolDescription:
    """Description of an available tool"""
    name: str
    description: str
    parameters: Dict[str, Any]

class PromptTemplates:
    """Collection of prompt templates used in the application"""
    
    # System prompts
    SYSTEM_BASE = """You are an AI assistant powered by {model_name}. 
You have access to various tools to help you complete tasks.
Always be helpful, accurate, and concise in your responses."""

    SYSTEM_WITH_TOOLS = """You are an AI assistant powered by {model_name}.
You have access to the following tools:
{tools_description}

IMPORTANT: When you are asked about any information that you're not 100% certain about, especially regarding recent developments, news, or specific details, you MUST use the search tool to find accurate and up-to-date information. Do not make assumptions or rely solely on your training data.

When you need to search for information or perform specific tasks, use the appropriate tools.
Always be helpful, accurate, and concise in your responses."""

    # Tool-specific prompts
    SEARCH_TOOL = ToolDescription(
        name="search_duckduckgo",
        description="Search the web using DuckDuckGo. Use this tool whenever you need to verify information, find recent developments, or when you're unsure about any details.",
        parameters={
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
    )

    # Role-specific prompts
    ROLE_PROMPTS = {
        AgentRole.ASSISTANT: """You are a helpful AI assistant. Your goal is to provide accurate and useful information to users.
IMPORTANT: You MUST use the search tool to verify information when:
1. Asked about recent developments or news
2. Unsure about specific details or facts
3. Need to provide up-to-date information
4. Asked about topics that might have changed since your training

Never make assumptions about information you're not certain about. Always search to verify.""",
        
        AgentRole.SEARCHER: """You are a research-focused AI assistant. Your primary goal is to find accurate and up-to-date information.
Use the search tool to gather information and provide well-researched responses.""",
        
        AgentRole.ANALYZER: """You are an analytical AI assistant. Your goal is to analyze information and provide insights.
Use the search tool to gather data and then analyze it to provide meaningful conclusions.""",
        
        AgentRole.PLANNER: """You are a planning-focused AI assistant. Your goal is to help users plan and organize tasks.
Use the search tool to gather relevant information that can help in planning."""
    }

    # Task-specific prompts
    TASK_PROMPTS = {
        "search": """Please search for information about: {query}
Focus on finding the most relevant and up-to-date information.""",
        
        "analyze": """Please analyze the following information and provide insights:
{content}""",
        
        "summarize": """Please summarize the following information concisely:
{content}""",
        
        "plan": """Please help plan the following task:
{task_description}
Consider all necessary steps and potential challenges."""
    }

    @classmethod
    def get_system_prompt(cls, model_name: str, include_tools: bool = True) -> str:
        """Get the appropriate system prompt based on configuration"""
        if include_tools:
            tools_description = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in [cls.SEARCH_TOOL]  # Add more tools here as needed
            ])
            return cls.SYSTEM_WITH_TOOLS.format(
                model_name=model_name,
                tools_description=tools_description
            )
        return cls.SYSTEM_BASE.format(model_name=model_name)

    @classmethod
    def get_role_prompt(cls, role: AgentRole) -> str:
        """Get the prompt for a specific role"""
        return cls.ROLE_PROMPTS.get(role, cls.ROLE_PROMPTS[AgentRole.ASSISTANT])

    @classmethod
    def get_task_prompt(cls, task_type: str, **kwargs) -> str:
        """Get the prompt for a specific task"""
        template = cls.TASK_PROMPTS.get(task_type)
        if template:
            return template.format(**kwargs)
        return ""

    @classmethod
    def get_tool_descriptions(cls) -> List[ToolDescription]:
        """Get all available tool descriptions"""
        return [cls.SEARCH_TOOL]  # Add more tools here as needed

class PromptManager:
    """Manager class for handling prompts in the application"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.templates = PromptTemplates()
    
    def get_chat_prompt(self, include_tools: bool = True) -> str:
        """Get the base chat prompt"""
        return self.templates.get_system_prompt(self.model_name, include_tools)
    
    def get_role_prompt(self, role: AgentRole) -> str:
        """Get a role-specific prompt"""
        return self.templates.get_role_prompt(role)
    
    def get_task_prompt(self, task_type: str, **kwargs) -> str:
        """Get a task-specific prompt"""
        return self.templates.get_task_prompt(task_type, **kwargs)
    
    def get_tool_descriptions(self) -> List[ToolDescription]:
        """Get all available tool descriptions"""
        return self.templates.get_tool_descriptions()
