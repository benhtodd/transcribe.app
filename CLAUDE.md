# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run unit tests (fast, no GPU required)
pytest tests/test_functions.py -v

# Run integration tests (slow — requires GPU and the test .mp4)
pytest tests/test_integration.py -m integration -v

# Run a single test
pytest tests/test_functions.py::test_find_keyword_hits_basic -v

# Run the transcriber
python3 transcribe.py <project-folder> --keywords word1 "multi word phrase"
```

## Slash Commands

- `/transcribe <args>` — runs `python3 transcribe.py $ARGUMENTS`, streams output, confirms transcript path
- `/vid-to-hol-lab <args>` — same script, output framed as a hands-on lab document

## Architecture

Everything lives in `transcribe.py`. There are no modules, packages, or imports beyond stdlib and `faster_whisper`.

**Input:** A *project folder* (not a raw video file). The folder must contain exactly one video (`.mp4`, `.mov`, `.mkv`) and optionally one `.md` script file (any name except `transcript.md`). The script is stripped of Markdown and fed to Whisper as an `initial_prompt` to improve accuracy.

**Pipeline:**

1. `resolve_project()` — validates the folder, finds the video and optional script
2. `WhisperModel.transcribe()` — runs faster-whisper on CUDA with `word_timestamps=True`
3. `find_keyword_hits()` + `dedup_hits()` — scans word-level timestamps for keyword/phrase matches; deduplicates hits within a configurable gap (default 2s)
4. `extract_screenshot()` — calls `ffmpeg` as a subprocess to pull a single frame at `timestamp + offset` (default +0.5s)
5. Writes `transcript.md` into the project folder with inline screenshot references

**Project folders live in `projects/`:**
```
projects/
  <project-name>/
    <video>.mp4          # gitignored — source video
    transcript.md        # committed — lab manual with embedded screenshot refs
    screenshots/         # committed — PNGs named NNNN_HH-MM-SS_keyword-slug.png
```

**Key design decisions:**
- Screenshots are keyed to the segment they fall in, not appended at the end — they appear inline after the segment where the keyword was spoken
- Multi-word phrases are matched by scanning a sliding window over word tokens; punctuation is stripped before comparison
- `dedup_hits` uses per-keyword tracking so two different keywords close together don't interfere

## Tests

`tests/test_functions.py` — pure unit tests, no I/O, no GPU. Safe to run any time.

`tests/test_integration.py` — marked `@pytest.mark.integration`. Requires the `GMT20260331-233449_Recording_1832x944.mp4` file to be present in the workspace root. These copy the video into a `tmp_path`, run the full script as a subprocess, and assert on the output files.
