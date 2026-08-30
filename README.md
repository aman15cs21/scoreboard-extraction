<div align="center">

# 🎳 Scoreboard Vision

### Computer Vision–Based Scoreboard Data Extraction from Video

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/OCR-Tesseract-111111?style=flat-square" alt="OCR">
  <img src="https://img.shields.io/badge/Status-Working-2EA44F?style=flat-square" alt="Status">
</p>

<p>
  <b>FOG Technologies — Computer Vision Engineer Assignment</b><br>
  Video → Scoreboard Detection → Data Extraction → Structured Output
</p>

</div>

---

## ✨ What this project does

This project processes a bowling video and automatically extracts the information displayed on the on-screen scoreboard.

Instead of manually reading the scoreboard, the system analyzes video frames, identifies the scoreboard region, isolates the score cells, applies image preprocessing and computer-vision matching, and aggregates observations across frames to produce a stable final result.

### Final extraction from the supplied video

| Player | Score |
|:------:|------:|
| **JAGDISH** | **41** |
| **VISHAL** | **37** |
| **P** | **54** |
| **TARUN** | **40** |

The same extracted information is written to both **JSON** and **CSV** files, while an annotated video is generated to make the detection process easy to verify.

---

## 🎬 Pipeline

<div align="center">

```text
┌──────────────────────┐
│  bowling_scoreboard  │
│       .mp4           │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   OpenCV Video I/O   │
│   Frame Sampling     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Scoreboard Detection │
│   & ROI Alignment    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Image Preprocessing  │
│ Resize / Threshold   │
│ Contrast Enhancement │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Score Extraction     │
│ Template Matching +  │
│ OCR Fallback         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Temporal Validation  │
│ Across Video Frames  │
└──────────┬───────────┘
           │
           ▼
     ┌─────┴─────┐
     ▼           ▼
  JSON/CSV   Annotated MP4
```

</div>

> **Why frame aggregation?**  
> A single video frame can contain blur, transitions, compression artifacts, or a temporary scoreboard update. The system therefore uses observations from multiple frames before selecting the final scoreboard state.

---

## 🧠 Approach

### 1. Video processing

OpenCV reads the supplied MP4 and samples frames at a configurable interval.

```text
Video
  ↓
Frame sampling
  ↓
Candidate scoreboard frames
```

This avoids unnecessarily running the complete extraction pipeline on every frame.

### 2. Scoreboard localization

The scoreboard is isolated from the rest of the video using visual characteristics of the supplied scoreboard layout.

The implementation aligns the scoreboard region before extracting individual score cells. This is more reliable for this assessment video than performing OCR over the complete 1920×1080 frame.

### 3. Image preprocessing

The extracted regions are normalized before recognition. Depending on the frame, preprocessing includes:

- resizing
- grayscale conversion
- contrast enhancement
- thresholding
- noise reduction
- binary/normalized representations

The objective is to make the digits as consistent as possible before matching/OCR.

### 4. Score recognition

The system uses computer-vision matching against reference digit patterns extracted from the supplied video and can use Tesseract OCR as a fallback.

The score is treated as a numeric value rather than arbitrary text, which allows invalid OCR results to be rejected.

### 5. Temporal validation

Results from individual frames are aggregated instead of trusting one observation.

```text
Frame 1  →  40
Frame 2  →  40
Frame 3  →  4O   ← noisy
Frame 4  →  40
Frame 5  →  40
             ↓
       validated = 40
```

This improves stability when the scoreboard is temporarily blurred or partially occluded.

### 6. Structured output

The final validated scoreboard is saved as:

- `scoreboard_data.json`
- `scoreboard_data.csv`

An annotated video is also generated so the extraction can be visually inspected.

---

## 📁 Project structure

```text
FOG_Final/
│
├── main.py
├── config.json
├── requirements.txt
├── README.md
├── bowling_scoreboard.mp4
│
├── src/
│   ├── __init__.py
│   └── scoreboard_extractor.py
│
├── templates/
│   └── reference score templates
│
├── output/
│   ├── scoreboard_data.json
│   ├── scoreboard_data.csv
│   └── detected_scoreboard.mp4
│
├── screenshots/
│   ├── 01_input_scoreboard.jpg
│   ├── 02_code_running.png
│   ├── 03_detected_scoreboard.jpg
│   ├── 04_final_scoreboard.jpg
│   └── 05_final_output.png
│
├── DOCUMENTATION.pdf
└── demo_video.mp4
```

---

## ⚙️ Technology stack

| Component | Technology |
|---|---|
| Language | Python |
| Video processing | OpenCV |
| Image processing | OpenCV / NumPy |
| Score recognition | Computer-vision template matching |
| OCR fallback | Tesseract via `pytesseract` |
| Output | JSON + CSV |
| Demonstration | Annotated MP4 |
| Documentation | PDF |

