"""Local Whisper ASR service using faster-whisper."""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import soundfile as sf
import av
from faster_whisper import WhisperModel

from common.config import get_settings


def _resolve_model_path(model_path: str) -> str:
    path = Path(model_path)
    if path.is_absolute():
        return str(path)
    backend_root = Path(__file__).resolve().parents[2]
    return str((backend_root / path).resolve())


def _resample_audio(audio: np.ndarray, original_sr: int, target_sr: int) -> np.ndarray:
    if original_sr == target_sr:
        return audio.astype(np.float32, copy=False)
    duration = len(audio) / float(original_sr)
    target_len = max(int(duration * target_sr), 1)
    old_positions = np.linspace(0.0, duration, num=len(audio), endpoint=False)
    new_positions = np.linspace(0.0, duration, num=target_len, endpoint=False)
    resampled = np.interp(new_positions, old_positions, audio).astype(np.float32)
    return resampled


def _decode_audio_with_pyav(audio_bytes: bytes) -> Tuple[np.ndarray, int]:
    """
    Fallback decoder for compressed containers/codecs (e.g. m4a/aac from mobile).
    Returns mono float32 waveform and sample rate.
    """
    container = av.open(io.BytesIO(audio_bytes))
    stream = next((s for s in container.streams if s.type == "audio"), None)
    if stream is None:
        raise ValueError("No audio stream found in uploaded file")

    audio_chunks: list[np.ndarray] = []
    sample_rate: int | None = None

    for frame in container.decode(stream):
        sample_rate = frame.sample_rate or sample_rate
        frame_array = frame.to_ndarray()
        # frame shape is typically (channels, samples)
        if frame_array.ndim == 2:
            mono = frame_array.mean(axis=0)
        else:
            mono = frame_array

        if np.issubdtype(mono.dtype, np.integer):
            max_val = max(np.iinfo(mono.dtype).max, 1)
            mono = mono.astype(np.float32) / float(max_val)
        else:
            mono = mono.astype(np.float32)

        audio_chunks.append(mono)

    if not audio_chunks or sample_rate is None:
        raise ValueError("Could not decode audio frames from uploaded file")

    return np.concatenate(audio_chunks), int(sample_rate)


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    settings = get_settings()
    model_path = _resolve_model_path(settings.ASR_MODEL_PATH)
    path_obj = Path(model_path)
    known_sizes = {
        "tiny.en",
        "tiny",
        "base.en",
        "base",
        "small.en",
        "small",
        "medium.en",
        "medium",
        "large-v1",
        "large-v2",
        "large-v3",
        "large",
        "distil-large-v2",
        "distil-medium.en",
        "distil-small.en",
        "distil-large-v3",
    }
    if path_obj.exists():
        if not path_obj.is_dir():
            raise ValueError(
                f"ASR_MODEL_PATH must be a directory. Got file: {model_path}"
            )
        resolved_model = str(path_obj)
    else:
        # Allow built-in model size names if explicitly provided
        if settings.ASR_MODEL_PATH in known_sizes:
            resolved_model = settings.ASR_MODEL_PATH
        else:
            raise ValueError(
                "ASR model path not found. "
                f"Set ASR_MODEL_PATH to a valid directory (relative to apps/backend) or use a "
                f"known size like 'small'. Provided: {settings.ASR_MODEL_PATH}"
            )
    model = WhisperModel(
        resolved_model,
        device=settings.ASR_DEVICE,
        compute_type=settings.ASR_COMPUTE_TYPE,
        cpu_threads=settings.ASR_CPU_THREADS,
    )

    if settings.ASR_FEATURE_SIZE:
        model.feature_extractor.feature_size = settings.ASR_FEATURE_SIZE
        model.feature_extractor.mel_filters = model.feature_extractor.get_mel_filters(
            model.feature_extractor.sampling_rate,
            model.feature_extractor.n_fft,
            n_mels=settings.ASR_FEATURE_SIZE,
        ).astype(np.float32)

    return model


def transcribe_audio_bytes(audio_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Transcribe WAV/FLAC audio bytes using the local Whisper model.

    Returns (transcript, metadata).
    """
    if not audio_bytes:
        return "", {"error": "empty_audio"}

    settings = get_settings()
    try:
        with sf.SoundFile(io.BytesIO(audio_bytes)) as sound_file:
            audio = sound_file.read(dtype="float32")
            sample_rate = sound_file.samplerate
    except Exception:
        # Mobile clients often upload m4a/aac which libsndfile may not recognize.
        audio, sample_rate = _decode_audio_with_pyav(audio_bytes)

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    audio = _resample_audio(audio, sample_rate, settings.ASR_SAMPLE_RATE)

    model = _get_model()
    segments, info = model.transcribe(
        audio,
        beam_size=settings.ASR_BEAM_SIZE,
        vad_filter=settings.ASR_VAD_FILTER,
        vad_parameters={"min_silence_duration_ms": settings.ASR_MIN_SILENCE_MS},
    )

    transcript_parts = [segment.text for segment in segments]
    transcript = "".join(transcript_parts).strip()

    return transcript, {
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
        "sample_rate": settings.ASR_SAMPLE_RATE,
    }
