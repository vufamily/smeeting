"""
Meeting Minutes Generation Module - Create formatted meeting minutes from transcription
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


class MeetingMinutesGenerator:
    """Generates structured meeting minutes using LLM"""
    
    SYSTEM_PROMPT = """Bạn là một trợ lý AI chuyên viết biên bản cuộc họp chuyên nghiệp.
Nhiệm vụ: Tạo biên bản cuộc họp từ transcription và thông tin đã trích xuất.

Format chuẩn biên bản cuộc họp:
1. **Tiêu đề**: Ngày, chủ đề cuộc họp
2. **Thông tin chung**: Ngày họp, thời gian, người tham dự (nếu có)
3. **Nội dung chính**: Tóm tắt các điểm thảo luận
4. **Quyết định**: Các quyết định đã được đưa ra
5. **Công việc cần làm**: Task list với người giao, deadline
6. **Cuộc họp tiếp theo**: Thời gian, địa điểm (nếu có)

Viết bằng tiếng Việt, rõ ràng, chuyên nghiệp."""

    USER_PROMPT_TEMPLATE = """Tạo biên bản cuộc họp từ thông tin sau:

## Transcription:
{transcription}

## Key Decisions (đã trích xuất):
{key_decisions}

## Tasks (đã trích xuất):
{tasks}

## Audio Segments Summary:
- Total segments: {num_segments}
- Speakers: {speakers}

{truncated_notice}

Viết biên bản theo format chuẩn. Chỉ trả về markdown, không giải thích."""

    def __init__(self, config: dict):
        self.config = config
        llm_config = config.get("llm", {})
        self.endpoint = llm_config.get("endpoint", "http://107.98.158.221:9229/v1")
        self.model = llm_config.get("model", "gemma4")
        self.api_key = llm_config.get("api_key", "dummy")
        self.temperature = llm_config.get("temperature", 0.4)
        self.max_tokens = llm_config.get("max_tokens", 4096)
        self.timeout = llm_config.get("timeout", 90)
    
    def generate(
        self,
        transcription: str,
        key_decisions: List[str],
        tasks: List[Dict],
        audio_segments: list = None
    ) -> str:
        """
        Generate meeting minutes
        
        Args:
            transcription: Raw transcription text
            key_decisions: List of extracted decisions
            tasks: List of extracted tasks
            audio_segments: Optional list of AudioSegment objects
            
        Returns:
            Markdown-formatted meeting minutes
        """
        logger.info("Generating meeting minutes...")
        
        # Build speakers list
        speakers = "Unknown"
        if audio_segments:
            unique_speakers = set(seg.speaker_label for seg in audio_segments)
            speakers = ", ".join(sorted(unique_speakers))
        
        # Build decisions string
        decisions_str = "\n".join(f"- {d}" for d in key_decisions) if key_decisions else "- Không có quyết định được ghi nhận"
        
        # Build tasks string
        if tasks:
            tasks_str = "\n".join(
                f"- **{t.get('task', 'N/A')}** (Giao cho: {t.get('assignee', 'Không xác định')}"
                + (f", Deadline: {t.get('deadline', 'Không có')})" if t.get('deadline') else ")")
                for t in tasks
            )
        else:
            tasks_str = "- Không có công việc được ghi nhận"
        
        # Truncate if too long
        max_chars = 12000
        truncated = len(transcription) > max_chars
        transcription_to_send = transcription[:max_chars]
        truncated_notice = "\n[Lưu ý: Transcription đã bị cắt ngắn]" if truncated else ""
        
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            transcription=transcription_to_send,
            key_decisions=decisions_str,
            tasks=tasks_str,
            num_segments=len(audio_segments) if audio_segments else 0,
            speakers=speakers,
            truncated_notice=truncated_notice
        )
        
        try:
            result = self._call_llm(self.SYSTEM_PROMPT, user_prompt)
            logger.info("Meeting minutes generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Meeting minutes generation failed: {e}")
            return self._fallback_minutes(transcription, key_decisions, tasks)
    
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
    
    def _fallback_minutes(
        self,
        transcription: str,
        key_decisions: List[str],
        tasks: List[Dict]
    ) -> str:
        """Generate basic meeting minutes when LLM fails"""
        lines = [
            "# Biên bản Cuộc họp",
            f"\n**Ngày:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "\n## Transcription\n",
            transcription[:500] + "... (đã cắt ngắn)" if len(transcription) > 500 else transcription,
            "\n## Quyết định quan trọng\n"
        ]
        
        for d in key_decisions:
            lines.append(f"- {d}")
        
        if not key_decisions:
            lines.append("- Không có quyết định được ghi nhận")
        
        lines.append("\n## Công việc cần làm\n")
        
        for t in tasks:
            assignee = t.get("assignee", "Không xác định")
            task = t.get("task", "N/A")
            deadline = t.get("deadline", "Không có")
            lines.append(f"- **{task}** - Giao cho: {assignee}, Deadline: {deadline}")
        
        if not tasks:
            lines.append("- Không có công việc được ghi nhận")
        
        return "\n".join(lines)
