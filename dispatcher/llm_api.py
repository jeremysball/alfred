"""Direct LLM API calls (bypassing pi for now)."""
import aiohttp
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class LLMApi:
    """Direct LLM API calls."""
    
    @staticmethod
    async def complete(
        provider: str,
        api_key: str,
        model: str,
        messages: list[dict],
        timeout: int = 300
    ) -> str:
        """Complete a conversation and return the response."""
        if provider == "zai":
            return await LLMApi._zai_complete(api_key, model or "glm-4.7", messages, timeout)
        elif provider == "moonshot":
            return await LLMApi._moonshot_complete(api_key, model or "moonshot-v1-8k", messages, timeout)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    async def _zai_complete(
        api_key: str,
        model: str,
        messages: list[dict],
        timeout: int
    ) -> str:
        """Call ZAI Coding Plan API."""
        url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 4096
            }
            
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"ZAI API error {resp.status}: {text}")
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    @staticmethod
    async def _moonshot_complete(
        api_key: str,
        model: str,
        messages: list[dict],
        timeout: int
    ) -> str:
        """Call Moonshot API."""
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 4096
            }
            
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Moonshot API error {resp.status}: {text}")
                
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
