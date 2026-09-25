"""Capture local API evidence and render a captioned, silent demo video.

Requires the bundled workspace Python with Pillow, ffmpeg, and a running local API.
The video is a storyboard of observed responses, not a public endpoint recording.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submission" / "PRISM_Theme2_Local_Demo_Working.mp4"
FRAMES = ROOT / ".runtime" / "demo_frames"
FONT = Path("C:/Windows/Fonts/segoeui.ttf")
BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
SIZE = (1600, 900)
BG = "#08141e"
PANEL = "#102838"
WHITE = "#f3f8fa"
MUTED = "#b5c9d1"
CYAN = "#6fd8d5"
YELLOW = "#f4c66a"


def get_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise ValueError(f"Local API returned {response.status}")
        return json.load(response)


def preview(url: str, sample: dict[str, str]) -> dict[str, object]:
    body = json.dumps({"query": sample["query"], "siis_response": {"title": sample["title"], "content": sample["content"]}}).encode()
    request = urllib.request.Request(url + "/v1/preview", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError(f"Local preview returned {response.status}")
        data = json.load(response)
        data["http_status"] = response.status
        return data


def summary(data: dict[str, object], source: str) -> dict[str, object]:
    procedures = data["preview"]["procedures"]
    return {
        "source": source,
        "http_status": data["http_status"],
        "article_hash": data["evidence"]["article_hash"],
        "official_procedures": len(data["response"]["contexts"]),
        "official_actions": sum(len(item["actions"]) for item in data["response"]["contexts"]),
        "preview_selected": sum(item["disposition"] == "included" for item in procedures),
        "preview_excluded": [item["title"] for item in procedures if item["disposition"] != "included"],
        "catalog_ids": sorted({action["catalog_id"] for item in procedures for action in item["actions"] if action["catalog_id"]}),
        "cache_status": data["trace"]["cache_status"],
    }


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def wrap(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    result: list[str] = []
    for paragraph in value.split("\n"):
        line = ""
        for word in paragraph.split():
            proposal = f"{line} {word}".strip()
            if line and draw.textbbox((0, 0), proposal, font=face)[2] > width:
                result.append(line)
                line = word
            else:
                line = proposal
        result.append(line)
    return result


def draw_text(draw: ImageDraw.ImageDraw, value: str, x: int, y: int, width: int, size: int = 33,
              color: str = WHITE, bold: bool = False, spacing: int = 15) -> int:
    face = font(size, bold)
    for line in wrap(draw, value, face, width):
        draw.text((x, y), line, font=face, fill=color)
        y += size + spacing
    return y


def card(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, heading: str, body: str,
         accent: str = CYAN) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=PANEL, outline="#285165", width=2)
    draw.rectangle((x + 32, y + 34, x + 39, y + 75), fill=accent)
    draw_text(draw, heading, x + 60, y + 34, w - 92, 31, accent, True, 7)
    draw_text(draw, body, x + 38, y + 119, w - 76, 31, WHITE, False, 13)


def slide(number: int, title: str, subtitle: str, cards: list[tuple[str, str, str]], footer: str) -> Path:
    image = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((65, 54, 1535, 836), radius=36, outline="#285165", width=3)
    draw.text((106, 85), "PRISM  /  THEME 02", font=font(25, True), fill=CYAN)
    draw_text(draw, title, 106, 145, 1390, 60, WHITE, True, 10)
    draw_text(draw, subtitle, 106, 245, 1380, 28, MUTED, False, 8)
    count = len(cards)
    gap = 26
    width = (1388 - gap * (count - 1)) // count
    for index, (heading, body, accent) in enumerate(cards):
        card(draw, 106 + index * (width + gap), 350, width, 365, heading, body, accent)
    draw.line((106, 759, 1490, 759), fill="#285165", width=2)
    draw_text(draw, footer, 106, 780, 1270, 21, MUTED, False, 4)
    draw.text((1435, 775), f"{number:02d} / 06", font=font(20, True), fill=CYAN)
    FRAMES.mkdir(parents=True, exist_ok=True)
    path = FRAMES / f"slide-{number:02d}.png"
    image.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--release-run", required=True, help="Relative path to a completed local release report")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if base not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
        raise ValueError("Demo capture is restricted to the local API on port 8000")
    run = (ROOT / args.release_run).resolve()
    if ROOT not in run.parents or not run.is_dir():
        raise ValueError("Release report must be inside theme2")
    release = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if release["passed"] < 10 or release["failed"] != 0 or release["submission_export_lines"] != 20:
        raise ValueError("Release evidence does not support the video claims")
    test_match = re.search(r"(\d+) passed", (run / "tests.stdout.txt").read_text(encoding="utf-8"))
    if test_match is None:
        raise ValueError("Release test count is unavailable")
    test_count = int(test_match.group(1))
    loopback_path = Path((run / "loopback.stdout.txt").read_text(encoding="utf-8").split("EVIDENCE: ")[-1].strip())
    if ROOT not in loopback_path.parents:
        raise ValueError("Loopback report is outside theme2")
    loopback = json.loads((loopback_path / "metrics.json").read_text(encoding="utf-8"))["workloads"]
    samples = get_json(base + "/api/samples")
    synthetic = get_json(base + "/api/development-sample")
    mixed = summary(preview(base, samples[2]), "official sample 03")
    touch = summary(preview(base, samples[18]), "official sample 19")
    fold = summary(preview(base, synthetic), "team-authored synthetic development source")
    if mixed["official_procedures"] < mixed["preview_selected"] or not mixed["preview_excluded"]:
        raise ValueError("Mixed-source demonstration lacks distinct preview exclusion")
    if not {"DL-0125", "DL-0126"}.issubset(touch["catalog_ids"]):
        raise ValueError("Touch branch catalog IDs are absent")
    capture = {"captured_at_utc": datetime.now(UTC).isoformat(), "environment": "local FastAPI on 127.0.0.1; deterministic backend", "release_run": run.name,
               "cases": [mixed, touch, fold], "loopback": loopback,
               "limits": "No independent semantic labels, hosted-model calls, public latency, or official competition score"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT.parent / "DEMO_CAPTURE.json").write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")
    paths = [
        slide(1, "From complaint to inspectable guide", "A local walkthrough of the working API and evidence view.",
              [("Complete guide", "The official response includes every source-backed procedure under the current policy.", CYAN),
               ("Selected preview", "The console separately shows complaint relevance, conditions, source offsets, and catalog choices.", YELLOW)],
              "Local API capture; no public endpoint or device action is implied."),
        slide(2, "A mixed article stays complete", "Observed official sample 03: black-screen complaint in a multi-topic article.",
              [("Official response", f"{mixed['official_procedures']} procedures and {mixed['official_actions']} actions in the full response.", CYAN),
               ("Preview selection", f"{mixed['preview_selected']} selected; {len(mixed['preview_excluded'])} unrelated topics flagged off-topic. The source remains intact.", YELLOW)],
              f"Evidence: local /v1/preview 200; article SHA-256 {str(mixed['article_hash'])[:16]}…"),
        slide(3, "Opposite operations keep separate links", "Observed official sample 19: both Touch sensitivity branches are in the source.",
              [("Enable", "The source-backed enable operation resolves to catalog ID DL-0126.", CYAN),
               ("Disable", "The separate disable operation resolves to catalog ID DL-0125.", YELLOW)],
              "A catalog URI shows an available action; this demo did not execute a setting on a device."),
        slide(4, "Scoped facts stay explicit", "Observed team-authored synthetic foldable development case.",
              [("Inner display", "A black inner display does not establish that the cover display is also invisible.", CYAN),
               ("Unknown stays unknown", "Applicability appears in the preview; controls can change facts without changing the shared article.", YELLOW)],
              f"Evidence: local /v1/preview 200; {fold['official_procedures']} full procedures; synthetic source, not holdout."),
        slide(5, "What the local checks actually measured", "The release report and loopback benchmark are separate deterministic evidence.",
              [("Contract", f"{test_count}/{test_count} tests; 20/20 supplied-query offline contract cases; 3/3 authored unfamiliar articles.", CYAN),
               ("Local cache", f"{loopback['exact']['answer_hits']}/{loopback['exact']['attempts']} exact hits, p95 {loopback['exact']['p95_ms']} ms; {loopback['paraphrase_first']['answer_hits']}/{loopback['paraphrase_first']['attempts']} first generated-variant hits, p95 {loopback['paraphrase_first']['p95_ms']} ms.", YELLOW)],
              f"Evidence: {run.name}; timings are local loopback, not public or hosted-model latency."),
        slide(6, "Review before submission", "The implementation is runnable locally; remaining gates need external input.",
              [("Independent review", "Two reviewers, sealed unfamiliar articles and fact pairs, plus variation review are pending.", CYAN),
               ("Hosted and release", "Provider access, quota, public endpoint approval, team details, and final sign-off are pending.", YELLOW)],
              "Launch: build frontend, start uvicorn, open localhost:8000. No official score is claimed."),
    ]
    concat = FRAMES / "slides.ffconcat"
    lines = ["ffconcat version 1.0"]
    for path in paths:
        lines.extend([f"file '{path.as_posix()}'", "duration 16"])
    lines.append(f"file '{paths[-1].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-safe", "0", "-f", "concat", "-i", str(concat),
               "-t", "96", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTPUT)]
    subprocess.run(command, check=True)
    print(f"DEMO: {OUTPUT}; 96 seconds; six captioned slides; no audio")
    print(f"CAPTURE: {OUTPUT.parent / 'DEMO_CAPTURE.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
