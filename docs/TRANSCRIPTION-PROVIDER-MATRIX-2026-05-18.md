# Transcription Provider Matrix

_Last reviewed: 2026-05-18. Sources are official provider docs/pricing pages unless noted._

WhisperForge already supports four transcription backends through
`TRANSCRIPTION_BACKEND`: OpenAI cloud transcription (`openai`), MLX Whisper
(`mlx`), whisper.cpp (`whisper_cpp`), and WhisperX (`whisperx`). This matrix
keeps the current defaults intact while making the tradeoffs visible before
adding more providers.

## Current Backends

| Backend | Accuracy posture | Streaming | Timestamps | Diarization | Local/offline | Vocabulary/customization | Cost posture | Privacy posture | Best use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `openai` (`gpt-4o-mini-transcribe` default, `gpt-4o-transcribe`, `whisper-1`) | Strong cloud baseline; OpenAI positions `gpt-4o-transcribe` as improved over Whisper for noisy/accented speech. | OpenAI offers realtime transcription models, but WhisperForge currently uses file transcription. | Current app path is text-only; OpenAI docs support transcription response formats and diarized output on `gpt-4o-transcribe-diarize`. | Candidate via `gpt-4o-transcribe-diarize`; not wired in WhisperForge yet. | No. Audio leaves the machine. | Prompting is available for some speech models; no project vocabulary dictionary in current code. | Repo pricing table tracks `gpt-4o-mini-transcribe` at `$0.003/min`, `gpt-4o-transcribe` and `whisper-1` at `$0.006/min`; verify against OpenAI pricing before changing. | Cloud API. Treat as external processing; use for non-sensitive or consented audio. | Default low-friction and low-cost cloud transcription. |
| `mlx` (`mlx-whisper`) | Good local Whisper path on Apple Silicon; quality depends on selected HF/MLX model size. | No app-level streaming. | Text-only in current app. | No built-in app diarization. | Yes, Apple Silicon local inference. | Model choice via `MLX_WHISPER_MODEL`; no vocabulary layer. | No API cost; local compute cost/time. | Best current privacy posture for Apple Silicon. Audio can stay local. | Local privacy, fast personal dictation/audio where text-only output is enough. |
| `whisper_cpp` | Good portable local Whisper path; quality depends on model file. | No app-level streaming. | Possible in upstream tooling, but current app path is text-only. | No built-in app diarization. | Yes, CPU/Metal/Core ML depending on build. | Model file/configuration only; no vocabulary layer. | No API cost; local compute cost/time. | Local/offline if model binary and runtime are local. | Local fallback outside MLX, CPU/Metal experiments, offline transcription. |
| `whisperx` | Best current in-app path for long-form alignment because it adds VAD and forced alignment on top of Whisper. | No app-level streaming. | Yes. Current direct-mode `transcribe_audio_detailed()` populates segments for chapter timestamps. | Optional via pyannote when `WHISPERX_DIARIZATION=1` and `WHISPERX_HF_TOKEN` is available. | Mostly local ASR/alignment; diarization may require downloaded models/token/license acceptance. | Model/device/compute env vars; no vocabulary layer. | No provider API cost; higher local setup/runtime cost. | Better than cloud for privacy if local models are already available; diarization token/model terms still need review. | Long-form accuracy, timestamps, chapter alignment, and speaker labels when local setup cost is acceptable. |

## Candidate Providers

