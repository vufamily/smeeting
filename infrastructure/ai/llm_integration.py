"""
Infrastructure AI: LLM Integration
Handles communication with Gemma4 LLM endpoint.
"""

import json
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMIntegration:
    """LLM integration for Gemma4 endpoint."""

    def __init__(self, config: dict):
        self.config = config
        llm_config = config.get("llm", {})
        self.endpoint = llm_config.get("endpoint", "http://107.98.158.221:9229/v1")
        self.model = llm_config.get("model", "gemma4")
        self.api_key = llm_config.get("api_key", "dummy")
        self.temperature = llm_config.get("temperature", 0.3)
        self.max_tokens = llm_config.get("max_tokens", 4096)
        self.timeout = llm_config.get("timeout", 90)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a chat completion request to the LLM.

        Args:
            system_prompt: System prompt
            user_prompt: User message

        Returns:
            LLM response text
        """
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

        try:
            response = requests.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def extract_json(self, system_prompt: str, user_prompt: str) -> Dict:
        """Extract structured JSON from LLM response."""
        import re

        response = self.chat(system_prompt, user_prompt)

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', response)
            json_str = json_match.group(0) if json_match else response

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {}

    def generate_meeting_minutes(
        self,
        transcription: str,
        key_decisions: List[str],
        tasks: List[Dict],
        audio_segments: List = None
    ) -> str:
        """Generate meeting minutes from transcription."""
        SYSTEM_PROMPT = """Bạn là một trợ lý AI chuyên viết biên bản cuộc họp chuyên nghiệp."""

        speakers = "Unknown"
        if audio_segments:
            unique_speakers = set(seg.get("speaker_label", "Unknown") for seg in audio_segments)
            speakers = ", ".join(sorted(unique_speakers))

        decisions_str = "\n".join(f"- {d}" for d in key_decisions) if key_decisions else "- Không có quyết định"

        if tasks:
            tasks_str = "\n".join(
                f"- **{t.get('task', 'N/A')}** (Giao cho: {t.get('assignee', 'Không xác định')})"
                for t in tasks
            )
        else:
            tasks_str = "- Không có công việc được ghi nhận"

        max_chars = 12000
        transcription_to_send = transcription[:max_chars]

        user_prompt = f"""Tạo biên bản cuộc họp từ thông tin sau:

## Transcription:
{transcription_to_send}

## Key Decisions:
{decisions_str}

## Tasks:
{tasks_str}

## Speakers: {speakers}

Viết biên bản theo format chuẩn markdown."""

        return self.chat(SYSTEM_PROMPT, user_prompt)

    def extract_key_info(self, transcription: str) -> Dict:
        """Extract decisions, tasks, dates from transcription."""
        SYSTEM_PROMPT = """Bạn là AI chuyên trích xuất thông tin từ biên bản cuộc họp.
Output format: JSON với keys: key_decisions (array), tasks (array), important_dates (array)."""

        max_chars = 15000
        transcription_to_send = transcription[:max_chars]

        user_prompt = f"""Trích xuất thông tin từ biên bản cuộc họp:

{transcription_to_send}

Trả về JSON:"""

        return self.extract_json(SYSTEM_PROMPT, user_prompt)
