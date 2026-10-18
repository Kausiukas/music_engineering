# Cloud STT/TTS tournament line-up (T0-6)

- Date: 2026-10-18
- Question (issue #12): Which cloud STT and TTS services enter the first tournament, per language?
- Scope: lyrics transcription from isolated vocal stems (sung, sometimes spoken/rap) in English (EN) and Lithuanian (LT); we need word-level timestamps, ideally with confidence, and force-align ourselves afterwards. TTS voices for EN and LT, plus singing synthesis or voice conversion.
- Method: official docs, pricing pages, and API references, all opened on 2026-10-18. Anything marked **unverified** was not confirmed on a page we opened.

## Recommended line-up

### STT, Lithuanian (5 entrants)

| # | Entrant | Why it is in |
|---|---|---|
| 1 | Local Whisper `base` (baseline) | Current baseline; `lt` is in Whisper's language list. |
| 2 | ElevenLabs Scribe v2 | LT listed in the "High Accuracy" tier (5–10% WER); word timestamps, per-word `logprob`, character-level timestamps, audio-event tags. $0.22/h. |
| 3 | Speechmatics (Enhanced) | LT supported; per-word `start_time`/`end_time`/`confidence`; best LT FLEURS WER on its own (vendor) page; no training without opt-in; 7-day auto-delete. $0.75/h. |
| 4 | Deepgram Nova-3 (`lt`) | LT supported; per-word start/end/confidence; cheapest ($0.26/h mono). Send `mip_opt_out=true`. |
| 5 | Azure AI Speech, fast transcription (`lt-LT`) | LT supported for fast transcription; word offsets/durations; no data retained for fast transcription. Confidence is per phrase only. |

Reserves (enter only if a slot frees up): Google Chirp 3 (`lt-LT` is Preview; no real word confidence; word timestamps "degrade transcription" and cap batch at ~20 min), AWS Transcribe (`lt-LT` batch; per-word confidence; but content may be stored to improve models unless opted out), AssemblyAI Universal-2 (LT in the "moderate accuracy, 25–50% WER" tier).

### STT, English (5 entrants)

| # | Entrant | Why it is in |
|---|---|---|
| 1 | Local Whisper `base` (baseline) | Current baseline. |
| 2 | ElevenLabs Scribe v2 | Same as LT; one integration covers both languages. |
| 3 | AssemblyAI Universal-3.5 Pro | Per-word `start`/`end`/`confidence`; $0.21/h. Opt out of training (paid accounts only). |
| 4 | Deepgram Nova-3 | Per-word confidence; $0.26/h; same integration as LT. |
| 5 | Speechmatics (Enhanced) | Same integration as LT; strong data terms. |

Reserves: OpenAI `whisper-1` (the only OpenAI model with word timestamps, 25 MB file cap, no confidence documented; useful as a "cloud Whisper" reference point), AWS Transcribe, Azure fast transcription, Google Chirp 3.

OpenAI `gpt-transcribe` / `gpt-4o-transcribe` are **not** entered: the guide says only `whisper-1` supports `timestamp_granularities[]`, so they return no word timestamps.

### TTS / voice (3 entrants)

| # | Entrant | LT | EN | Why |
|---|---|---|---|---|
| 1 | Edge-TTS (baseline) | yes (current baseline) | yes | Baseline. Note: Edge-TTS is an unofficial client of Microsoft's read-aloud endpoint; no published API terms (**unverified**). Its official counterpart is Azure Neural TTS below. |
| 2 | Azure AI Speech Neural TTS | `lt-LT-OnaNeural`, `lt-LT-LeonasNeural` | many | Full SSML `<prosody>` with `pitch`, `contour`, `range`, `rate`; the licensed way to run the same voices as Edge-TTS. |
| 3 | ElevenLabs (Eleven v3 / v4 for speech; Voice Changer and Eleven Music as the singing/conversion probe) | v3/v4 list `lt` | yes | Most expressive voices; the only candidate here with a voice-conversion (speech-to-speech) API and a music/vocals generator. |

Reserve: Google Cloud TTS Chirp 3: HD (30 `lt-LT` voices) — but Chirp 3: HD supports neither SSML nor rate/pitch parameters, which weakens it for prosody/pitch work.

No cloud provider found offers a documented, controllable singing-voice synthesis API (notes/lyrics in, sung audio out) in Lithuanian. That stays a local-path item.

## Main caveats

1. **Lithuanian gaps.** OpenAI's newer transcription models lack word timestamps (and the guide does not list languages). AssemblyAI's best model (Universal-3.5 Pro) does not cover LT; Universal-2 does, in its weakest accuracy tier. Google Chirp 3 LT is Preview. Deepgram's Flux and domain models are EN only (Nova-3/Nova-2 general cover LT). ElevenLabs Multilingual v2, Flash v2.5, and the speech-to-speech models do not list LT.
2. **Word confidence.** Real per-word confidence: Deepgram, Speechmatics, AWS, AssemblyAI, ElevenLabs (`logprob`), Google `chirp_2`. Not available: Google Chirp 3 (value "isn't truly a confidence score"), Azure fast transcription (phrase-level only in the samples), OpenAI `whisper-1` (not documented).
3. **Training on uploads by default.** Deepgram (Model Improvement Partnership; opt out per request with `mip_opt_out=true`), AssemblyAI (ToS 4.3 licence for training; free tier cannot opt out; EU servers are excluded), AWS Transcribe ("may temporarily store your content to continuously improve" models; opt-out policy **unverified**, not opened). No training by default: OpenAI API, Speechmatics (opt-in only, for a 33% discount), Azure (no retention for fast/real-time). ElevenLabs: zero-retention mode is enterprise-only; "no training on your data" appears only on a marketing page (**unverified** in the terms).
4. **Vocal stems hurt Whisper.** On Jam-ALT, HTDemucs-separated vocals raised Whisper v3 WER from 35.5% to 47.9%, often by emitting the wrong language. Always pass an explicit language code in the tournament, for every service.
5. **No singing evidence** was found for any cloud STT vendor on a page we opened; the tournament itself must produce it.

## STT comparison

Prices are as published on 2026-10-18 (pay-as-you-go, list price).

| Service / model | LT | EN | Word timestamps | Word confidence | Diarization | Max file | Price / audio hour | Limits | Data use / retention | Singing evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Local Whisper (base, large-v3) | yes (`lt`) | yes | yes (local) | via token probs (local) | no | n/a | free (local) | n/a | local | Jam-ALT: v3 35.5% WER, 47.9% with Demucs separation |
| Google STT V2 Chirp 3 | Preview (`lt-LT`, `eu`) | yes | optional; "some transcription degradation is expected"; Recognize/BatchRecognize only | no (not a true confidence) | yes (single channel; LT row says no) | sync <1 min recommended; batch ~1 h, ~20 min with word timestamps | $0.96/h ($0.016/min) **unverified** (pricing page did not render; figure from search snippet); dynamic batch $0.18/h **unverified** | **unverified** | V1 data-logging opt-in exists; V2 terms **unverified** | none found |
| Google STT V2 `chirp_2` | yes (`asia-southeast1`, `europe-west4`) | yes | **unverified** | yes | no | **unverified** | as above, **unverified** | **unverified** | as above | none found |
| Azure AI Speech, fast transcription | yes (`lt-LT`) | yes | yes (word offset/duration ms) | phrase-level only | yes (2–35 speakers) | <5 h, <500 MB | not rendered on pricing page (**unverified**); free tier 5 h/month real-time | **unverified** | fast and real-time: not retained; batch: customer storage, `timeToLive` | none found |
| AWS Transcribe | yes (`lt-LT`, batch; streaming in most regions) | yes | yes (every word) | yes (every word) | yes | **unverified** (limits page not opened) | $0.36/h ($0.006/min, US East example); 60 min/month free for 12 months | job queueing available | "may temporarily store your content to continuously improve" models; deletion via Support case; default-bucket transcripts expire after 90 days | none found |
| Deepgram Nova-3 | yes (`lt`) | yes | yes | yes | yes (param not confirmed on opened page) | 2 GB | $0.26/h mono, $0.31/h multilingual; $200 free credit | 50 concurrent REST requests | Model Improvement Partnership unless `mip_opt_out=true`; opted-out data kept only for processing | none found |
| AssemblyAI Universal-2 | yes (`lt`, 25–50% WER tier) | yes | yes | yes | add-on, language-dependent | **unverified** | $0.15/h (+$0.02/h diarization) | 100 new streams/min (PAYG) | training on customer data unless opted out (paid only), BAA, or EU servers; audio deleted 24–48 h, transcripts 30 days, TTL down to 1 h | none found |
| AssemblyAI Universal-3.5 Pro | no | yes | yes | yes | add-on | **unverified** | $0.21/h | as above | as above | none found |
| ElevenLabs Scribe v2 | yes (`lit`, 5–10% WER tier) | yes | yes (word or character) | `logprob` per word | yes (up to 32) | 5 GB upload; 10 h | $0.22/h | **unverified** | history kept by default; zero-retention (`enable_logging=false`) enterprise only; training terms **unverified** | none found; tags non-speech `audio_event`s |
| OpenAI `whisper-1` | yes per Whisper language list | yes | yes (`timestamp_granularities[]`) | not documented | no | 25 MB | $0.36/h ($0.006/min) | **unverified** | not used for training unless opted in; transcription endpoint has no abuse-monitoring retention; ZDR eligible | Jam-ALT figures above are for open Whisper, not this endpoint |
| OpenAI `gpt-transcribe` / `gpt-4o-transcribe` | **unverified** | yes | no | not documented | `gpt-4o-transcribe-diarize` only | 25 MB | from $0.27/h ($0.0045/min, `gpt-transcribe`) | **unverified** | as above | none found |
| Speechmatics (Standard / Enhanced) | yes (`lt`) | yes | yes | yes | yes | **unverified** | $0.45/h / $0.75/h; $100 sign-up credit | **unverified** | never used for training unless opt-in (33% discount); pre-recorded auto-deleted after 7 days | none found; vendor FLEURS LT WER 9.35% (Enhanced) |
| Tilde (LTASR) | yes | **unverified** | **unverified** | **unverified** | **unverified** | **unverified** | not published | **unverified** | on-premise/private cloud possible | none found; current API docs not found, sales contact needed |

## TTS / voice comparison

| Service | LT voices | EN voices | SSML / prosody | Pitch control | Price | Singing / voice conversion |
|---|---|---|---|---|---|---|
| Edge-TTS (baseline) | yes (current baseline) | yes | **unverified** | **unverified** | free, unofficial | no |
| Azure Neural TTS | `lt-LT-OnaNeural` (F), `lt-LT-LeonasNeural` (M); no styles | many | full SSML; `<prosody>` pitch, contour, range, rate, volume; `lyrical` style on some voices (not LT) | yes (absolute, relative, contour) | not rendered on pricing page (**unverified**); free tier 0.5 M characters/month | LT voices: "voice conversion not supported" |
| Google Cloud TTS | 30 Chirp 3: HD voices + `lt-LT-Standard-B` | many | Chirp 3: HD: no SSML; Standard voice: **unverified** | Chirp 3: HD: no pitch/rate parameters | **unverified** | none |
| ElevenLabs | Eleven v3 / v3 Conversational / v4 / v4 Turbo list `lt` | yes | audio tags (v3/v4); no SSML pitch documented | not documented | $0.08 per 1k characters (v3, Multilingual v2), $0.04 (Flash/Turbo) | Voice Changer (STS): 29 languages, LT not listed, 5-minute segments, singing not documented. Eleven Music: generates vocals from prompts/lyrics, API for paid plans; LT not listed |
| Deepgram Aura-2 | **unverified** | yes | **unverified** | **unverified** | $0.030 per 1k characters | none |
| OpenAI TTS | **unverified** | yes | **unverified** | **unverified** | TTS-1 $15 / 1M chars, TTS-1 HD $30 / 1M chars | none |

## Open items for the tournament harness

- Pass `language` explicitly everywhere (Jam-ALT shows Whisper picking the wrong language on separated vocals).
- Deepgram requests must carry `mip_opt_out=true`; set AssemblyAI opt-out in the dashboard (paid account) or use EU servers; set ElevenLabs logging per plan; AWS AI-services opt-out policy to be checked before use.
- Google pricing and Azure prices must be read from the live price list before budgeting (pages did not render for us).

## Sources (all opened 2026-10-18)

- Google STT V2 supported languages: https://docs.cloud.google.com/speech-to-text/v2/docs/speech-to-text-supported-languages
- Google Chirp 3: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Google STT pricing (did not render; figures **unverified**): https://cloud.google.com/speech-to-text/pricing
- Google TTS voice list: https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types
- Azure language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt
- Azure fast transcription: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/fast-transcription-create
- Azure STT data, privacy, security: https://learn.microsoft.com/en-us/legal/cognitive-services/speech-service/speech-to-text/data-privacy-security
- Azure SSML voice/prosody: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice
- Azure Speech pricing (prices did not render): https://azure.microsoft.com/en-us/pricing/details/speech/
- AWS Transcribe supported languages: https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html
- AWS Transcribe feature matrix: https://docs.aws.amazon.com/transcribe/latest/dg/feature-matrix.html
- AWS Transcribe data input and output: https://docs.aws.amazon.com/transcribe/latest/dg/input.html
- AWS Transcribe data protection: https://docs.aws.amazon.com/transcribe/latest/dg/data-protection.html
- AWS Transcribe pricing: https://aws.amazon.com/transcribe/pricing/
- Deepgram models and languages: https://developers.deepgram.com/docs/models-languages-overview
- Deepgram pre-recorded audio: https://developers.deepgram.com/docs/pre-recorded-audio
- Deepgram Model Improvement Partnership: https://developers.deepgram.com/docs/the-deepgram-model-improvement-partnership-program
- Deepgram pricing: https://deepgram.com/pricing
- AssemblyAI supported languages: https://www.assemblyai.com/docs/getting-started/supported-languages
- AssemblyAI word-level timestamps: https://www.assemblyai.com/docs/speech-to-text/pre-recorded-audio/word-level-timestamps
- AssemblyAI data retention and model training: https://www.assemblyai.com/docs/data-retention-and-model-training
- AssemblyAI pricing: https://www.assemblyai.com/pricing
- ElevenLabs speech to text: https://elevenlabs.io/docs/capabilities/speech-to-text
- ElevenLabs STT API reference: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- ElevenLabs models: https://elevenlabs.io/docs/models
- ElevenLabs text to speech: https://elevenlabs.io/docs/capabilities/text-to-speech
- ElevenLabs voice changer: https://elevenlabs.io/docs/capabilities/voice-changer
- ElevenLabs music: https://elevenlabs.io/docs/capabilities/music
- ElevenLabs API pricing: https://elevenlabs.io/pricing/api
- OpenAI speech to text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI API pricing: https://developers.openai.com/api/docs/pricing
- OpenAI your data: https://developers.openai.com/api/docs/guides/your-data
- Whisper language list: https://github.com/openai/whisper/blob/main/whisper/tokenizer.py
- Speechmatics languages: https://docs.speechmatics.com/speech-to-text/languages
- Speechmatics output formatting: https://docs.speechmatics.com/speech-to-text/formatting
- Speechmatics pricing: https://www.speechmatics.com/pricing
- Speechmatics Lithuanian (vendor claims): https://www.speechmatics.com/speech-to-text/lithuanian
- Jam-ALT paper (Whisper on lyrics, Demucs effect): https://arxiv.org/html/2311.13987v1
- Tilde: product page and older API docs seen only in search results (https://tilde.ai/speech/, https://tilde.com/node/528); the docs page returned 404 when opened, so all Tilde details are **unverified**.