---

## 🚀 Getting started

### Prerequisites

- Python 3.11+ recommended
- Windows / Linux / macOS
- Tesseract OCR installed and available in `PATH` if OCR fallback is required

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd FOG_Final
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate it

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the extraction

```bash
python main.py --input bowling_scoreboard.mp4 --output output --sample-every 15
```

### 6. Check the results

After execution, the output directory contains:

```text
output/
├── scoreboard_data.json
├── scoreboard_data.csv
└── detected_scoreboard.mp4
```

A successful run prints the extracted scoreboard in the terminal.

Example:

```text
=== FINAL SCOREBOARD ===
JAGDISH    : 41
VISHAL     : 37
P          : 54
TARUN      : 40

Scoreboard observations: 79
```

---

## 🖥️ Example output

### JSON

```json
{
  "JAGDISH": 41,
  "VISHAL": 37,
  "P": 54,
  "TARUN": 40
}
```

### CSV

```csv
player,score
JAGDISH,41
VISHAL,37
P,54
TARUN,40
```

> The exact JSON/CSV formatting may depend on the output writer version in the repository; the important result is the validated scoreboard data extracted from the supplied video.

---

## 🎥 Visual verification

The project generates an annotated video:

```text
output/detected_scoreboard.mp4
```

This video is intended to show the extracted scoreboard region while the source video is being processed.

For the assignment demonstration, the recommended flow is:

```text
01  Show input video
        ↓
02  Show project/code
        ↓
03  Run main.py
        ↓
04  Show detected scoreboard
        ↓
05  Open JSON/CSV final output
```

---

## 📊 Assignment deliverables

This repository is organized around the three deliverables requested in the assignment.

### 1. GitHub Repository

Contains:

- complete source code
- requirements
- configuration
- templates
- README
- sample input/output artifacts

### 2. Demo Video

`demo_video.mp4`

The demonstration shows:

- input video
- project running
- scoreboard detection/extraction
- final extracted data

### 3. Documentation

`DOCUMENTATION.pdf`

Includes screenshots and explanations for:

- input video/frame
- code execution
- detected scoreboard
- extracted output

---

## 🔍 Design decisions

### Why not OCR the complete frame?

Running OCR over the entire video frame introduces unnecessary text and visual noise. Restricting recognition to the scoreboard region reduces the search space and makes numeric extraction more reliable.

### Why process multiple frames?

Scoreboards can change during the video and individual frames may be imperfect. Aggregating observations helps avoid accepting a single noisy recognition result.

### Why keep JSON and CSV?

JSON is convenient for downstream applications and APIs, while CSV is easy to inspect, analyze, and import into spreadsheets or data-analysis tools.

### Why generate an annotated video?

A final number alone does not demonstrate where it came from. The annotated video provides visual evidence that the scoreboard region was actually processed.

---

## 🧪 Reproducibility

The project was tested using an isolated Python virtual environment.

Example setup:

```text
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py --input bowling_scoreboard.mp4 --output output --sample-every 15
```

Expected final extraction:

```text
JAGDISH    : 41
VISHAL     : 37
P          : 54
TARUN      : 40
```

---

## ⚠️ Scope & limitations

This implementation is designed for the **scoreboard format and visual presentation of the assessment video supplied by FOG Technologies**.

It is not presented as a universal scoreboard detector for arbitrary sports broadcasts. A production system intended for different cameras, layouts, resolutions, or sports would benefit from a learned scoreboard detector and a larger OCR/detection validation dataset.

This distinction is intentional: the goal of this submission is to solve the supplied assessment reliably while keeping the implementation reproducible and understandable.

---

## 🔮 Possible extensions

If this were extended beyond the assessment dataset, the next improvements would be:

- train a YOLO detector specifically for scoreboard localization
- support multiple scoreboard layouts
- add confidence scores for every extracted field
- use PaddleOCR/EasyOCR as additional recognition backends
- track scoreboard state changes over time
- expose extraction through a REST API
- add automated unit/integration tests
- support live camera/video-stream input
- add Docker-based deployment

---

## 👨‍💻 Author

**Ayush Sahu**

Computer Science & Data Science  
Interested in Computer Vision, Machine Learning & Data Engineering

<p>
  <a href="https://github.com/ayushsahu45k-a11y">
    <img src="https://img.shields.io/badge/GitHub-Ayush%20Sahu-181717?style=flat-square&logo=github" alt="GitHub">
  </a>
</p>

---

<div align="center">

### Built for the FOG Technologies Computer Vision Engineer Assignment

**Video in. Scoreboard out.**

</div>
