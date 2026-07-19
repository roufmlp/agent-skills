# memory-reel — technical pipeline (battle-tested recipes)

Target spec used throughout: W×H = 1080×1920 (9:16) or 1920×1080 (16:9), 30 fps,
h264 yuv420p, `-preset veryfast -crf 20` for masters.

## Inventory script
Python: walk folder; for jpg use exifread (`pip install --break-system-packages
exifread`) for DateTimeOriginal/Orientation/GPS; for mp4/mov use ffprobe JSON
(format.duration, creation_time, location tags, stream width/height + rotation
side_data). Save inventory.json. Filenames like `20251115_214349` are the most
reliable datetime source.

## Thumbnails + sheets (chunked)
- Photos: `convert IN -auto-orient -thumbnail 220x220 OUT.jpg`
- Videos: mid-frame `ffmpeg -ss DUR/2 -i IN -frames:v 1 -vf scale=220:220:force_original_aspect_ratio=decrease OUT.jpg`
- Sheets: `montage -label <name> ... -tile 6x -geometry 220x220+2+12 -pointsize 13 sheet.jpg`,
  ≤24 thumbs per sheet (bigger sheets get downscaled unreadably in the viewer).
- Chunk pattern (applies to every batch step):
  ```bash
  START=$(date +%s)
  for f in ...; do
    [ $(($(date +%s)-START)) -gt 30 ] && echo TIME && exit 0
    [ -f done/"$f" ] && continue
    <work> && touch done/"$f"
  done; echo ALLDONE
  ```
  Re-run the same script until ALLDONE. Never rely on nohup/background survival.

## Voice scan (find sound moments)
Extract `-ac 1 -ar 16000` wav per candidate; numpy: overall RMS dB, voice-band
ratio = power in 300–3000 Hz / total, burstiness = std/mean of 0.25 s frame RMS.
Laughter/squeals ≈ voiceband >65% AND bursty >0.5. Engine/wind ≈ voiceband <10%.
Report per-second RMS for chosen clips to find the exact loud/quiet windows.

## Segment encode (one file per clip)
Video clip:
```
ffmpeg -ss START -t DUR -i SRC -vf "scale=W:H:force_original_aspect_ratio=increase,
crop=W:H,setsar=1,fps=30,GRADE,format=yuv420p[,TEXT]" -an -c:v libx264 -preset veryfast -crf 20 out.mp4
```
GRADE (warm filmic): `curves=master='0/0.045 0.5/0.51 1/0.96',eq=saturation=1.06:contrast=1.02,colortemperature=temperature=5900`
Slow-mo: add `setpts=PTS/0.6` (or /0.5) BEFORE fps=30; only when source ≥60 fps.
Photo clip (Ken Burns) — pre-rotate first (`convert IN -auto-orient -resize "2WxH^" tmp.jpg`):
```
ffmpeg -loop 1 -framerate 30 -t DUR -i tmp.jpg -vf "scale=2W:2H:force_original_aspect_ratio=increase,
crop=2W:2H,zoompan=z='1+0.10*on/(DUR*30)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=WxH:fps=30,
setsar=1,GRADE,format=yuv420p" -an ... out.mp4
```
TEXT (handwritten Amatic SC; font path from the pip package's `files/` dir):
`drawtext=fontfile=F:text='...':fontsize=~110 title /~64 quip:fontcolor=white:x=(w-text_w)/2:y=h*0.25:shadowcolor=black@0.5:shadowx=3:shadowy=3:alpha='if(lt(t,a),0,if(lt(t,b),(t-a)/(b-a),if(lt(t,c),1,max(0,(d-t)/(d-c)))))'`
Stagger multi-line fades. Escape commas in text as `\,`.

## Photo collage (the one special photo moment)
3 vertical panels (each W/3 wide, pre-cropped with convert) over a dark blurred
base, sliding in staggered: per panel
`overlay=x='min(0,-w+(t-T)*w/0.4)':y=0` with T = 0, 0.3, 0.6. Render as its own
segment, then it joins the chain like any clip.

## Join: xfade chains + lossless concat
xfade chain (per section of ≤ ~90 s output):
```
[0:v][1:v]xfade=transition=T1:duration=X:offset=O1[v1];[v1][2:v]xfade=...[v2];...
```
offsets are cumulative: O_n = (sum of previous segment durations) − n·X.
X = 0.45 s default, 0.3 s in fast sections. Transition menu: fade, dissolve,
fadeblack (day↔night), fadewhite (into celebration/party), smoothleft/up (walks).
Zoom-punch into a cut: on the outgoing segment add
`scale='iw*(1+0.06*max(0,t-(D-0.3))/0.3)':-1,crop=W:H` before joining.
Sections end/start at fadeblack boundaries with baked `fade=t=out/in:d=0.4`,
then `ffmpeg -f concat -safe 0 -i list.txt -c copy` joins sections losslessly —
this keeps every encode call under the shell time cap and avoids generation loss.

## Audio build
- Each music track: `loudnorm=I=-16:TP=-1.5:LRA=11`, stereo 44.1k wav.
- Sequence tracks with `acrossfade=d=1.5:c1=tri:c2=tri`; if no user music, loop a
  clean in-footage section: trim body, `acrossfade` copies, denoise
  (`highpass=f=70,afftdn=nr=12,acompressor=threshold=-20dB:ratio=2,loudnorm`).
- Sound moments: extract each clip's own audio for its exact timeline window
  (incl. transition overlaps); `loudnorm=I=-18`, `alimiter`, `highpass=f=100`,
  boost quiet voices up to +6 dB.
- Ducking without sidechain (deterministic): per sound moment at [t1,t2],
  music volume envelope
  `volume='if(between(t,t1,t2),0.3,if(between(t,t1-0.5,t1),1-1.4*(t-(t1-0.5)),if(between(t,t2,t2+0.5),0.3+1.4*(t-t2),1)))':eval=frame`
  (ramps land on the crossfades). Real-moment audio (live music scene): duck the
  bed to 0 and play the scene's own audio full, continuing it across adjacent
  clips of the same scene rather than switching per cut.
- Mix: `amix=inputs=N:normalize=0`, master `loudnorm=I=-15:TP=-1.2`, end fade
  3–4 s. Mux: `-c:v copy -c:a aac -b:a 192k -movflags +faststart`.

## Verify, deliver
- Frame sheets: 1 frame every ~5 s + every text moment + first/last; `montage`,
  view, fix, re-join only affected sections.
- `volumedetect` sanity: mean around −15…−20 dB, max ≤ −1 dB.
- Share copy: `-vf scale=720:1280 -crf 27 -maxrate 2200k -bufsize 4400k`.
- Copy deliverables to the user's outputs folder; confirm they appear host-side
  (sync can lag ~1 min). Update project memory.md.

## Known traps
- EXIF rotation (photos sideways) — always pre-rotate.
- `montage` has no `-y` flag.
- Files in protected folders can't be deleted — overwrite with `-y` instead.
- Uploaded files live in a session-scoped uploads dir — copy them to a real
  folder before any scheduled/future-session work.
- A user-curated subfolder beats any algorithm — weight it heavily in selection.
