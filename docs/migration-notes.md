# MixMaster → Melodiva migration and cutover checklist

Source integration snapshot: `codenfig/mix-master` branch `feature/energy-music-mix` at `2db2f54aa99eca5d95f406404c6421d8611aa59b`.

## Feature mapping

| Generation capability | Melodiva frontend | Melodiva backend |
| --- | --- | --- |
| Full song projects, voice/genre/output/BPM, jobs, download | `web/src/pages/FullSongPage.tsx` | `backend/full_song.py`, `backend/full_song_jobs.py`, `backend/song_arrangement.py` |
| Lyrics authoring/review/Ollama | `web/src/pages/LyricsGeneratorPage.tsx` | `backend/lyrics_generator.py`, `backend/lyrics_quality.py` |
| Rule-based instrumental composition | `web/src/pages/TextToSongPage.tsx` | `backend/text_to_song.py` |
| Song extension from existing audio | FullSongPage | `backend/song_extension.py` |
| Local ACE-Step/MusicGen engine wrappers | FullSongPage | `backend/ace_step_adapter.py`, `backend/musicgen_adapter.py` and launch scripts |
| Song library, artwork and deletion | `web/src/pages/GeneratedFilesPage.tsx` + FullSongPage | `backend/generated_storage.py` (generation categories only) |
| Commercial licensing | FullSongPage + `web/src/pages/PricingPage.tsx` | `backend/commercial_licensing.py` |

## Mandatory production cutover gates

1. Verify the Python and web builds on the Melodiva migration PR.
2. Configure local/remote model engines and verify full-song generation with the real model, lyrics with Ollama, extension with a compatible audio-conditioned engine and the rule-based instrumental composer.
3. Back up/snapshot live MixMaster SQLite, S3/local objects, user files and model configuration. **Never commit credentials, database dumps or user audio.**
4. Run the local-storage migration script in dry-run mode, then execute against copied/stopped or consistent snapshots; compare file hashes and metadata for every copied record. For S3, perform an independently reviewed copy preserving object keys and user permissions.
5. Review commercial-license orders and event IDs, existing users' rights and access controls, and switch Stripe webhooks only after testing against the destination.
6. Recover browser-local saved drafts/favorites via explicit user export/import; these values reside in the browser and are not GitHub data.
7. Configure isolated `STORAGE_LOCAL_ROOT`, `STORAGE_METADATA_DB` and `FULL_SONG_PROJECT_ROOT` in Melodiva, and verify no references to the MixMaster directory remain in runtime defaults.
8. Confirm migrated library counts, playback, stream and downloads; verify delete behavior only on test data.
9. Remove generation-specific **routes, components, adapters, tests and documentation** from MixMaster in its separate cleanup PR. Keep its shared generated-file storage and non-generation records in place.
10. Rebuild MixMaster and verify Music Mix, Audio Mastering, stem splitting, vocal remover and voice studio before merging cleanup.

## Safety notes

- The copied storage service is filtered to `full_song` and `text_to_song`. MixMaster's own shared generated-file storage must be retained for `audio_mastering`, `stem_splitter`, `vocal_remover`, `voice_studio` and other processing outputs.
- Source Git history remains recoverable even after eventual source cleanup; "removed" refers to active source tree and runtime routes, not rewriting Git history.
- Model checkpoints and existing local `~/MixMasterAI/Storage` audio files are not present in Git and cannot be migrated via GitHub alone.
- This is a migration branch, not a production deployment. In-process job state is lost on restart; authentication is not yet included.
