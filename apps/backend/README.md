# PropPal Backend (ASR Integration)

## ASR + Urdu/English Chat

This backend now supports speech-to-text using a local Whisper model (faster-whisper). The `/api/chat/message/audio` endpoint accepts a WAV/FLAC audio file, transcribes it, and routes the result through the existing chat pipeline. If the transcript is detected as Urdu, it is translated to English before it hits the agent logic.

### Required environment variables

Set these in `apps/backend/.env` (paths can be **relative** to `apps/backend`).

- `ASR_MODEL_PATH=models/asr/ur_en_whisper_ct2_int8`
- `GROQ_API_KEY=...` (optional, for Urdu → English translation)

### Optional ASR tuning

- `ASR_DEVICE=cpu`
- `ASR_COMPUTE_TYPE=int8`
- `ASR_CPU_THREADS=4`
- `ASR_SAMPLE_RATE=16000`
- `ASR_VAD_FILTER=true`
- `ASR_MIN_SILENCE_MS=500`
- `ASR_BEAM_SIZE=1`

### Endpoint overview

- `POST /api/chat/message` — text input (auto-translates Urdu)
- `POST /api/chat/message/audio` — audio input (WAV/FLAC)

### Troubleshooting

- Ensure the ASR model folder exists at `ASR_MODEL_PATH`.
- `ASR_MODEL_PATH` can be a relative path from `apps/backend` or a known Whisper size (e.g., `small`).
- If translation is required, make sure `GROQ_API_KEY` is set.
- Audio must be WAV/FLAC (PCM). Use 16kHz mono when possible.
