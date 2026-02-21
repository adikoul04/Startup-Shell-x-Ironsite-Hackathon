"""Core VLM analysis pipeline — sends frame chunks to Gemini and parses responses."""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

# Support both old and new Gemini SDK
try:
    from google import genai
    from google.genai import types as genai_types
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai_legacy
    USE_NEW_SDK = False

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    FRAMES_DIR,
    CACHE_DIR,
    NAIVE_PROMPT,
    build_structured_prompt,
    build_memory_prompt,
    FRAMES_PER_CHUNK,
    FRAME_INTERVAL_SEC,
    REQUEST_DELAY_SECONDS,
)


def init_gemini():
    """Initialize Gemini client (supports both old and new SDK)."""
    if USE_NEW_SDK:
        return genai.Client(api_key=GEMINI_API_KEY)
    else:
        genai_legacy.configure(api_key=GEMINI_API_KEY)
        return genai_legacy.GenerativeModel(GEMINI_MODEL)


def load_frames(frames_dir: str = FRAMES_DIR) -> list[Path]:
    """Load all extracted frame paths, sorted by number."""
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    if not frames:
        raise FileNotFoundError(f"No frames found in {frames_dir}")
    return frames


def chunk_frames(frames: list[Path], chunk_size: int = FRAMES_PER_CHUNK) -> list[list[Path]]:
    """Split frames into chunks for batch VLM calls."""
    return [frames[i : i + chunk_size] for i in range(0, len(frames), chunk_size)]


def frames_to_pil(frame_paths: list[Path]) -> list[Image.Image]:
    """Load frame paths as PIL images."""
    return [Image.open(str(p)) for p in frame_paths]


