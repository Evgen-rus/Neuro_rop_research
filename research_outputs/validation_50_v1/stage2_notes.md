# Stage 2: scope and limitations

Exactly the frozen 50 deals were processed through the existing practice read-only fetch, downloader and external transcription pipeline. Runtime raw contexts, SQLite, audio and subprocess logs are private and ignored by Git. No CRM writes or practice source changes were made.

The gate checks every enumerated root/source-lead call activity against its audio manifest and requires a nonempty correctly linked transcript for every measured call at least 36 seconds. The final call gate passes: 470 eligible calls, 470 linked transcripts, zero eligible gaps. Calls with unavailable audio or unknown duration are missing-data limitations; they are not customer rejection or manager failure evidence. Audio-unavailable counts include purged files with valid existing transcripts and overlap unknown-duration counts.

The private Max voice scan is bounded to raw root-deal and explicit source-lead comments, with a raw SHA and exact comment/owner linkage. It finds 30 messages in deals 7567 and 18845. Four have linked transcripts; 26 failed native ffmpeg decoding. Local file presence does not imply playable audio. These 26 messages remain unresolved technical limitations, not semantic evidence. The native Max downloader has no targeted validated replacement path; no new downloader or production patch was introduced.

Separate customer-chat history is not collected by the standard deal fetch command. Saved timeline communications, activities, worklog claims, task records and task-chat bundles are retained where available. This limitation applies to all 50 deals; it does not establish the absence of off-CRM communication.

The native transcription CLI may return exit code zero after catching an exception. The research wrapper now validates the actual linked transcript after each attempt and retains technical diagnostics only in private logs. Earlier attempt counters are not transcript-coverage evidence; `completeness.json` is authoritative.

An older cached audio manifest for 7567 lacked 11 activities present in the newly fetched raw context. A bounded native audio refresh covered them; seven additional eligible calls were transcribed. No extra deals were added.
