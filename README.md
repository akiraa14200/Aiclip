# Aiclip — free media-to-video editor

A mobile-friendly, GitHub-powered editing pipeline for turning images, video clips, and permitted YouTube sources into beat-synchronised edits.

## Current architecture
- **FFmpeg** renders video, transitions, scaling, audio and motion effects.
- **Librosa** analyses audio tempo/onsets to suggest cut points.
- **yt-dlp** optionally downloads publicly accessible videos when you have permission to use them.
- **GitHub Actions** runs the renderer without a paid editing API.

## Repository folders
- `media/input/` — put images and video clips here.
- `media/audio/` — put the soundtrack or narration here.
- `media/output/` — rendered MP4s are uploaded as workflow artifacts (not committed back into Git by default).
- `config/edit.json` — output settings and optional source URL.

## Run
1. Add source media to the folders above, or start **Aiclip Render** from Actions and supply an optional YouTube URL.
2. Choose an aspect ratio and render quality.
3. Download the MP4 from the workflow's Artifacts section.

The first version is a deterministic beat-aware renderer, not a claim of full semantic AI scene understanding. A scene-by-scene review/planning layer can be added after the rendering pipeline is validated.

## Important limits
- GitHub Actions has usage and artifact-retention limits; it is not unlimited hosting or compute.
- Do not upload copyrighted material unless you have the rights or permission to use it. YouTube downloads must respect the source's terms and applicable law. No DRM, private-video, paywall or access-control bypass is provided.
- GitHub repositories are not ideal for large media libraries. Keep source files small or use temporary workflow uploads where practical.
