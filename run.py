#!/usr/bin/env python3
"""
Construction Video Spatial Memory — Main entry point.

Usage:
    # Run analysis (memory mode, all chunks):
    python run.py analyze

    # Run analysis (first 5 chunks only, for testing):
    python run.py analyze --max-chunks 5

    # Run analysis in naive mode:
    python run.py analyze --mode naive

    # Run full comparison (naive vs structured vs memory):
    python run.py compare

    # Run comparison on first 5 chunks:
    python run.py compare --max-chunks 5

    # Launch dashboard:
    python run.py dashboard

    # Extract frames from a video:
    python run.py extract path/to/video.mp4

    # Extract at custom fps:
    python run.py extract path/to/video.mp4 --fps 1
"""
import argparse
import os
import subprocess
import sys


def cmd_extract(args):
    """Extract frames from a video file."""
    video = args.video
    fps = args.fps
    frames_dir = os.path.join(os.path.dirname(__file__), "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # Clear existing frames
    for f in os.listdir(frames_dir):
        if f.startswith("frame_"):
            os.remove(os.path.join(frames_dir, f))

    cmd = [
        "ffmpeg", "-y",
        "-i", video,
        "-vf", f"fps={fps}",
        "-q:v", "3",
        os.path.join(frames_dir, "frame_%04d.jpg"),
    ]
    print(f"Extracting frames at {fps} fps...")
    subprocess.run(cmd, check=True)
    n = len([f for f in os.listdir(frames_dir) if f.startswith("frame_")])
    print(f"Extracted {n} frames to {frames_dir}")


def cmd_analyze(args):
    """Run the analysis pipeline."""
    from analyzer import run_pipeline
    run_pipeline(mode=args.mode, max_chunks=args.max_chunks)


def cmd_compare(args):
    """Run naive vs structured vs memory comparison."""
    from compare import run_comparison
    run_comparison(max_chunks=args.max_chunks)


def cmd_dashboard(args):
    """Launch the Streamlit dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", dashboard_path, "--server.headless", "true"],
    )


def main():
    parser = argparse.ArgumentParser(description="Construction Video Spatial Memory Analysis")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract
    p_extract = subparsers.add_parser("extract", help="Extract frames from video")
    p_extract.add_argument("video", help="Path to video file")
    p_extract.add_argument("--fps", type=float, default=0.5, help="Frames per second (default: 0.5)")
    p_extract.set_defaults(func=cmd_extract)

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Run VLM analysis pipeline")
    p_analyze.add_argument("--mode", choices=["naive", "structured", "memory"], default="memory")
    p_analyze.add_argument("--max-chunks", type=int, default=None)
    p_analyze.set_defaults(func=cmd_analyze)

    # compare
    p_compare = subparsers.add_parser("compare", help="Run mode comparison")
    p_compare.add_argument("--max-chunks", type=int, default=None)
    p_compare.set_defaults(func=cmd_compare)

    # dashboard
    p_dashboard = subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")
    p_dashboard.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
