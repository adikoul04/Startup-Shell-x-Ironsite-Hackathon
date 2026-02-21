"""Configuration for the visual memory pipeline."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file")

GEMINI_MODEL = "gemini-2.5-flash"

# Rate limiting: Free tier has strict limits (20 requests with rolling window)
# Use 8 seconds between requests to avoid hitting rate limits
# This means ~7.5 requests/minute, well under the 20/minute rolling window limit
REQUEST_DELAY_SECONDS = 8

# --- Video Processing ---
FRAMES_DIR = os.path.join(os.path.dirname(__file__), "frames")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# How many frames per VLM call (batch size)
FRAMES_PER_CHUNK = 4
# Seconds between extracted frames
FRAME_INTERVAL_SEC = 2

# --- Prompts ---
NAIVE_PROMPT = "What is happening in this video?"

JSON_SCHEMA = '''{
  "timestamp_range": "start_sec - end_sec",
  "hands": "description of hand activity",
  "tools": ["tool1 (location)", "tool2 (location)"],
  "materials": ["material1 (location)", "material2 (location)"],
  "environment": {
    "structure_type": "wood frame / steel / concrete / other",
    "phase": "framing / sheathing / roofing / drywall / finishing / other",
    "level": "ground / upper floor / roof",
    "surface": "description"
  },
  "hazards": {
    "items": ["hazard1", "hazard2"],
    "risk_level": "LOW / MEDIUM / HIGH / CRITICAL",
    "details": "explanation"
  },
  "activity": "one of the categories above",
  "productivity": "PRODUCTIVE / TRANSITIONAL / IDLE",
  "confidence": 0.0,
  "reasoning": "brief explanation of classification",
  "spatial_memory": [
    {"object": "name", "location": "relative position", "type": "landmark/hazard/tool/person"}
  ]
}'''


def build_structured_prompt(n_frames, interval):
    """Build the structured analysis prompt with frame count and interval."""
    return f"""You are analyzing egocentric construction footage from a worker's body camera.
Analyze these {n_frames} consecutive frames (taken {interval}s apart) and provide a structured analysis.

Follow these steps IN ORDER:

Step 1 - HANDS & BODY: What are the worker's hands doing? What are they holding, gripping, or touching? What body posture do you observe?

Step 2 - TOOLS & MATERIALS: List every tool and construction material visible. For each, note its approximate position relative to the worker (in hands, on floor nearby, on workbench, mounted on wall, etc).

Step 3 - ENVIRONMENT: Describe the immediate work area:
- What type of structure (wood frame, steel, concrete, etc)?
- What construction phase (foundation, framing, sheathing, roofing, drywall, finishing)?
- Are they indoors/outdoors/on an upper floor?
- What is the floor/surface they're standing on?

Step 4 - SPATIAL HAZARDS: Identify any safety concerns:
- Unguarded edges or floor openings
- Overhead hazards
- Trip hazards (loose materials, cords, debris)
- Ladder/scaffold safety issues
- Missing PPE (hard hat, harness, safety glasses, proper footwear)
- Proximity to power tools
Rate overall risk: LOW / MEDIUM / HIGH / CRITICAL

Step 5 - ACTIVITY: Based on steps 1-4, classify the primary activity into exactly ONE of:
[framing, sheathing, roofing, measuring, cutting, drilling/fastening, carrying/moving, climbing, planning/discussing, idle, walking, other]

Step 6 - PRODUCTIVITY: Is the worker:
- PRODUCTIVE: actively performing a construction task
- TRANSITIONAL: moving between tasks, setting up, getting materials
- IDLE: not working (break, phone, waiting)

Step 7 - SPATIAL MEMORY UPDATE: List any objects or landmarks that should be remembered for future frames, with their approximate location relative to the camera:
- Fixed landmarks (walls, columns, stairs, ladder positions)
- Hazards (edges, openings, overhead risks)
- Tool locations
- Other worker positions

Respond with ONLY valid JSON (no markdown, no backticks):
{JSON_SCHEMA}"""


def build_memory_prompt(n_frames, interval, memory_summary):
    """Build memory-augmented prompt with spatial context from previous chunks."""
    base = build_structured_prompt(n_frames, interval)
    return f"""SPATIAL MEMORY FROM PREVIOUS SEGMENTS:
The following objects and hazards have been observed earlier in this video.
The worker may have moved since these were recorded. Use this context to
understand the broader work environment.

{memory_summary}

---

Now analyze the CURRENT frames:

{base}"""
