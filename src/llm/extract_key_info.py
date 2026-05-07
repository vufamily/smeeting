"""
Key Information Extraction Module - Extract decisions, tasks, dates from transcription
"""

import json
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KeyInfoExtractor:
    """Uses LLM to extract structured key information from transcription"""
    
    SYSTEM_PROMPT = """Bạn là một trợ lý AI chuyên trích xuất thông tin quan trọng từ biên bản cuộc họp.
Nhiệm vụ: Đọc văn bản cuộc họp và trích xuất:
1. **key_decisions**: Các quyết định quan trọng đã được đưa ra
2. **tasks**: Các công việc cần làm (bao gồm người được giao, deadline nếu có)
3. **important_dates**: Các ngày quan trọng, deadline
4. **assigned_responsibilities**: Ai được giao việc gì

Output format: JSON với các keys: key_decisions (array), tasks (array of objects với keys: task, assignee, deadline), important_dates (array), assigned_responsibilities (array)

Chỉ trả về JSON, không giải thích gì thêm."""

    USER_PROMPT_TEMPLATE = """Trích xuất thông tin từ biên bản cuộc họp sau:

{transcription}

{truncated_notice}

Trả về JSON:"""

    def __init__(self, config: dict):
        self.config = config
        llm_config = config.get("llm", {})
        self.endpoint = llm_config.get("endpoint", "http://107.98.158.221:9229/v1")
        self.model = llm_config.get("model", "gemma4")
        self.api_key = llm_config.get("api_key", "dummy")
        self.temperature = llm_config.get("temperature", 0.3)
        self.max_tokens = llm_config.get("max_tokens", 2048)
        self.timeout = llm_config.get("timeout", 60)
    
    def extract(self, transcription: str) -> Dict:
        """
        Extract key decisions, tasks, dates from transcription
        
        Args:
            transcription: Raw transcription text
            
        Returns:
            Dict with key_decisions, tasks, important_dates, assigned_responsibilities
        """
        logger.info("Extracting key info from transcription...")
        
        # Truncate if too long (LLM context limit)
        max_chars = 15000
        truncated = len(transcription) > max_chars
        transcription_to_send = transcription[:max_chars]
        
        truncated_notice = "\n[Lưu ý: Văn bản đã bị cắt ngắn do giới hạn]" if truncated else ""
        
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            transcription=transcription_to_send,
            truncated_notice=truncated_notice
        )
        
        try:
            response = self._call_llm(self.SYSTEM_PROMPT, user_prompt)
            
            # Parse JSON response
            result = self._parse_json_response(response)
            
            logger.info(f"Extracted {len(result.get('key_decisions', []))} decisions, "
                       f"{len(result.get('tasks', []))} tasks")
            
            return result
            
        except Exception as e:
            logger.error(f"Key info extraction failed: {e}")
            return self._empty_result()
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM endpoint"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        response = requests.post(
            f"{self.endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        data = response.json()
        
        return data["choices"][0]["message"]["content"]
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response, handling potential markdown code blocks"""
        import re
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON directly
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}. Response was: {response[:500]}")
            return self._empty_result()
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "key_decisions": [],
            "tasks": [],
            "important_dates": [],
            "assigned_responsibilities": []
        }
