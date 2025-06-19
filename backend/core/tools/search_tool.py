from typing import List, Dict, Any
from duckduckgo_search import DDGS
from loguru import logger

async def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search using DuckDuckGo and return results
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        List of search results, each containing title, link, and snippet
    """
    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    'title': r['title'],
                    'link': r['link'],
                    'snippet': r['body']
                })
            return results
    except Exception as e:
        logger.error(f"Error in DuckDuckGo search: {str(e)}", exc_info=True)
        raise e 