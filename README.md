# Construction Video Spatial Memory

VLM-powered construction footage analyzer with persistent spatial memory. Compares naive prompting vs structured spatial decomposition vs memory-augmented analysis.

## Setup

```bash
pip install google-generativeai streamlit Pillow
export GEMINI_API_KEY="your-key-here"
```

## Usage

```bash
# 1. Extract frames from your video
python run.py extract path/to/construction_video.mp4

# 2. Run analysis (memory mode — the full pipeline)
python run.py analyze --mode memory

# 3. Or run a quick test on first 5 chunks
python run.py analyze --mode memory --max-chunks 5

# 4. Run full comparison (naive vs structured vs memory)
python run.py compare --max-chunks 10

# 5. Launch dashboard to view results
python run.py dashboard
```

## Architecture

```
video.mp4
    │
    ▼ (ffmpeg, 0.5fps)
frames/frame_0001.jpg ... frame_NNNN.jpg
    │
    ▼ (chunk into groups of 4)
┌─────────────────────────────────────┐
│  analyzer.py                        │
│                                     │
│  For each chunk:                    │
│  1. Load 4 frames as PIL images     │
│  2. Build prompt (naive/structured) │
│  3. Inject spatial memory context   │
│  4. Send to Gemini                  │
│  5. Parse structured JSON response  │
│  6. Update spatial memory           │
│  7. Append to timeline              │
│  8. Cache result                    │
└─────────────┬───────────────────────┘
              │
              ▼
output/timeline_memory.json
output/comparison.json
              │
              ▼
dashboard.py (Streamlit)
```

## Modes

- **naive**: "What is happening?" — baseline
- **structured**: Spatial decomposition prompt (hands → tools → environment → hazards → activity)
- **memory**: Structured + persistent spatial memory across chunks. Each chunk reports spatial landmarks, and subsequent chunks receive accumulated memory as context.

## Key Insight

The structured spatial decomposition prompt forces the VLM to reason about spatial relationships (hands → tools → environment) BEFORE classifying activity, dramatically improving accuracy. The memory layer adds temporal persistence — the system remembers hazards and landmarks even when the camera turns away.
