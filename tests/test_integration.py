"""
Integration tests — run the full pipeline against a real project folder.

These are SLOW (requires GPU transcription). They are skipped by default.
To run them:

    pytest tests/test_integration.py -m integration -v

"""
import subprocess
import sys
import shutil
from pathlib import Path
import pytest

WORKSPACE = Path(__file__).parent.parent
VIDEO = WORKSPACE / "projects" / "GMT20260331-233449_Recording_1832x944" / "GMT20260331-233449_Recording_1832x944.mp4"
SCRIPT = WORKSPACE / "transcribe.py"


def make_project(tmp_path, name="test-project"):
    """Create a temp project folder with the test video inside."""
    project = tmp_path / name
    project.mkdir()
    shutil.copy(VIDEO, project / VIDEO.name)
    return project


@pytest.mark.integration
def test_pipeline_produces_transcript_and_screenshots(tmp_path):
    if not VIDEO.exists():
        pytest.skip(f"Test video not found: {VIDEO}")

    project = make_project(tmp_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(project), "--keywords", "unicorn"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\n{result.stderr}\n{result.stdout}"

    transcript = project / "transcript.md"
    assert transcript.exists(), "transcript.md was not created in project folder"

    screenshots_dir = project / "screenshots"
    assert screenshots_dir.exists(), "screenshots/ not created in project folder"

    screenshots = list(screenshots_dir.glob("*.png"))
    assert len(screenshots) > 0, "No screenshots were captured"
    assert len(screenshots) < 10, (
        f"Too many screenshots ({len(screenshots)}) — likely Whisper hallucination"
    )

    content = transcript.read_text()
    assert "unicorn" in content.lower(), "Keyword not found in transcript"
    assert "screenshots/" in content, "No screenshot references in transcript"
    assert content.startswith("# Transcript:"), "Transcript missing header"


@pytest.mark.integration
def test_pipeline_multi_keyword(tmp_path):
    if not VIDEO.exists():
        pytest.skip(f"Test video not found: {VIDEO}")

    project = make_project(tmp_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(project), "--keywords", "unicorn", "administration"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\n{result.stderr}\n{result.stdout}"

    content = (project / "transcript.md").read_text()
    assert "unicorn" in content.lower()
    assert "administration" in content.lower()


@pytest.mark.integration
def test_pipeline_with_script_file(tmp_path):
    if not VIDEO.exists():
        pytest.skip(f"Test video not found: {VIDEO}")

    project = make_project(tmp_path)
    script = project / "lab-script.md"
    script.write_text("# Lab Script\nConfigure cost management in VCF Operations Console.")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(project), "--keywords", "unicorn"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Script failed:\n{result.stderr}\n{result.stdout}"
    content = (project / "transcript.md").read_text()
    assert "lab-script.md" in content, "Script filename not referenced in transcript header"


@pytest.mark.integration
def test_pipeline_errors_on_multiple_videos(tmp_path):
    project = tmp_path / "bad-project"
    project.mkdir()
    (project / "video1.mp4").write_text("fake")
    (project / "video2.mp4").write_text("fake")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(project), "--keywords", "unicorn"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "multiple video" in result.stderr.lower() or "multiple video" in result.stdout.lower()