| Provider | Accuracy posture | Streaming | Timestamps | Diarization | Local/offline | Vocabulary/customization | Cost posture | Privacy posture | Integration fit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI `gpt-4o-transcribe-diarize` | Same vendor as current default; OpenAI docs list a diarized transcription model. | OpenAI has realtime transcription, but this smallest path can stay file-based first. | Expected structured diarized JSON rather than current text-only parser. | Yes, via diarized response. | No. | Same OpenAI speech model family; limited app-specific vocabulary story. | Same pricing family to verify on OpenAI pricing page. | Same cloud posture as current `openai` backend. | **Smallest next integration**: same SDK/key/client, add model option and response parser tests. |
| Deepgram Nova-3 / Flux | Speech-specialized cloud provider; Nova-3 is positioned by Deepgram as high-accuracy with self-serve vocabulary adaptation. | Yes; docs include streaming transcription, and Flux is their streaming/turn-detection lane. | Yes, including timestamped utterances/words in API docs. | Yes, diarization/utterances supported. | No standard local mode. | Keyterm prompting/custom models depending on plan. | Published STT pricing; validate plan/region before adding. | Cloud API; review Deepgram privacy/security and retention terms before sensitive use. | Good external candidate for streaming, vocabulary, and diarization after OpenAI diarize. |
| AssemblyAI Universal / Streaming | Speech-specialized cloud provider with async and streaming APIs. | Yes; Universal-Streaming over WebSocket. | Yes; docs include word timestamps/confidence. | Yes; async and streaming speaker diarization are documented. | No standard local mode. | Keyterms/prompting and PII redaction features are documented. | Published pricing and free-credit model; validate plan before adding. | Cloud API; review AssemblyAI privacy/data-retention docs and DPA needs. | Strong candidate when realtime diarization or keyterms matter more than vendor minimization. |
| Google Cloud Speech-to-Text v2 | Mature cloud STT; broad language/model coverage. | Yes. | Yes; docs support word time offsets across recognition methods. | Yes via `SpeakerDiarizationConfig`/speaker labels in v2 docs. | No. | Speech adaptation, recognizers, custom models. | Published cloud pricing; usage/region complexity. | Google Cloud data governance; use when GCP controls are already acceptable. | Good enterprise/cloud option, but heavier integration surface than Deepgram/AssemblyAI. |
| Amazon Transcribe | Mature cloud STT with batch/streaming and AWS-native governance. | Yes. | Yes; AWS docs describe word timestamps. | Yes; batch and streaming speaker partitioning are documented. | No. | Custom vocabulary, vocabulary filters, custom language models. | Published AWS per-second pricing/minimums; region/feature complexity. | AWS governance/S3 controls; good if customer data already lives in AWS. | Good AWS-native option, not the smallest integration for this repo. |
| Speechmatics | Speech-specialized API with real-time/batch and deployment options. | Yes. | Yes, in product docs. | Yes; speaker/channel diarization for batch and realtime. | Offers deployment options including on-device/enterprise paths. | Custom dictionary/language options. | Published pricing; enterprise deployment likely custom. | Potentially strong privacy posture for dedicated/on-device deployments. | Worth revisiting for enterprise/local deployment, not first integration. |

## Recommendations

- **Default low-cost cloud runs:** keep `TRANSCRIPTION_BACKEND=openai` with
  `WHISPER_MODEL=gpt-4o-mini-transcribe`. It is already wired, tested, and
  priced in the repo.
- **Local privacy:** use `TRANSCRIPTION_BACKEND=mlx` on Apple Silicon. Use
  `whisper_cpp` when MLX is unavailable or when testing CPU/Metal model files.
- **Long-form accuracy and timestamps:** use `TRANSCRIPTION_BACKEND=whisperx`
  in direct mode. It is the current path that returns segments for chapter
  timestamps.
- **Speaker labels:** use `whisperx` with `WHISPERX_DIARIZATION=1` and a valid
  `WHISPERX_HF_TOKEN` today. For a cloud implementation, evaluate OpenAI
  `gpt-4o-transcribe-diarize` first because it reuses the existing OpenAI
  adapter.
- **Streaming/voice-agent experiments:** evaluate Deepgram or AssemblyAI after
  the file-based OpenAI diarization path, because both have first-class
  streaming APIs and richer vocabulary/diarization controls.

## Implemented Router Behavior

`whisperforge_core.audio.build_transcription_plan()` now exposes the provider
router contract as fixture-friendly structured data. This is a planning layer,
not a runtime behavior change: `transcribe_audio()` still uses the existing
default OpenAI path, size chunker, and sequential chunk transcription unless
the caller explicitly selects another backend or chunker.

The implemented plan fields connect this matrix to code:

| Plan field | Implemented behavior |
| --- | --- |
| `capabilities` | Reports backend limits and feature flags for `openai`, `mlx`, `whisper_cpp`, and `whisperx`. |
| `media` | Summarizes ffprobe-style media fixtures, or stays unprobed when no fixture/inspection is requested. |
| `normalization` | Emits a planned-only FFmpeg command for video extraction or large probed audio that needs mono 16 kHz PCM normalization. |
| `output_contract` | Marks text-only backends versus WhisperX segment timestamps and diarization capability. |
| `privacy` | States whether audio leaves the device, which cloud provider receives it, and which local temp artifacts are expected. |
| `cost` | States whether provider API billing applies, estimated billable minutes when duration is known, and whether local/FFmpeg compute is expected. |

