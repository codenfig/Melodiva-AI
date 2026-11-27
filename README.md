# Melodiva AI

Melodiva AI is the **standalone music generation** application migrated from [codenfig/mix-master](https://github.com/codenfig/mix-master). This branch contains the original working generation implementation, split into its own React web app and FastAPI backend. MixMaster's audio mixing, mastering, stem splitting, and vocal processing remain separate.

## Features

- Full-song projects, lyrics and arrangement previews; optional vocal, instrumental and mixed-song engines
- Background generation jobs, progress and cancellation
- Offline deterministic Text to Song instrumental composer (not an AI model)
- Local Ollama lyrics generation, review and refinement
- Audio-conditioned song extension (requires separately configured engine)
- Song library, playback/download, titles/artwork, metadata and local/S3 storage
- Song-level commercial-license request, rights approval and optional Stripe checkout (not production ready without configuration, rights and security review)
- ACE-Step 1.5 full-song and instrumental generation, with language, tempo, key/scale, time signature, seed, and inference controls; MusicGen local model adapters and diagnostics

**Important:** Model weights, GPU software, external model servers, credentials, and existing user-generated files are **not** stored in Git. Model-based generation is unavailable until you configure compatible engines. The current backend uses in-process jobs that are not restart-durable, and user authentication is not yet implemented; **do not expose this app publicly without deploying appropriate access controls and production hardening.**

## Start the backend

Requires Python 3.11+, FFmpeg (for extension workflows) and an environment that can install dependencies.

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn server:app --reload --host 127.0.0.1 --port 8002
```

API documentation: http://127.0.0.1:8002/docs ; health: http://127.0.0.1:8002/health .

## Start the frontend

```bash
cd web
npm ci
npm run dev
```

Open http://localhost:5174/#/full-song . Vite proxies `/api` and `/health` to port 8002.

## Configure model-based generation

Copy the settings in `backend/storage.env.example` into your own **untracked** deployment environment. Do not commit secrets.

- `FULL_SONG_ENGINE_EXECUTABLE`: path to executable accepting `project.json` and `output.wav` for instrumentals.
- `FULL_SONG_VOCAL_EXECUTABLE`: same contract for vocal/full-song generation.
- `FULL_SONG_EXTENSION_EXECUTABLE`: audio-conditioned extension engine accepting `request.json` and `continuation.wav`.
- `MELODIVA_ENABLE_ACESTEP=1` permits the local ACE-Step 1.5 adapter for **mixed full songs and instrumentals** on its own service; models must be installed separately. This does not produce isolated vocal stems. An explicitly configured engine takes precedence.
- Install ACE-Step separately from https://github.com/ace-step/ACE-Step-1.5 (`uv sync` then `uv run acestep-api`; default service `http://127.0.0.1:8001`). Keep the service on loopback unless secured.
- The Full Song API accepts optional ACE-Step generation controls: `vocal_language` (e.g. `sw`), `key_scale`, `time_signature`, `model`, `seed`, `inference_steps`, `guidance_scale`, `thinking`, and `use_format`. The adapter maps an instrumental output to ACE-Step's `[inst]` token. These controls are ignored by other configured generation engines unless they support them.
- `ACESTEP_BASE_URL` and `ACESTEP_API_KEY` configure the ACE-Step server. The adapter enforces authentication for remote hosts.
- `MELODIVA_MUSICGEN_MODEL_DIR` and `MELODIVA_MUSICGEN_DEVICE` configure the optional offline MusicGen adapter (requires separately installed PyTorch/Transformers).
- `MELODIVA_LYRICS_MODEL` configures the model in a separately installed Ollama server. `OLLAMA_URL` configures its address.

When no matching model is configured, the API responds with `503` rather than pretending to generate a song. Text to Song can create rule-based instrumentals without these models.

## Separate storage and preserve records

Melodiva uses a different **default storage root**, `~/MelodivaAI/Storage`, from MixMaster's `~/MixMasterAI/Storage`. Set `STORAGE_LOCAL_ROOT` and, optionally, `STORAGE_METADATA_DB` explicitly. Song project drafts default to `~/MelodivaAI/Storage/full_song_projects` via `FULL_SONG_PROJECT_ROOT`.

**Do not delete source storage or Git history.** Existing files, SQLite metadata, artwork, license requests and Stripe payment records are outside Git and **are not automatically migrated by code commits**.

For local storage, take a consistent backup/snapshot of both source and destination and use `tools/migrate_music_data.py`. Dry-run is the default; `--execute` copies only `full_song` and `text_to_song` records and their file objects, related license requests/orders, and keeps original identifiers. It does **not** delete or modify source data. The script does not migrate S3 objects; plan a separate verified S3 copy with correct credentials and access policies.

```bash
python3 tools/migrate_music_data.py \
  --source-root "$HOME/MixMasterAI/Storage" \
  --dest-root "$HOME/MelodivaAI/Storage"

# Inspect summary and backups before doing a real copy:
python3 tools/migrate_music_data.py \
  --source-root "$HOME/MixMasterAI/Storage" \
  --dest-root "$HOME/MelodivaAI/Storage" --execute
```

Source metadata defaults to `<source-root>/metadata/files.sqlite3`. Browser-local drafts, favorites and overrides require a separate client-side export/import because the web origins differ (MixMaster `:5173`; Melodiva `:5174`). See `docs/migration-notes.md`.

## Verification

```bash
cd backend && python -m compileall -q . && python -m pytest -q tests
cd ../web && npm ci && npm run build
```

GitHub Actions runs those checks on PRs. Live GPU/model execution, S3 storage, authentication, Stripe fulfillment, end-user media and deployment must be verified separately before cutting over.

## License and legacy references

This migration preserves existing feature logic for compatibility, with updated Melodiva branding and storage defaults. It does not grant third-party model licenses or commercial rights in generated music. See the source repo's original documentation for upstream installation requirements and legal limitations.


## Managed ACE-Step: local or remote

Run `bash scripts/setup.sh` then `bash scripts/start.sh` from the repository root. Install uv and Node.js first. Auto mode selects remote on Intel macOS and local elsewhere; override with MELODIVA_ENGINE_MODE=local or remote. Remote setup skips model installation. Without remote credentials the studio starts but AI generation remains disabled.

For remote generation, deploy ACE-Step 1.5 on a supported GPU host using its upstream instructions. Expose its REST API through an authenticated HTTPS endpoint (no URL path prefix). Configure the same API key on the remote service and Melodiva. Never commit credentials.

```bash
export MELODIVA_ENGINE_MODE=remote
export ACESTEP_BASE_URL=https://your-gpu-host.example
read -rs ACESTEP_API_KEY
export ACESTEP_API_KEY
bash scripts/start.sh
```

Check http://127.0.0.1:8002/api/full-song/engine and refresh the studio engine status. A reachable health endpoint is not proof of successful inference; test a real song before deployment. GPU hosting and model downloads are separate costs. Stop the launcher with Ctrl+C and stop rented GPU instances separately when finished.


### Google Colab GPU lab

[Open the Melodiva ACE-Step notebook in Colab](https://colab.research.google.com/github/codenfig/Melodiva-AI/blob/main/notebooks/Melodiva_ACE_Step_Colab.ipynb). Select a GPU runtime, execute the setup and inference cells, download the WAV, then stop the runtime. This is interactive testing only; it does not expose a public API or enable the local Studio generation button. For persistent remote generation use the authenticated HTTPS deployment described above.
