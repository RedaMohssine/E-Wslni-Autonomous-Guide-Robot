import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class MemoryService:
    """Simple filesystem-backed memory per conversation (superrun).

    Stores a list of messages as JSON at ./memories/{conversation_id}.json
    Each message is a dict: {"role": "user"|"assistant", "text": str, "ts": isoformat}
    """

    def __init__(self, base_path: str = "./memories"):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, conversation_id: str) -> Path:
        return self.base / f"{conversation_id}.json"

    def create(self, conversation_id: str) -> None:
        p = self._path(conversation_id)
        if not p.exists():
            p.write_text(json.dumps([]))

    def exists(self, conversation_id: str) -> bool:
        return self._path(conversation_id).exists()
    
    def clear(self, conversation_id: str) -> None:
        p = self._path(conversation_id)
        if p.exists():
            p.write_text(json.dumps([]))

    def add_message(self, conversation_id: str, role: str, text: str) -> None:
        p = self._path(conversation_id)
        msgs = []
        if p.exists():
            try:
                msgs = json.loads(p.read_text())
            except Exception:
                msgs = []
        entry = {"role": role, "text": text, "ts": datetime.utcnow().isoformat()}
        msgs.append(entry)
        p.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict]:
        p = self._path(conversation_id)
        if not p.exists():
            return []
        try:
            msgs = json.loads(p.read_text())
        except Exception:
            return []
        if limit:
            return msgs[-limit:]
        return msgs
