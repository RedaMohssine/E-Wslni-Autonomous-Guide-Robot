# models.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Destination:
    location_name: str
    category: str
    description: str
    latitude: float
    longitude: float
    building: str = ""
    floor: str = ""
    accessible: bool = False
    aliases: List[str] = field(default_factory=list)
    matched_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "location_name": self.location_name,
            "category": self.category,
            "description": self.description,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "building": self.building,
            "floor": self.floor,
            "accessible": self.accessible,
            "aliases": list(self.aliases),
            "matched_name": self.matched_name,
        }


@dataclass
class State:
    audio_input: Optional[bytes] = None
    user_query: Optional[str] = None
    transcription: Optional[str] = None
    retrieved_docs: Optional[List[str]] = None
    response: Optional[str] = None
    conversation_id: Optional[str] = None
    response_audio: Optional[bytes] = None
    response_audio_format: Optional[str] = None
    # Language code ("fr" | "en" | "ar") emitted by the LLM via the [lang:xx]
    # tag at the end of its reply. The tag is stripped from `response` before
    # storage/display; this field carries the parsed value for TTS routing.
    detected_language: Optional[str] = None
