from __future__ import annotations

from typing import Optional


_whisper_model = None


def _load_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper  # type: ignore

            _whisper_model = whisper.load_model("base")
        except Exception:
            _whisper_model = None
    return _whisper_model


def transcribe_audio_file(file_path: str) -> Optional[str]:
    model = _load_model()
    if model is None:
        return None
    try:
        result = model.transcribe(file_path)
        return result.get("text") if isinstance(result, dict) else None
    except Exception:
        return None 