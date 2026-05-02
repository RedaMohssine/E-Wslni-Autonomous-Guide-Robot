import base64
from src.workflow import Workflow


# SINGLE WORKFLOW INSTANCE (avoid reloading every call)
workflow = Workflow(memory_base="./memories")


# MAIN ENTRY POINT (called from Streamlit)
def handle_voice_request(payload: dict) -> dict:
    """
    Process a voice request coming from the frontend component.

    Expected payload:
    {
        "audio_base64": str,
        "mime_type": str,
        "conversation_id": str | None
    }
    """
    try:
        audio_base64 = str(payload.get("audio_base64", ""))
        if not audio_base64:
            return {"error": "Empty audio payload."}

        audio_bytes = base64.b64decode(audio_base64)
        print(f"[VOICE_DEBUG] Received audio: {len(audio_bytes)} bytes")

        conversation_id = payload.get("conversation_id")
        
        result = workflow.run_audio(audio_bytes, conversation_id=conversation_id)
        
        # 🔍 DIAGNOSTIC: Check what we got back
        print(f"[VOICE_DEBUG] Result type: {type(result)}")
        if hasattr(result, '__dict__'):
            print(f"[VOICE_DEBUG] Result attributes: {list(result.__dict__.keys())}")
        
        response_audio = _state_value(result, "response_audio")
        response_text = _state_value(result, "response")
        transcription = _state_value(result, "transcription")
        
        print(f"[VOICE_DEBUG] response_text: '{response_text[:100] if response_text else 'NONE'}...'")
        print(f"[VOICE_DEBUG] transcription: '{transcription[:100] if transcription else 'NONE'}...'")
        print(f"[VOICE_DEBUG] response_audio bytes: {len(response_audio) if response_audio else 0}")
        print(f"[VOICE_DEBUG] response_audio is None: {response_audio is None}")

        response_audio_format = _state_value(result, "response_audio_format", "audio/wav") or "audio/wav"
        response_audio_base64 = _encode_audio(response_audio)
        
        print(f"[VOICE_DEBUG] base64 length: {len(response_audio_base64) if response_audio_base64 else 0}")

        response_payload = {
            "response": response_text or "",
            "transcription": transcription or "",
            "response_audio_base64": response_audio_base64,
            "response_audio_mime_type": response_audio_format,
        }

        return response_payload

    except Exception as exc:
        import traceback
        print(f"[VOICE_ERROR] {exc}")
        print(traceback.format_exc())
        return {"error": str(exc) or "Voice processing failed."}

# HELPERS (unchanged logic, just cleaner)
def _state_value(result, key: str, default=None):
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def _encode_audio(audio_bytes: bytes | None) -> str | None:
    if not audio_bytes:
        return None
    return base64.b64encode(audio_bytes).decode("ascii")