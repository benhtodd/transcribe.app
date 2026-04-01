# transcribe.app

Transcribes a recorded video into a Markdown lab manual. Audio is transcribed using Whisper, and screenshots are captured at every moment a keyword is spoken — embedded inline in the output document.

Designed for turning screen-recorded training videos into readable, self-contained lab guides.

---

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA support (required for Whisper transcription speed)
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your PATH

---

## Installation

**1. Clone the repo**

```bash
git clone git@github.com:benhtodd/transcribe.app.git
cd transcribe.app
```

**2. Install Python dependencies**

```bash
pip install faster-whisper
```

**3. Verify ffmpeg is installed**

```bash
ffmpeg -version
```

If it's not installed:
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

---

## Project Folder Convention

Each video you want to transcribe lives in its own folder inside `projects/`. The folder must contain:

- **Exactly one video file** (`.mp4`, `.mov`, or `.mkv`)
- **Optionally one `.md` script file** — if you have a written lab script, include it. Whisper uses it as a hint to improve transcription accuracy (names, technical terms, etc.)

```
projects/
  my-lab/
    recording.mp4
    lab-script.md     ← optional but recommended
```

Output is written into the same folder:

```
projects/
  my-lab/
    recording.mp4
    lab-script.md
    transcript.md         ← generated lab manual
    screenshots/          ← screenshots captured at keyword moments
      0001_00-01-22_keyword.png
      ...
```

---

## Usage

```bash
python3 transcribe.py projects/my-lab --keywords "keyword one" "keyword two"
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `project` | Yes | Path to the project folder |
| `--keywords` | Yes | One or more words or phrases to screenshot |
| `--model` | No | Whisper model size (default: `large-v3`) |
| `--screenshot-offset` | No | Seconds after the keyword to capture the frame (default: `0.5`) |

**Model size options** (larger = more accurate, slower):
`tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`

**Example:**

```bash
python3 transcribe.py projects/lab-3-cost-management \
  --keywords "click administration" "cost drivers" "showback dashboard" \
  --model large-v3
```

---

## Slash Commands (Claude Code)

If you use [Claude Code](https://claude.ai/code), two slash commands are included:

- `/transcribe <project-folder> --keywords ...` — transcribe a video and report the output location
- `/vid-to-hol-lab <project-folder> --keywords ...` — same, output framed as a hands-on lab document

---

## Output Format

`transcript.md` is a chronological transcript with timestamps, screenshots embedded inline where each keyword was spoken:

```markdown
**[00:01:22]** Click administration. Then click global settings.

![click administration at 00:01:22](screenshots/0001_00-01-22_click-administration.png)
> **[00:01:22] Keyword: "click administration"**
```

---

## Running Tests

```bash
# Unit tests (fast, no GPU required)
pytest tests/test_functions.py -v

# Integration tests (slow — requires GPU and a video in the project folder)
pytest tests/test_integration.py -m integration -v
```
