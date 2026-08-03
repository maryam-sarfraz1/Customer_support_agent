"""Record a LinkedIn-ready product demo video (MP4, 1280x720).

Records the real product end-to-end, then cuts idle "waiting for the API"
stretches out of the final edit so the pacing stays tight.

Usage: python scripts/record_demo.py [--base-url http://localhost:8000]
Requires: playwright (+ chromium) and imageio-ffmpeg.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.mp4"

SLIDE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body {{ margin:0; height:100vh; display:flex; align-items:center; justify-content:center;
         background:#10131f; color:#e9e7de; font-family:'Segoe UI',sans-serif; text-align:center; }}
  h1 {{ font-family:Georgia,serif; font-size:2.6rem; font-weight:400; margin:0 0 1rem; }}
  h1 em {{ color:#e8a33d; font-style:normal; }}
  p {{ color:#9aa0b4; font-size:1.15rem; margin:.35rem 0; }}
</style></head><body><div>{body}</div></body></html>"""

INTRO = SLIDE.format(
    body="<h1>AI Customer Support <em>Agent</em></h1>"
    "<p>Answers from your docs — with citations.</p>"
    "<p>Escalates to humans when it isn't sure.</p>"
)
OUTRO = SLIDE.format(
    body="<h1>Support that <em>knows</em> when it doesn't know</h1>"
    "<p>RAG &nbsp;·&nbsp; LangGraph multi-agent workflow &nbsp;·&nbsp; FastAPI</p>"
    "<p>github.com/maryam-sarfraz1/Customer_support_agent</p>"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-email", default="admin@gmail.com")
    parser.add_argument("--admin-password", default="admin-change-me")
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="demo-video-"))
    intro_file = tmp / "intro.html"
    outro_file = tmp / "outro.html"
    intro_file.write_text(INTRO, encoding="utf-8")
    outro_file.write_text(OUTRO, encoding="utf-8")

    keeps: list[list[float]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(tmp),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()
        t0 = time.monotonic()

        def now() -> float:
            return time.monotonic() - t0

        def keep(start: float, end: float) -> None:
            # Merge with the previous window when they touch/overlap.
            if keeps and start <= keeps[-1][1] + 0.05:
                keeps[-1][1] = max(keeps[-1][1], end)
            else:
                keeps.append([start, end])

        def type_slow(selector: str, text: str) -> None:
            page.click(selector)
            page.type(selector, text, delay=45)

        # --- Intro slide ---
        s = now()
        page.goto(intro_file.as_uri())
        page.wait_for_timeout(3000)
        keep(s, now())

        # --- Chat: question typed + brief "Thinking…" ---
        s = now()
        page.goto(f"{args.base_url}/chat")
        page.wait_for_timeout(1200)
        type_slow("#box", "What is your refund policy?")
        page.wait_for_timeout(300)
        page.click("button.send")
        page.wait_for_timeout(1200)
        keep(s, now())

        # --- Cited answer arrives (idle wait will be cut) ---
        page.wait_for_selector(".cite", timeout=120_000)
        s = now() - 0.2
        page.wait_for_timeout(4000)
        keep(s, now())

        # --- Second question: ask for a human ---
        s = now()
        type_slow("#box", "I'd rather talk to a real person please")
        page.wait_for_timeout(300)
        page.click("button.send")
        page.wait_for_timeout(1200)
        keep(s, now())

        page.wait_for_selector(".notice", timeout=180_000)
        s = now() - 0.2
        page.wait_for_timeout(4000)
        keep(s, now())

        # --- Admin dashboard ---
        s = now()
        page.goto(f"{args.base_url}/admin")
        page.wait_for_timeout(800)
        type_slow("#email", args.admin_email)
        type_slow("#password", args.admin_password)
        page.click("button[type=submit]")
        page.wait_for_selector(".tile", timeout=30_000)
        page.wait_for_timeout(3200)
        page.mouse.wheel(0, 420)
        page.wait_for_timeout(2600)
        keep(s, now())

        # --- Outro slide ---
        s = now()
        page.goto(outro_file.as_uri())
        page.wait_for_timeout(3500)
        keep(s, now())

        context.close()  # flushes the video file
        video_path = Path(page.video.path())
        browser.close()

    # Cut the kept segments and concatenate into a tight H.264 MP4.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    parts = []
    filters = []
    for i, (start, end) in enumerate(keeps):
        filters.append(
            f"[0:v]trim=start={start:.2f}:end={end:.2f},setpts=PTS-STARTPTS[v{i}]"
        )
        parts.append(f"[v{i}]")
    filter_complex = (
        ";".join(filters) + f";{''.join(parts)}concat=n={len(keeps)}:v=1:a=0[out]"
    )
    subprocess.run(
        [
            ffmpeg, "-y", "-i", str(video_path),
            "-filter_complex", filter_complex, "-map", "[out]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
            "-movflags", "+faststart", str(OUT),
        ],
        check=True,
        capture_output=True,
    )
    total = sum(e - s for s, e in keeps)
    print(f"saved {OUT} ({OUT.stat().st_size / 1_048_576:.1f} MB, ~{total:.0f}s)")


if __name__ == "__main__":
    main()
