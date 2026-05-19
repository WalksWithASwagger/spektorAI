# Large-File Router Evaluation

Date: 2026-05-19

Related issue: `#39`

## Decision

FFmpeg-style large-file handling should become a provider-router capability,
but not as a direct port from the archived `WalksWithASwagger/whisperforge`
implementation.

WhisperForge already has a size-based and optional VAD chunker in
`whisperforge_core/audio.py`. The right next step is to formalize large-file
policy around the existing transcription router: file validation, chunking
strategy, cleanup, backend capability flags, and fixture coverage. Runtime
defaults should not change until those tests exist.

## Current State

- `transcribe_audio()` routes files over `CHUNK_THRESHOLD_BYTES` through
  `transcribe_large_file()`.
- The default chunker uses pydub/AudioSegment and caps chunk count with
  `MAX_CHUNKS`.
- `CHUNKER=vad` can use Silero VAD to cut on speech segments before
  transcription.
- Direct-mode WhisperX can return rich segment metadata, but the generic
  large-file path is text-first.
- Chunk temp directories are cleaned after transcription.

## Legacy Signal

The archived public `whisperforge` repo documented a useful FFmpeg strategy:

- validate file size and supported audio/video formats before processing;
- use ffprobe/FFmpeg for stream inspection and audio extraction;
- normalize chunks to Whisper-friendly mono 16 kHz audio;
- process chunks in parallel only when the backend and rate limits allow it;
- reassemble transcripts in chronological order;
- define success thresholds and fallback behavior.

The old implementation also carried stale assumptions that should not move
forward: Supabase coupling, monolithic Streamlit state, and broad
"production-ready" claims without current canonical fixtures.

## Backend Fit

| Backend | Large-file policy | Timestamp policy | Parallel policy | Privacy notes |
| --- | --- | --- | --- | --- |
| `openai` | Keep chunking for API file-size limits. Prefer FFmpeg normalization before upload once fixtures exist. | Text-only today; diarized/verbose JSON needs parser tests before richer metadata. | Conservative sequential default; parallel only with rate-limit and retry fixtures. | Cloud processing; keep temp audio local except uploaded chunks. |
| `mlx` | Chunking is useful for memory/runtime control, not API limits. | Text-only today. | Parallelism is usually not worth local memory pressure on laptops. | Best local privacy path if models are present. |
| `whisper_cpp` | Chunking helps CPU/Metal runtime and avoids very long single-process calls. | Upstream can emit timestamps, but canonical parser does not yet. | Keep sequential until CLI temp-output handling is tested. | Local/offline if model and binary are local. |
| `whisperx` | Prefer whole-file or VAD-aware chunking depending on memory. | Richest current timestamp/diarization path. | Parallelism is risky because model load is heavy; evaluate after fixture benchmarks. | Mostly local, with pyannote token/model terms for diarization. |

## Proposed Router Contract

The provider router should expose capability metadata before changing runtime
behavior:

- `max_input_bytes`
- `accepts_video`
- `needs_ffmpeg`
- `supports_segments`
- `supports_diarization`
- `supports_streaming`
- `safe_parallel_chunks`
- `privacy_mode`

The large-file path should select the smallest processing plan that satisfies
the selected backend:

1. Validate extension, file size, and readable media metadata.
2. Use FFmpeg/ffprobe only when needed for video extraction, normalization, or
   files that pydub cannot inspect reliably.
3. Normalize to mono 16 kHz chunks only when the backend benefits from it.
4. Record chunk plan metadata in run artifacts.
5. Delete temp chunk files after success or failure.
6. Preserve chronological order in assembled transcript and segment metadata.

## Fixture Requirements

Before enabling a new FFmpeg route or parallel chunking:

- Unit-test file validation for audio, video, unknown extension, empty file,
  oversized file, dotfile/temp file, and generated chunk file.
- Mock ffprobe output for duration, streams, codec, channels, and sample rate.
- Test chunk-plan generation without requiring a real large media file.
- Test transcript assembly from multiple chunks, including a partial failure
  below and above the chosen success threshold.
- Test temp cleanup on success and raised error.
- For segment-capable backends, test timestamp offsets across chunks.
- Keep credentialed provider calls out of the default suite.

## Recommendation

Keep the current default large-file behavior for now. The next code issue
should add router capability metadata and fixture-only chunk planning before
any FFmpeg rewrite. FFmpeg should be introduced as a narrow media-inspection
and normalization layer, not as a second transcription architecture.
