"""Run naive vs structured vs memory comparison and output results."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from analyzer import run_pipeline, init_gemini, load_frames, chunk_frames, analyze_chunk
from config import FRAMES_PER_CHUNK, FRAME_INTERVAL_SEC


def run_comparison(max_chunks=None):
    """Run all three modes and produce a comparison report."""

    modes = ["naive", "structured", "memory"]
    results = {}

    for mode in modes:
        print(f"\n{'='*60}")
        print(f"  RUNNING: {mode.upper()} MODE")
        print(f"{'='*60}")
        results[mode] = run_pipeline(mode=mode, max_chunks=max_chunks)

    # Build comparison
    comparison = {
        "modes": {},
        "side_by_side": [],
    }

    for mode in modes:
        r = results[mode]
        comparison["modes"][mode] = r["summary"]

    # Side by side timeline
    n_chunks = min(len(r["timeline"]) for r in results.values())
    for i in range(n_chunks):
        entry = {"chunk": i}
        for mode in modes:
            t = results[mode]["timeline"][i]
            entry[mode] = {
                "activity": t.get("activity", "unknown"),
                "productivity": t.get("productivity", "unknown"),
                "confidence": t.get("confidence", 0),
                "hazards": (
                    t.get("hazards", {}).get("risk_level", "?")
                    if isinstance(t.get("hazards"), dict)
                    else "?"
                ),
            }
            if mode == "naive":
                entry[mode] = {
                    "raw_response": t.get("raw_response", "")[:200],
                }
        comparison["side_by_side"].append(entry)

    # Spatial memory unique to memory mode
    if "memory" in results:
        comparison["accumulated_spatial_memory"] = results["memory"]["spatial_memory"]

    output_path = os.path.join(os.path.dirname(__file__), "output", "comparison.json")
    with open(output_path, "w") as f:
        json.dump(comparison, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("  COMPARISON RESULTS")
    print(f"{'='*60}")

    for mode in modes:
        s = comparison["modes"][mode]
        print(f"\n--- {mode.upper()} ---")
        if "productivity" in s:
            p = s["productivity"]
            print(f"  Productive: {p.get('productive_pct', '?')}%")
            print(f"  Transitional: {p.get('transitional_pct', '?')}%")
            print(f"  Idle: {p.get('idle_pct', '?')}%")
        if "activity_distribution" in s:
            print(f"  Activities: {s['activity_distribution']}")
        if "unique_hazards" in s:
            print(f"  Hazards found: {len(s['unique_hazards'])}")
            for h in s["unique_hazards"][:5]:
                print(f"    - {h}")
        if "risk_levels_seen" in s:
            print(f"  Risk levels: {s['risk_levels_seen']}")

    print(f"\nSaved comparison to {output_path}")
    return comparison


if __name__ == "__main__":
    max_chunks = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_comparison(max_chunks=max_chunks)
