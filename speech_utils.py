"""Speech utilities: German speech recognition & text-to-speech.

Features:
- Transcription (German) using OpenAI Whisper API if OPENAI_API_KEY set.
  Falls back to a stub warning if unavailable.
- Text-to-Speech using OpenAI TTS if API key set, else gTTS fallback.

Large local model dependencies are avoided for now. Replace `transcribe_audio`
with a local model (e.g. faster-whisper) later if desired.
"""
from __future__ import annotations

from typing import Tuple, Optional
import io
import os
import tempfile
from typing import Any

try:
    from openai import OpenAI  # openai>=1.x
except Exception:
    OpenAI = None  # type: ignore

try:
    from gtts import gTTS
except Exception:
    gTTS = None  # type: ignore

def _get_openai_client() -> Optional[Any]:
    # Create an OpenAI client if the package and API key are available
    try:
        if OpenAI and os.getenv("OPENAI_API_KEY"):
            return OpenAI()
    except Exception:
        pass
    return None


def transcribe_audio(file_bytes: bytes, filename: str = "audio.wav", language: str = "de") -> Tuple[str, str]:
    """Transcribe spoken German audio. Returns (text, source)."""
    client = _get_openai_client()
    if not client:
        return "(No API key / model) – unable to transcribe.", "stub"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix="_speech") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            for m in ("gpt-4o-mini-transcribe", "whisper-1"):
                try:
                    resp = client.audio.transcriptions.create(model=m, file=f, language=language)
                    text = getattr(resp, "text", None) or getattr(resp, "data", "") or str(resp)
                    if text:
                        return text.strip(), "openai"
                except Exception:
                    continue
        return "Transcription failed.", "error"
    except Exception as e:
        return f"Transcription error: {e}", "error"
    finally:
        try:
            if tmp_path:
                os.remove(tmp_path)
        except Exception:
            pass


def synthesize_speech(text: str, voice: str = "alloy", language: str = "de") -> Tuple[Optional[bytes], str, str]:
    """Generate spoken audio for German text. Returns (audio_bytes, mime, source)."""
    client = _get_openai_client()
    if client:
        try:
            resp = client.audio.speech.create(model="gpt-4o-mini-tts", voice=voice, input=text)
            audio_bytes = resp.read() if hasattr(resp, "read") else resp
            if isinstance(audio_bytes, bytes):
                return audio_bytes, "audio/mpeg", "openai"
        except Exception:
            pass

    if gTTS:
        try:
            tts = gTTS(text=text, lang=language)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue(), "audio/mpeg", "gtts"
        except Exception:
            return None, "application/octet-stream", "error"

    return None, "application/octet-stream", "stub"


__all__ = ["transcribe_audio", "synthesize_speech"]
