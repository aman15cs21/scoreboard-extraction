from __future__ import annotations
import argparse
from pathlib import Path
from src.scoreboard_extractor import ScoreboardExtractor

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract bowling scoreboard data from video")
    parser.add_argument("--input", "-i", default="bowling_scoreboard.mp4")
    parser.add_argument("--output", "-o", default="output")
    parser.add_argument("--sample-every", type=int, default=15, help="Analyze every Nth frame")
    parser.add_argument("--no-video", action="store_true", help="Skip annotated output video")
    parser.add_argument("--ocr-fallback", action="store_true", help="Use Tesseract when template confidence is low (slower)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    video = Path(args.input)
    if not video.is_absolute():
        video = root / video
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    extractor = ScoreboardExtractor(root)
    result = extractor.process(video, output, sample_every=args.sample_every, save_video=not args.no_video, use_ocr=args.ocr_fallback)

    print("\n=== FINAL SCOREBOARD ===")
    for row in result["final_scoreboard"]:
        print(f"{row['player']:10s} : {row['score']}")
    print(f"\nScoreboard observations: {len(result['observations'])}")
    print(f"JSON: {output / 'scoreboard_data.json'}")
    print(f"CSV : {output / 'scoreboard_data.csv'}")
    if not args.no_video:
        print(f"Video: {output / 'detected_scoreboard.mp4'}")


if __name__ == "__main__":
    main()

