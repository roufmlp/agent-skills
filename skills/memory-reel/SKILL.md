---
name: memory-reel
description: Turn a folder of photos and videos into a polished, music-driven memory reel video — inventory, visual review, clip selection, colour grade, transitions, text overlays, audio ducking, scheduled unattended build. Use this skill whenever the user wants a video made from their photos/videos — a memory reel, highlight video, trip video, montage, recap, "make a video from this folder", birthday/anniversary/holiday video, or anything where a folder of mixed media becomes one edited film. Trigger even if they just say "make something nice from my pictures".
---

# memory-reel

Turn a folder of mixed photos/videos into one edited, music-driven film. The user
puts everything in one folder; this skill handles the rest: analyse → ask the right
questions → get plan approval → build unattended (immediately or scheduled).

The user is typically not a video editor. Speak plainly, never dump ffmpeg jargon
on them, and make every question concrete with recommended options.

## Phase 0 — Setup
- If a project folder convention exists (e.g. `Projects/<name>/CLAUDE.md` + `memory.md`),
  read those first and create them for new projects (context, decisions, progress).
- Request access to the media folder if not mounted. Work in a scratchpad; deliver to
  the user's outputs folder.
- Check tools: ffmpeg, ffprobe, ImageMagick `convert`, python3 + numpy. Install the
  handwritten font: `pip install --break-system-packages font-amatic-sc`.

## Phase 1 — Analyse before asking anything
Questions are only useful once you know the material. Run, in order:
1. **Inventory** (chunked script): per file — type, datetime (filename pattern
   `YYYYMMDD_HHMMSS` or EXIF/container tags), duration, resolution, EXIF orientation,
   GPS if present. Group by day. Note user-curated subfolders (a subfolder of
   hand-picked files = the user's favourites; weight selection towards them heavily).
2. **Thumbnail contact sheets**: one mid-frame thumb per file, montage into labelled
   sheets of ≤24 (6 columns), and actually look at every sheet. Identify recurring
   people, places, standout moments, the emotional high points.
3. **Voice scan** of candidate clips (see `references/pipeline.md` §Voice scan):
   flags clips with laughter/speech worth keeping audible. Report findings to the
   user — they know which sounds are precious; you only know which are loud.

## Phase 2 — The questions (AskUserQuestion, after analysis)
Ask in this order, with recommendations grounded in what you saw:
1. **Aspect ratio**: 9:16 (phone/WhatsApp/social) or 16:9 (TV/laptop). Note most
   phone footage is vertical — 16:9 will crop it.
2. **Length**: ~30s / 60–90s / 2–3 min, with clip-count implications stated.
3. **Theme**: offer 3–4 options BASED ON THE CONTENT you reviewed (e.g. "kid-focused
   playful", "city-by-city tour", "mixed-order memory reel", "one person's story").
   Describe each in one line of plain English.
4. **Audio**: ask the user to supply music, with this exact brief — number of tracks =
   number of emotional acts (typically 2); for each act give them target duration
   (act length + 10s spare), mood, and tempo (upbeat acts ~100–115 BPM, tender acts
   slower); same key family across tracks so handovers feel deliberate; any format.
   Also ask whether any in-footage live audio (music performances, singing) should
   feature at full volume as a "real moment". Fallbacks if they can't supply: audio
   extracted from the footage itself (loop + clean it), or clearly say there is no
   bundled music. NEVER fabricate ownership claims about music.
5. **Text**: propose concrete title / 1–2 mid quips / ending lines in a playful,
   personal voice (use real names if known — ask). Show exact wording for approval.
   Text goes ON footage, handwritten font, never on plain background cards, unless
   the user asks otherwise.
6. **When to run**: now, or scheduled (e.g. overnight). If scheduled, see Phase 4.

## Phase 3 — The plan (always approved before building)
Write a full build plan and show the user a readable summary: storyline beats,
exact clip list (file + start + duration + role), which clips keep their real
audio, all text wording, transition style, audio architecture (which track covers
which beat, where ducking happens, where live audio takes over). For any clip the
user flagged as sensitive, give exact seconds and wait for verification.
Iterate until approved. Save the approved plan as `BUILD-PLAN-<name>.md` in the
project folder — complete enough that a cold session could execute it without
asking anything.

## Phase 4 — Scheduling (if not building now)
A scheduled run starts cold, so persist everything first:
- Copy any user-uploaded audio out of the uploads dir into a real folder (uploads
  do not survive the session).
- The BUILD-PLAN must contain every trim, text and audio decision.
- Create a one-time scheduled task whose prompt says: read project CLAUDE.md,
  memory.md and the BUILD-PLAN, request the media folder if unmounted, execute
  exactly, verify, save outputs, update memory.md, never share/send/delete.
- Tell the user: the app must be open at fire time (else it runs on next launch);
  permission prompts pause an unattended run — suggest "Run now" once to pre-approve,
  and warn about laptop sleep settings.

## Phase 5 — The build (unattended)
Full technical recipes live in `references/pipeline.md` — read it before building.
The non-negotiables, and why:
- **Chunked, resumable scripts** with done-markers and a ~30s time guard per shell
  call: sandbox shells have a hard 45s cap and background processes die between
  calls. One monolithic command will fail and lose progress.
- **Pre-rotate photos** with `convert -auto-orient` before ffmpeg: ffmpeg ignores
  EXIF rotation and sideways photos are the most common silent failure.
- **Pacing**: ~3s per clip (2–2.5s in high-energy runs), mostly video, very few
  photos; photos appear as an animated multi-panel collage at one special moment
  rather than scattered stills.
- **Transitions**: soft and varied (fade / dissolve / fadeblack / fadewhite),
  faster cuts + subtle zoom-punch in energetic sections, dissolves for tender ones.
  Slow-mo (setpts) on emotional peaks — clean only if source fps ≥ 2× output fps.
- **Sound moments**: clip audio runs the FULL clip including transition overlaps,
  with the music ducking to ~30% on 0.5s ramps aligned to the crossfades. If a
  clip's good audio dies before the cut, trim the clip to the audio, not the other
  way round. Normalise each sound clip (loudnorm I=-18, limiter, highpass 100Hz)
  so a screaming playground never jumps out of a quiet bed.
- **Verify before delivering**: frame-sheet spot checks across the whole timeline —
  every text overlay, photo orientation, collage, the first/last seconds. Fix and
  re-join rather than hoping.
- **Deliver**: keepsake quality (crf 20) + a small share copy (720p, capped
  bitrate, "-whatsapp" suffix) to the user's outputs folder. Update project
  memory.md. Never share, send, publish or delete anything.
