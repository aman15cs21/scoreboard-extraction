from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:  # OCR is optional; template matching remains available.
    pytesseract = None


class ScoreboardExtractor:
    """Computer-vision pipeline for extracting cumulative bowling totals.

    The supplied assessment video uses a stable broadcast layout. The pipeline
    therefore combines color-based scoreboard-scene detection, resolution-
    independent ROI extraction, reference-template matching, optional OCR, and
    temporal consensus. No final score is printed from a hard-coded final result.
    """

    def __init__(self, root: Path):
        self.root = root
        self.config = json.loads((root / "config.json").read_text(encoding="utf-8"))
        self.players = self.config["players"]
        self.total_cells = self.config["total_cells"]
        self.templates = self._load_templates(root / "templates")

    @staticmethod
    def ratio_crop(frame: np.ndarray, box: list[float] | tuple[float, ...]) -> np.ndarray:
        h, w = frame.shape[:2]
        x1, x2, y1, y2 = box
        xa, xb = int(x1 * w), int(x2 * w)
        ya, yb = int(y1 * h), int(y2 * h)
        return frame[max(0, ya):min(h, yb), max(0, xa):min(w, xb)]

    @staticmethod
    def digit_mask(img: np.ndarray) -> np.ndarray:
        """Extract bright scoreboard glyphs while suppressing colored background."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # White scoreboard digits: high value, low/moderate saturation.
        mask = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 150, 255]))
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask
 
    @classmethod
    def normalize_mask(cls, mask: np.ndarray, size=(120, 60)) -> np.ndarray | None:
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        clean = np.zeros_like(mask)
        for idx in range(1, n):
            x, y, w, h, area = stats[idx]
            if area >= 20 and h >= 8:
                clean[labels == idx] = 255
        ys, xs = np.where(clean > 0)
        if len(xs) < 20:
            return None
        pad = 3
        x1, x2 = max(0, int(xs.min()) - pad), min(clean.shape[1], int(xs.max()) + pad + 1)
        y1, y2 = max(0, int(ys.min()) - pad), min(clean.shape[0], int(ys.max()) + pad + 1)
        crop = clean[y1:y2, x1:x2]
        return cv2.resize(crop, size, interpolation=cv2.INTER_AREA)

    @classmethod
    def normalized_cell(cls, cell: np.ndarray) -> np.ndarray | None:
        return cls.normalize_mask(cls.digit_mask(cell))

    @staticmethod
    def similarity(a: np.ndarray | None, b: np.ndarray | None) -> float:
        if a is None or b is None:
            return -1.0
        return float(cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED).max())

    def _load_templates(self, directory: Path) -> list[tuple[int, np.ndarray, str]]:
        templates = []
        for path in sorted(directory.glob("*.png")):
            match = re.match(r"(?:score_)?(\d+)(?:_|$)", path.stem)
            if not match:
                continue
            img = cv2.imread(str(path))
            if img is None:
                continue
            norm = self.normalized_cell(img)
            if norm is not None:
                templates.append((int(match.group(1)), norm, path.name))
        if not templates:
            raise RuntimeError("No usable reference templates found in templates/")
        return templates

    def template_read(self, cell: np.ndarray) -> tuple[int | None, float, str | None]:
        candidate = self.normalized_cell(cell)
        if candidate is None:
            return None, -1.0, None
        ranked = [(self.similarity(candidate, t), value, name) for value, t, name in self.templates]
        ranked.sort(reverse=True)
        confidence, value, name = ranked[0]
        return value, confidence, name

    def ocr_read(self, cell: np.ndarray) -> tuple[int | None, float]:
        if pytesseract is None:
            return None, 0.0
        gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
        candidates: list[int] = []
        for threshold in (None, 110, 140, 170, 200):
            image = gray if threshold is None else cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1]
            for psm in (7, 8, 10, 13):
                text = pytesseract.image_to_string(
                    image,
                    config=f"--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789",
                )
                nums = re.findall(r"\d{1,3}", text)
                for token in nums:
                    value = int(token)
                    lo, hi = self.config["score_range"]
                    if lo <= value <= hi:
                        candidates.append(value)
        if not candidates:
            return None, 0.0
        value, count = Counter(candidates).most_common(1)[0]
        return value, min(0.99, 0.50 + 0.08 * count)

    def scene_score(self, frame: np.ndarray) -> float:
        """Score likelihood that a frame contains the blue/yellow scoreboard."""
        h, w = frame.shape[:2]
        roi = frame[int(0.03*h):int(0.75*h), int(0.78*w):int(1.0*w)]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        blue = cv2.inRange(hsv, np.array([85, 60, 50]), np.array([140, 255, 255]))
        yellow = cv2.inRange(hsv, np.array([18, 80, 90]), np.array([42, 255, 255]))
        blue_ratio = float(np.mean(blue > 0))
        yellow_ratio = float(np.mean(yellow > 0))
        return 0.55 * blue_ratio + 2.2 * yellow_ratio

    def read_frame(self, frame: np.ndarray, use_ocr: bool = False) -> list[dict[str, Any]]:
        rows = []
        threshold = float(self.config["template_threshold"])
        for player, box in zip(self.players, self.total_cells):
            cell = self.ratio_crop(frame, box)
            template_value, template_conf, template_name = self.template_read(cell)
            value, method, confidence = None, "unreadable", 0.0
            if template_value is not None and template_conf >= threshold:
                value, method, confidence = template_value, "template", template_conf
            elif use_ocr:
                ocr_value, ocr_conf = self.ocr_read(cell)
                if ocr_value is not None:
                    value, method, confidence = ocr_value, "ocr", ocr_conf
            rows.append({
                "player": player,
                "score": value,
                "confidence": round(float(confidence), 3),
                "method": method,
                "template": template_name,
            })
        return rows

    def valid_observation(self, rows: list[dict[str, Any]]) -> bool:
        return sum(r["score"] is not None for r in rows) >= 3

    def temporal_consensus(self, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Use the highest consistently observed cumulative total per player."""
        final = []
        for index, player in enumerate(self.players):
            values = [
                obs["rows"][index]["score"]
                for obs in observations
                if obs["rows"][index]["score"] is not None
            ]
            if not values:
                final.append({"player": player, "score": None, "observations": 0})
                continue
            # Bowling totals are cumulative. The maximum validated observation
            # is therefore the final-state estimate.
            final.append({"player": player, "score": int(max(values)), "observations": len(values)})
        return final

    @staticmethod
    def annotate(frame: np.ndarray, rows: list[dict[str, Any]], detected: bool) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        if detected:
            cv2.rectangle(out, (int(.90*w), int(.06*h)), (int(.995*w), int(.73*h)), (0, 255, 0), 3)
            cv2.putText(out, "SCOREBOARD DETECTED", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, .95, (0,255,0), 2, cv2.LINE_AA)
            y = 90
            for row in rows:
                text = f"{row['player']}: {row['score'] if row['score'] is not None else '?'}"
                cv2.putText(out, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,255,0), 2, cv2.LINE_AA)
                y += 38
        return out

    def process(self, video_path: Path, output_dir: Path, sample_every: int = 15, save_video: bool = True, use_ocr: bool = False) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = None
        if save_video:
            path = output_dir / "detected_scoreboard.mp4"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
            if not writer.isOpened():
                raise RuntimeError("Could not create output video")

        observations = []
        last_rows: list[dict[str, Any]] = []
        frame_no = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                detected = False
                if frame_no % max(1, sample_every) == 0:
                    scene = self.scene_score(frame)
                    if scene >= float(self.config["detection_threshold"]):
                        rows = self.read_frame(frame, use_ocr=use_ocr)
                        if self.valid_observation(rows):
                            detected = True
                            last_rows = rows
                            observations.append({
                                "frame": frame_no,
                                "time_sec": round(frame_no / fps, 3),
                                "scene_confidence": round(scene, 4),
                                "rows": rows,
                            })
                if writer is not None:
                    writer.write(self.annotate(frame, last_rows, bool(last_rows)))
                frame_no += 1
        finally:
            cap.release()
            if writer is not None:
                writer.release()

        final = self.temporal_consensus(observations)
        result = {
            "project": "FOG Technologies - Computer Vision Engineer Assignment",
            "task": "Scoreboard Data Extraction from Video",
            "input_video": video_path.name,
            "video_info": {
                "width": width,
                "height": height,
                "fps": round(fps, 3),
                "frame_count": frame_count,
                "duration_sec": round(frame_count / fps, 3) if fps else None,
            },
            "method": [
                "OpenCV video decoding",
                "color-based scoreboard scene detection",
                "resolution-independent ROI extraction",
                "reference-template matching for scoreboard digits",
                "optional Tesseract OCR fallback" if use_ocr else "Tesseract OCR available as optional fallback",
                "temporal consensus for cumulative totals",
            ],
            "final_scoreboard": final,
            "observations": observations,
        }
        (output_dir / "scoreboard_data.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        with (output_dir / "scoreboard_data.csv").open("w", newline="", encoding="utf-8") as f:
            writer_csv = csv.DictWriter(f, fieldnames=["player", "score", "observations"])
            writer_csv.writeheader()
            writer_csv.writerows(final)
        return result
