"""Check the structure and evidence linkage of working submission artifacts."""

from __future__ import annotations

import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"


def office_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Damaged Office archive: {path.name}")
        return archive.read(member).decode("utf-8")


def main() -> int:
    deck = SUBMISSION / "PRISM_Theme2_Submission_Working.pptx"
    disclosure = SUBMISSION / "PRISM_Theme2_AI_Disclosure_Working.docx"
    video = SUBMISSION / "PRISM_Theme2_Local_Demo_Working.mp4"
    export = SUBMISSION / "results.jsonl"
    capture = json.loads((SUBMISSION / "DEMO_CAPTURE.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(deck) as archive:
        if archive.testzip() is not None:
            raise ValueError("Damaged presentation")
        slides = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        if len(slides) != 12:
            raise ValueError(f"Expected 12 template slides, found {len(slides)}")
        deck_xml = " ".join(archive.read(name).decode("utf-8") for name in slides)
    if "20/20 supplied-query contract cases" not in deck_xml or "independent" not in deck_xml.lower():
        raise ValueError("Deck is missing evidence or its limitation")
    disclosure_xml = office_text(disclosure, "word/document.xml")
    if "OpenAI Codex" not in disclosure_xml or "To be completed by the team" not in disclosure_xml:
        raise ValueError("Disclosure lacks AI provenance or team sign-off placeholder")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(video)],
                           capture_output=True, text=True, check=True)
    media = json.loads(probe.stdout)["format"]
    duration = float(media["duration"])
    if not 1 < duration <= 300 or int(media["size"]) < 10000:
        raise ValueError("Demo media is absent or exceeds the five-minute limit")
    report = ROOT / "reports" / capture["release_run"]
    if not report.is_dir() or json.loads((report / "summary.json").read_text(encoding="utf-8"))["failed"] != 0:
        raise ValueError("Demo capture references a failed or absent local release report")
    if len(capture["cases"]) != 3 or any(case["http_status"] != 200 for case in capture["cases"]):
        raise ValueError("Demo capture lacks the three local cases")
    if len(export.read_text(encoding="utf-8").splitlines()) != 20:
        raise ValueError("Official export does not have 20 lines")
    print(f"WORKING ARTIFACTS: 12 template slides, disclosure text present, {duration:.2f}s demo, 3 local case captures, 20 export lines")
    print("LIMIT: Office visual rendering, team sign-off, human variation review and public deployment remain pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
