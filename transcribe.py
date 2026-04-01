#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel


def fmt_ts_file(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}-{m:02d}-{s:02d}"


def fmt_ts_display(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_screenshot(video_path, timestamp_seconds, output_path):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", str(timestamp_seconds),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )


def find_keyword_hits(all_words, keywords):
    hits = []
    for keyword in keywords:
        kw_tokens = keyword.lower().split()
        kw_len = len(kw_tokens)
        for i in range(len(all_words) - kw_len + 1):
            window = [
                re.sub(r"[^\w]", "", w.word.lower())
                for w in all_words[i : i + kw_len]
            ]
            if window == kw_tokens:
                hits.append((all_words[i].start, keyword))
    hits.sort(key=lambda x: x[0])
    return hits


def dedup_hits(hits, min_gap_seconds=2.0):
    seen = {}
    result = []
    for timestamp, keyword in hits:
        last = seen.get(keyword, -999)
        if timestamp - last >= min_gap_seconds:
            result.append((timestamp, keyword))
            seen[keyword] = timestamp
    return result


def resolve_project(folder):
    """Find the video and optional script inside a project folder."""
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise SystemExit(f"Error: not a directory: {folder}")

    videos = list(folder.glob("*.mp4")) + list(folder.glob("*.mov")) + list(folder.glob("*.mkv"))
    if not videos:
        raise SystemExit(f"Error: no video file found in {folder}")
    if len(videos) > 1:
        names = ", ".join(v.name for v in videos)
        raise SystemExit(f"Error: multiple video files found in {folder} — remove all but one: {names}")

    scripts = [f for f in folder.glob("*.md") if f.name != "transcript.md"]
    script = scripts[0] if len(scripts) == 1 else None
    if len(scripts) > 1:
        names = ", ".join(s.name for s in scripts)
        raise SystemExit(f"Error: multiple .md files found in {folder} — keep only the script: {names}")

    return videos[0], script, folder


def load_initial_prompt(script_path):
    raw = script_path.read_text(encoding="utf-8")
    plain = re.sub(r"#{1,6}\s+", "", raw)
    plain = re.sub(r"[*_`~]{1,3}", "", plain)
    plain = re.sub(r"!\[.*?\]\(.*?\)", "", plain)
    plain = re.sub(r"\[.*?\]\(.*?\)", "", plain)
    plain = re.sub(r"^\s*[-*>|]+\s*", "", plain, flags=re.MULTILINE)
    return " ".join(plain.split())


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a project folder containing a video (and optional script)"
    )
    parser.add_argument("project", help="Project folder containing the video and optional script .md")
    parser.add_argument("--keywords", nargs="+", required=True, help="Keywords to screenshot")
    parser.add_argument("--model", default="large-v3", help="Whisper model size (default: large-v3)")
    parser.add_argument("--screenshot-offset", type=float, default=0.5, help="Seconds after keyword timestamp to capture screenshot (default: 0.5)")
    args = parser.parse_args()

    video_path, script_path, project_dir = resolve_project(args.project)
    screenshots_dir = project_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    print(f"Project  : {project_dir.name}/")
    print(f"Video    : {video_path.name}")
    if script_path:
        print(f"Script   : {script_path.name}")
    else:
        print(f"Script   : (none found — transcribing without prompt)")

    initial_prompt = None
    if script_path:
        initial_prompt = load_initial_prompt(script_path)
        print(f"Prompt   : {len(initial_prompt)} chars loaded from script")

    print(f"\nLoading model: {args.model} (CUDA)")
    model = WhisperModel(args.model, device="cuda", compute_type="float16")

    print(f"Transcribing ...")
    segments_gen, info = model.transcribe(
        str(video_path),
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt,
    )

    all_segments = []
    all_words = []
    for seg in segments_gen:
        all_segments.append(seg)
        if seg.words:
            all_words.extend(seg.words)
        print(f"  [{fmt_ts_display(seg.start)}] {seg.text.strip()[:80]}")

    print(f"\nFound {len(all_segments)} segments, {len(all_words)} words.")
    print(f"Scanning for keywords: {args.keywords}")
    hits = dedup_hits(find_keyword_hits(all_words, args.keywords))
    print(f"Found {len(hits)} keyword hit(s).")

    screenshot_info = {}
    for idx, (timestamp, keyword) in enumerate(hits, 1):
        ts_file = fmt_ts_file(timestamp)
        kw_slug = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")
        filename = f"{idx:04d}_{ts_file}_{kw_slug}.png"
        rel_path = f"screenshots/{filename}"
        abs_path = screenshots_dir / filename
        print(f"  Screenshot {idx}: [{fmt_ts_display(timestamp)}] \"{keyword}\" -> {filename}")
        extract_screenshot(video_path, timestamp + args.screenshot_offset, abs_path)
        screenshot_info[idx] = {
            "timestamp": timestamp,
            "keyword": keyword,
            "rel_path": rel_path,
            "ts_display": fmt_ts_display(timestamp),
        }

    seg_hit_map = {}
    for hit_idx, hit in screenshot_info.items():
        best = 0
        for i, seg in enumerate(all_segments):
            if seg.start <= hit["timestamp"]:
                best = i
        seg_hit_map.setdefault(best, []).append(hit_idx)

    lines = [
        f"# Transcript: {video_path.name}",
        "",
        f"**Duration:** {fmt_ts_display(info.duration)}  ",
        f"**Keywords:** {', '.join(args.keywords)}  ",
        f"**Screenshots:** {len(hits)}  ",
    ]
    if script_path:
        lines.append(f"**Script:** {script_path.name}  ")
    lines += ["", "---", ""]

    for i, seg in enumerate(all_segments):
        ts = fmt_ts_display(seg.start)
        lines.append(f"**[{ts}]** {seg.text.strip()}")

        if i in seg_hit_map:
            for hit_idx in sorted(seg_hit_map[i], key=lambda h: screenshot_info[h]["timestamp"]):
                s = screenshot_info[hit_idx]
                lines.append("")
                lines.append(f"![{s['keyword']} at {s['ts_display']}]({s['rel_path']})")
                lines.append(f'> **[{s["ts_display"]}] Keyword: "{s["keyword"]}"**')
                lines.append("")

    transcript_path = project_dir / "transcript.md"
    transcript_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nDone.")
    print(f"  Transcript : {transcript_path}")
    print(f"  Screenshots: {screenshots_dir} ({len(hits)} files)")


if __name__ == "__main__":
    main()
