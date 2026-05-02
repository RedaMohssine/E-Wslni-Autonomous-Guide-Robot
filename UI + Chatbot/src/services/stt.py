import io
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)


# ─────────────────────── transcript post-processing ─────────────────────────
#
# Even with Whisper's prompt-biasing, the model can occasionally pick a
# closer English homophone for short utterances ("Emile" instead of
# "EMINES"). We rewrite those after the fact, regardless of detected
# language, so the LLM always sees the canonical term.
#
# Add new mishearings here as you observe them in production.

_EMINES_FIXUPS = re.compile(
    r"\b("
    r"emile|emiles|"
    r"emin|emins|emine|emines|"
    r"emi[lkn]?ess|"
    r"amines|"
    r"eminem|"
    r"i\s*mines?|ay\s*mines?|a\s*mines?|"
    r"إيميل|إيمين|إيمينس"            # Arabic mishearings of EMINES
    r")\b",
    flags=re.IGNORECASE | re.UNICODE,
)
_UM6P_FIXUPS = re.compile(
    r"\b(?:u\s*m\s*6\s*p|um\s*six\s*p|you\s*m\s*six\s*p)\b",
    flags=re.IGNORECASE,
)


def _postprocess(text: str) -> str:
    if not text:
        return text
    text = _EMINES_FIXUPS.sub("EMINES", text)
    text = _UM6P_FIXUPS.sub("UM6P", text)
    return text


# ─────────────────────── audio format detection ─────────────────────────────
#
# Browser MediaRecorder defaults vary: Chrome → WebM/Opus, Firefox → Ogg,
# Safari → MP4. The Whisper API auto-detects from the file extension we
# pass, so we sniff magic bytes and label the BytesIO accordingly.

def _guess_extension(audio_bytes: bytes) -> str:
    if not audio_bytes:
        return "wav"
    head = audio_bytes[:12]
    if head[:4] == b"RIFF":
        return "wav"
    if head[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    if head[:4] == b"OggS":
        return "ogg"
    if len(audio_bytes) >= 12 and head[4:8] == b"ftyp":
        return "m4a"
    if head[:3] == b"ID3" or head[:2] == b"\xff\xfb":
        return "mp3"
    return "webm"  # safe default for browser-recorded audio


# ─────────────────────────────── service ────────────────────────────────────


class SpeechToTextService:
    """OpenAI Whisper-based transcription.

    AssemblyAI's universal-3-pro was producing 20-30 s latencies on short
    utterances, which is unusable for a live voice UX. Whisper-1 typically
    returns in 1-3 s for the same audio, supports the same multilingual
    range (FR/EN/AR/…), and accepts a free-form `prompt` to bias the
    decoder toward proper nouns — the same role AssemblyAI's word_boost
    was supposed to fill.
    """

    # Free-text prompt fed to Whisper at the start of each transcription.
    # Whisper conditions its output as if this text immediately preceded
    # the audio, so listing campus proper nouns here makes the model
    # vastly more likely to write "EMINES" than "Emile".
    PROMPT_HINT = (
        "EMINES, UM6P, Mohammed VI Polytechnique, Ben Guerir, "
        "Cafétéria, Administration, Accueil, Foyer Étudiant, "
        "Bureau d'Aide Financière, Bureau des Admissions, "
        "Affaires Étudiantes, Bureau d'Ordre, Health Center, "
        "Laboratoire de Physique Expérimentale, "
        "Laboratoire de Projet d'Ingénierie, "
        "Laboratoire de Mécatronique, Radio Étudiante, "
        "Bureau E-tech, Bureau E-olive, Bureau E-mix, "
        "Service d'Impression, Station de Recharge, Toilettes."
    )

    MODEL = "whisper-1"

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""

        ext = _guess_extension(audio_bytes)
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = f"audio.{ext}"

        try:
            response = self.client.audio.transcriptions.create(
                model=self.MODEL,
                file=file_obj,
                prompt=self.PROMPT_HINT,
                response_format="text",
            )
        except Exception as exc:
            print(f"[STT] Whisper transcribe failed: {exc!r}")
            return ""

        # response_format="text" makes the SDK return the body as a plain
        # string, but be defensive in case a future SDK wraps it.
        text = response if isinstance(response, str) else getattr(response, "text", "")
        return _postprocess(text or "")