Current router fixture coverage pins the main lanes:

- `openai`: cloud, billable audio-minute receipt, chunked for files over
  `CHUNK_THRESHOLD_BYTES`, and no default FFmpeg probe.
- `mlx`: local/private receipt, no provider API billing, and no normalization
  for ordinary small audio.
- `whisperx`: local timestamp-capable plan, whole-file default for large inputs
  unless `CHUNKER=vad`, and explicit diarization-capable output metadata.
- Video sources and large probed audio: planned FFmpeg extraction/resampling
  before transcription, without requiring FFmpeg in the default unit suite.

Do not enable this normalization path as a runtime default until a product
decision accepts the `privacy` and `cost` receipts for the selected backend.

## Smallest Next Integration

Add an OpenAI diarized transcription mode without changing the default.

Proposed acceptance criteria:

- Add `gpt-4o-transcribe-diarize` as an opt-in `WHISPER_MODEL` value.
- Extend the OpenAI transcription parser to accept diarized JSON and return
  plain text plus speaker/segment metadata through `TranscriptionResult`.
- Add unit tests that mock OpenAI diarized responses and assert stable speaker
  labels, timestamps, and text rendering.
- Keep `gpt-4o-mini-transcribe` as the default until a fixture comparison proves
  the diarized model is worth the extra cost or complexity.
- Document privacy/cost differences in `readme.md` before enabling it in UI.

## Large-File Router Evaluation

The archived `whisperforge` repo had useful FFmpeg large-file ideas, but the
canonical app should rebuild them through the existing provider router rather
than copying the old monolith. The current evaluation lives in
[`LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md`](LARGE-FILE-ROUTER-EVALUATION-2026-05-19.md).

Summary:

- Keep the current chunking default until fixture coverage exists.
- Add provider capability metadata before changing runtime behavior.
- Use FFmpeg/ffprobe narrowly for validation, video/audio extraction, and
  normalization.
- Preserve privacy and cleanup guarantees: no lingering temp chunks, no hidden
  cloud path for local backends, and no parallel chunking without rate-limit or
  local-memory fixtures.

## Sources

- [OpenAI Speech to text](https://platform.openai.com/docs/guides/speech-to-text?lang=curl)
- [OpenAI API pricing](https://openai.com/api/pricing/)
- [OpenAI GPT-4o Transcribe model docs](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)
- [mlx-examples Whisper README](https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md)
- [whisper.cpp README](https://github.com/ggml-org/whisper.cpp/blob/master/README.md)
- [WhisperX README](https://github.com/m-bain/whisperX)
- [Deepgram docs](https://developers.deepgram.com/documentation/)
- [Deepgram models docs](https://developers.deepgram.com/docs/models)
- [Deepgram pricing](https://deepgram.com/pricing)
- [AssemblyAI streaming docs](https://www.assemblyai.com/docs/api-reference/streaming-api/streaming-api)
- [AssemblyAI speaker diarization docs](https://www.assemblyai.com/docs/speaker-diarization)
- [AssemblyAI pricing](https://www.assemblyai.com/pricing)
- [Google Cloud Speech-to-Text overview](https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-requests)
- [Google Cloud Speech-to-Text v2 reference](https://docs.cloud.google.com/speech-to-text/docs/reference/rpc/google.cloud.speech.v2)
- [Amazon Transcribe documentation overview](https://aws.amazon.com/documentation-overview/transcribe/)
- [Amazon Transcribe diarization docs](https://docs.aws.amazon.com/transcribe/latest/dg/diarization.html)
- [Amazon Transcribe pricing](https://aws.amazon.com/transcribe/pricing/?nc1=h_ls)
- [Speechmatics docs](https://docs.speechmatics.com/)
- [Speechmatics features and deployments](https://www.speechmatics.com/product/features-and-deployments)
- [Speechmatics pricing](https://www.speechmatics.com/pricing)
