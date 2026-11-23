# PostgreSQL song metadata migration

This is an opt-in metadata backend. Default local SQLite behavior remains unchanged.
The PostgreSQL option stores generated-file and commercial-license metadata; audio
bytes remain in the configured local directory or S3 bucket. It does not create
customer accounts or change the model-generation engines.

1. Back up the MixMaster storage root and stop source writes during migration.
2. Install dependencies: `python3 -m pip install -r backend/requirements.txt`.
3. Set `DATABASE_URL` privately (avoid embedding the password in shell history).
   Example without a password: `postgresql://postgres@localhost:5432/melodiva_db`.
   Use a local `.pgpass` or a secure environment secret for authentication.
4. Run the dry run:

```sh
python3 tools/migrate_music_to_postgres.py \
  --source-root "$HOME/MixMasterAI/Storage" \
  --dest-root "$HOME/MelodivaAI/Storage"
```

5. After confirming the counts and backup, run the same command with `--execute`.
   The tool creates the four metadata tables, checks ID conflicts, copies local
   audio with SHA-256 verification, imports matching records, and verifies again.
   It never removes source data. This script does not copy project drafts;
   the original SQLite migration tool can handle drafts separately.
6. Start Melodiva with `STORAGE_METADATA_BACKEND=postgres`,
   `DATABASE_URL`, and `STORAGE_LOCAL_ROOT=~/MelodivaAI/Storage`.
   These environment variables must be set for the server process, not just
   the migration shell.
7. Check `SELECT category, COUNT(*) FROM generated_files GROUP BY category;`
   in PostgreSQL, then test song playback and license endpoints before cutover.

Do not merge MixMaster's cleanup PR until real song playback and all relevant
generation/model and licensing paths have been verified. Keep database credentials
out of Git and rotate any credentials disclosed in chat.
