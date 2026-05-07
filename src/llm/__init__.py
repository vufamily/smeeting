"""
LLM Processing Module - Extract key info and generate meeting minutes using Gemma4
"""

from .extract_key_info import KeyInfoExtractor
from .generate_meeting_minutes import MeetingMinutesGenerator

__all__ = ["KeyInfoExtractor", "MeetingMinutesGenerator"]