def get_cache_path(chunk_idx: int, mode: str) -> Path:
    """Get cache file path for a chunk result."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return Path(CACHE_DIR) / f"chunk_{chunk_idx:04d}_{mode}.json"


def analyze_chunk(
    client,
    frame_paths: list[Path],
    chunk_idx: int,
    mode: str = "structured",
    memory: list[dict] | None = None,
    frame_interval: int = FRAME_INTERVAL_SEC,
) -> dict:
    """
    Analyze a chunk of frames with Gemini.

    Args:
        client: Gemini client instance
        frame_paths: list of frame image paths
        chunk_idx: index of this chunk (for timestamp calculation)
        mode: "naive" or "structured"
        memory: accumulated spatial memory from previous chunks
        frame_interval: seconds between frames

    Returns:
        Parsed JSON response dict
    """
    # Check cache first
    cache_path = get_cache_path(chunk_idx, mode)
    if cache_path.exists():
        with open(cache_path) as f:
            cached = json.load(f)
            # Don't use cached errors - retry those chunks
            if "error" not in cached and "parse_error" not in cached:
                return cached

    images = frames_to_pil(frame_paths)

    # Calculate timestamp range
    start_sec = chunk_idx * FRAMES_PER_CHUNK * frame_interval
    end_sec = start_sec + len(frame_paths) * frame_interval

    if mode == "naive":
        prompt = NAIVE_PROMPT
    elif mode == "structured" and memory:
        memory_lines = []
        for item in memory[-20:]:
            memory_lines.append(f"- {item['object']} ({item['type']}): {item['location']}")
        memory_summary = "\n".join(memory_lines) if memory_lines else "No prior observations."
        prompt = build_memory_prompt(len(images), frame_interval, memory_summary)
    else:
        prompt = build_structured_prompt(len(images), frame_interval)

    # Build content parts: images + prompt text
    content_parts = list(images) + [prompt]

    # Retry logic for rate limiting
    max_retries = 5
    retry_count = 0
    
    try:
        while retry_count < max_retries:
            try:
                if USE_NEW_SDK:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=content_parts,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.2,
                            max_output_tokens=4096,
                        ),
                    )
                else:
                    response = client.generate_content(
                        content_parts,
                        generation_config=genai_legacy.types.GenerationConfig(
                            temperature=0.2,
                            max_output_tokens=4096,
                        ),
                    )
                raw_text = response.text.strip()
                break  # Success, exit retry loop
                
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e.__class__.__name__):
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise  # Give up after max retries
                    
                    # Extract retry delay from error message if available
                    retry_delay = 45  # Default to 45 seconds
                    if "retry in" in str(e).lower():
                        import re
                        match = re.search(r'retry in (\d+)', str(e).lower())
                        if match:
                            retry_delay = int(match.group(1)) + 5  # Add buffer
                    
                    print(f"\n  Rate limited. Waiting {retry_delay}s before retry {retry_count}/{max_retries}...", flush=True)
                    time.sleep(retry_delay)
                else:
                    raise  # Re-raise non-rate-limit errors

        if mode == "naive":
            result = {
                "timestamp_range": f"{start_sec}s - {end_sec}s",
                "raw_response": raw_text,
                "activity": "unknown",
                "productivity": "unknown",
                "confidence": 0.0,
            }
        else:
            # Clean up response — strip markdown code fences if present
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

            try:
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to fix truncated JSON by closing brackets
                fixed = cleaned
                open_braces = fixed.count("{") - fixed.count("}")
                open_brackets = fixed.count("[") - fixed.count("]")
                # Remove trailing comma if present
                fixed = fixed.rstrip().rstrip(",")
                fixed += "]" * open_brackets + "}" * open_braces
                result = json.loads(fixed)

            result["timestamp_range"] = f"{start_sec}s - {end_sec}s"

    except json.JSONDecodeError as e:
        result = {
            "timestamp_range": f"{start_sec}s - {end_sec}s",
            "raw_response": raw_text,
            "parse_error": str(e),
            "activity": "parse_error",
            "productivity": "unknown",
            "confidence": 0.0,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        result = {
            "timestamp_range": f"{start_sec}s - {end_sec}s",
            "error": str(e),
            "activity": "error",
            "productivity": "unknown",
            "confidence": 0.0,
        }

    # Cache result (but don't cache errors - we want to retry those)
    if "error" not in result and "parse_error" not in result:
        with open(cache_path, "w") as f:
            json.dump(result, f, indent=2)
    else:
        # If error cache exists, remove it so we retry next time
        if cache_path.exists():
            cache_path.unlink()

    return result


def run_pipeline(
    mode: str = "structured",
    max_chunks: int | None = None,
    frames_dir: str = FRAMES_DIR,
) -> dict:
    """
    Run the full analysis pipeline on all frames.

    Args:
        mode: "naive", "structured", or "memory" (structured + spatial memory accumulation)
        max_chunks: limit number of chunks to process (for testing)
        frames_dir: directory containing extracted frames

    Returns:
        Full timeline dict with all chunk results
    """
    client = init_gemini()
    frames = load_frames(frames_dir)
    chunks = chunk_frames(frames)

    if max_chunks:
        chunks = chunks[:max_chunks]

    timeline = []
    spatial_memory = []

    use_memory = mode == "memory"

    print(f"Processing {len(chunks)} chunks ({len(frames)} frames) in '{mode}' mode...")

    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i + 1}/{len(chunks)} ({len(chunk)} frames)...", end=" ", flush=True)

        result = analyze_chunk(
            client=client,
            frame_paths=chunk,
            chunk_idx=i,
            mode="structured" if use_memory else mode,
            memory=spatial_memory if use_memory else None,
        )

        timeline.append(result)

        # Accumulate spatial memory
        if use_memory and "spatial_memory" in result:
            for item in result["spatial_memory"]:
                item["first_seen"] = result.get("timestamp_range", "unknown")
                spatial_memory.append(item)

        activity = result.get("activity", "?")
        productivity = result.get("productivity", "?")
        
        # Print error details if present
        if "error" in result:
            print(f"{activity} [{productivity}] - ERROR: {result['error']}")
        elif "parse_error" in result:
            print(f"{activity} [{productivity}] - PARSE ERROR: {result['parse_error']}")
        else:
            print(f"{activity} [{productivity}]")

        # Rate limit - configurable delay to avoid API quota issues
        time.sleep(REQUEST_DELAY_SECONDS)

    # Compile summary
    output = {
        "mode": mode,
        "total_frames": len(frames),
        "total_chunks": len(chunks),
        "timeline": timeline,
        "spatial_memory": spatial_memory if use_memory else [],
        "summary": compile_summary(timeline),
    }

    # Save output
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)
    output_path = os.path.join(os.path.dirname(__file__), "output", f"timeline_{mode}.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {output_path}")
    return output


def compile_summary(timeline: list[dict]) -> dict:
    """Compile aggregate stats from timeline."""
    activities = {}
    productivities = {"PRODUCTIVE": 0, "TRANSITIONAL": 0, "IDLE": 0}
    hazards_seen = []
    risk_levels = []

    for entry in timeline:
        act = entry.get("activity", "unknown")
        activities[act] = activities.get(act, 0) + 1

        prod = entry.get("productivity", "unknown")
        if prod in productivities:
            productivities[prod] += 1

        if "hazards" in entry and isinstance(entry["hazards"], dict):
            hazards_seen.extend(entry["hazards"].get("items", []))
            risk_levels.append(entry["hazards"].get("risk_level", "unknown"))

    total = len(timeline)
    productive_pct = (productivities["PRODUCTIVE"] / total * 100) if total else 0
    idle_pct = (productivities["IDLE"] / total * 100) if total else 0
    transitional_pct = (productivities["TRANSITIONAL"] / total * 100) if total else 0

    # Find idle stretches
    idle_stretches = []
    current_streak = 0
    streak_start = 0
    for i, entry in enumerate(timeline):
        if entry.get("productivity") == "IDLE":
            if current_streak == 0:
                streak_start = i
            current_streak += 1
        else:
            if current_streak >= 2:
                idle_stretches.append({
                    "start_chunk": streak_start,
                    "end_chunk": streak_start + current_streak - 1,
                    "duration_chunks": current_streak,
                    "timestamp": timeline[streak_start].get("timestamp_range", "?"),
                })
            current_streak = 0
    if current_streak >= 2:
        idle_stretches.append({
            "start_chunk": streak_start,
            "end_chunk": streak_start + current_streak - 1,
            "duration_chunks": current_streak,
        })

    return {
        "activity_distribution": activities,
        "productivity": {
            "productive_pct": round(productive_pct, 1),
            "transitional_pct": round(transitional_pct, 1),
            "idle_pct": round(idle_pct, 1),
        },
        "total_segments": total,
        "unique_hazards": list(set(hazards_seen)),
        "risk_levels_seen": list(set(risk_levels)),
        "idle_stretches": idle_stretches,
    }


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "memory"
    max_chunks = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_pipeline(mode=mode, max_chunks=max_chunks)
