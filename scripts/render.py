#!/usr/bin/env python3
"""Aiclip's first beat-aware renderer. Uses FFmpeg for all actual rendering."""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "media/input"
AUDIO = ROOT / "media/audio"
OUTPUT = ROOT / "media/output"
WORK = ROOT / "work"
CONFIG = ROOT / "config/edit.json"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True)

def probe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True)
    return max(0.1, float(out.strip()))

def beat_times(audio_path):
    try:
        import librosa
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        if len(y) < sr:
            return []
        _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
        return [float(t) for t in beats if t > 0.15]
    except Exception as exc:
        print(f"Beat analysis unavailable; using even scene timing: {exc}")
        return []

def main():
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("FFmpeg and ffprobe are required.")
    cfg = json.loads(CONFIG.read_text())
    INPUT.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(exist_ok=True)
    for p in OUTPUT.glob("*.mp4"): p.unlink()
    for p in WORK.iterdir():
        if p.is_file(): p.unlink()
        elif p.is_dir(): shutil.rmtree(p)

    url = os.getenv("INPUT_YOUTUBE_URL", "").strip() or cfg.get("youtube_url", "").strip()
    if url:
        # Only publicly accessible media; no DRM/private-access bypass.
        download_dir = WORK / "youtube"; download_dir.mkdir(exist_ok=True)
        run(["yt-dlp", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]",
             "--merge-output-format", "mp4", "-o", str(download_dir / "source.%(ext)s"), url])
        downloaded = sorted(download_dir.glob("source.*"))
        if downloaded:
            target = INPUT / ("youtube-source" + downloaded[0].suffix)
            shutil.copy2(downloaded[0], target)

    tracks = sorted([p for p in AUDIO.iterdir() if p.suffix.lower() in AUDIO_EXT])
    if not tracks:
        raise RuntimeError("Add one soundtrack to media/audio/ before rendering.")
    soundtrack = tracks[0]
    media = sorted([p for p in INPUT.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXT | VIDEO_EXT])
    if not media:
        raise RuntimeError("Add at least one image/video to media/input/ or provide a permitted YouTube URL.")

    ratio = os.getenv("INPUT_ASPECT_RATIO", cfg.get("aspect_ratio", "9:16"))
    dims = {"9:16": (1080,1920), "16:9": (1920,1080), "1:1": (1080,1080)}
    w,h = dims.get(ratio, dims["9:16"])
    quality = os.getenv("INPUT_QUALITY", "standard")
    crf = "20" if quality == "high" else "23"
    fps = int(cfg.get("fps", 30))
    audio_len = probe_duration(soundtrack)
    beats = beat_times(soundtrack) if cfg.get("beat_sync", True) else []
    cuts = [0.0]
    if beats:
        for t in beats:
            if 0.65 <= t < audio_len and t - cuts[-1] >= 1.15:
                cuts.append(t)
    else:
        step = float(cfg.get("image_seconds", 3.0))
        cuts += [t for t in (i*step for i in range(1, int(audio_len/step)+1)) if t < audio_len]
    cuts.append(audio_len)

    segments = []
    for i in range(len(cuts)-1):
        src = media[i % len(media)]
        duration = max(0.5, cuts[i+1]-cuts[i])
        out = WORK / f"segment_{i:04d}.mp4"
        if src.suffix.lower() in IMAGE_EXT:
            zoom_expr = "min(zoom+0.0008,1.12)" if i % 2 == 0 else "if(eq(on,1),1.12,max(zoom-0.0008,1.0))"
            vf = f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},zoompan=z='{zoom_expr}':d=1:s={w}x{h}:fps={fps},setsar=1,format=yuv420p"
            run(["ffmpeg","-y","-loop","1","-i",src,"-t",f"{duration:.3f}","-vf",vf,
                 "-r",str(fps),"-an","-c:v","libx264","-preset","veryfast","-crf",crf,str(out)])
        else:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1,format=yuv420p"
            run(["ffmpeg","-y","-i",src,"-t",f"{duration:.3f}","-vf",vf,"-an",
                 "-c:v","libx264","-preset","veryfast","-crf",crf,"-r",str(fps),str(out)])
        segments.append(out)

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments))
    final = OUTPUT / "aiclip-final.mp4"
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-i",soundtrack,
         "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k",
         "-t",f"{audio_len:.3f}","-movflags","+faststart",final])
    print(f"Render complete: {final}")

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr); sys.exit(1)
