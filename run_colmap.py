"""
Step 2: Run COLMAP reconstruction
Requires COLMAP to be installed: https://colmap.github.io/install.html
"""
import subprocess
import os
import re
import sys
import time
from pathlib import Path


def run_with_progress(cmd, step_name="Processing"):
    """
    Run command and parse output for progress indicators
    """
    print(f"\n{'='*60}")
    print(f"{step_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    last_status = ""
    images_registered = 0
    total_images = 0
    
    try:
        for line in process.stdout:
            # Track feature extraction progress
            if "Processed file" in line:
                match = re.search(r'\[(\d+)/(\d+)\]', line)
                if match:
                    current, total = int(match.group(1)), int(match.group(2))
                    percent = (current / total) * 100
                    print(f"\r📷 Extracting features: {current}/{total} ({percent:.1f}%)", end='', flush=True)
            
            # Track feature matching progress
            elif "Processing image" in line or "Processing block" in line:
                match = re.search(r'\[(\d+)/(\d+)\]', line)
                if match:
                    current, total = int(match.group(1)), int(match.group(2))
                    percent = (current / total) * 100
                    elapsed = time.time() - start_time
                    if current > 0:
                        estimated_total = (elapsed / current) * total
                        remaining = estimated_total - elapsed
                        print(f"\r🔗 Matching features: {current}/{total} ({percent:.1f}%) - Est. remaining: {remaining/60:.1f}min", end='', flush=True)
            
            # Track mapper progress
            elif "Registering image" in line:
                images_registered += 1
                elapsed = time.time() - start_time
                print(f"\r🗺️  Reconstructing: {images_registered} images registered - {elapsed/60:.1f}min elapsed", end='', flush=True)
            
            elif "=> Registered images:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    images_registered = int(match.group(1))
            
            # Show important status messages
            elif any(x in line for x in ["Bundle adjustment", "Retriangulation", "Extracting colors"]):
                status = line.strip()
                if status != last_status:
                    print(f"\n  ⚙️  {status}")
                    last_status = status
    
    except KeyboardInterrupt:
        process.kill()
        raise
    
    process.wait()
    elapsed = time.time() - start_time
    
    if process.returncode == 0:
        print(f"\n✅ Completed in {elapsed/60:.1f} minutes")
    else:
        print(f"\n❌ Failed with exit code {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, cmd)
    
    return process.returncode


class ColmapReconstructor:
    def __init__(self, workspace_dir="colmap_workspaces/colmap_workspace", video_name=None):
        """
        Args:
            workspace_dir: Base workspace directory
            video_name: If provided, creates a video-specific workspace (e.g., colmap_workspaces/colmap_workspace_clip_6)
        """
        if video_name:
            # Use video-specific workspace to keep videos separate
            workspace_dir = f"{workspace_dir}_{video_name}"
        
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        
        self.image_dir = self.workspace / "images"
        self.database_path = self.workspace / "database.db"
        self.sparse_dir = self.workspace / "sparse"
        self.dense_dir = self.workspace / "dense"
        
    def setup_images(self, frames_dir="extracted_frames", video_names=None):
        """
        Copy or symlink extracted frames to COLMAP workspace
        
        Args:
            frames_dir: Directory containing extracted frames
            video_names: List of video clip names to include (without extension)
                        e.g., ['clip_6_hallway_solo', 'clip_7_down_stairs_solo']
                        If None, includes all videos
        """
        self.image_dir.mkdir(exist_ok=True)
        
        # Create symlinks to save space
        frames_path = Path(frames_dir)
        processed_count = 0
        
        for video_folder in frames_path.iterdir():
            if not video_folder.is_dir():
                continue
            
            # Check if this video should be included
            if video_names is not None and video_folder.name not in video_names:
                print(f"Skipping: {video_folder.name}")
                continue
            
            print(f"Including: {video_folder.name}")
            for frame in video_folder.glob("*.jpg"):
                link_path = self.image_dir / f"{video_folder.name}_{frame.name}"
                if not link_path.exists():
                    os.symlink(frame.absolute(), link_path)
                processed_count += 1
        
        print(f"\nTotal frames linked: {processed_count}")
    
    def run_feature_extraction(self, use_gpu=True, max_features=32768):
        """
        Extract features from images
        
        Args:
            use_gpu: Use GPU for feature extraction
            max_features: Maximum number of features per image (default 32768, COLMAP default is 8192-16384)
        """
        cmd = [
            "colmap", "feature_extractor",
            "--database_path", str(self.database_path),
            "--image_path", str(self.image_dir),
            "--ImageReader.camera_model", "OPENCV",
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.max_num_features", str(max_features)
        ]
        
        # Add GPU flag only if explicitly disabled (GPU is default in newer COLMAP)
        if not use_gpu:
            cmd.extend(["--SiftExtraction.gpu_index", "-1"])
        
        run_with_progress(cmd, "Step 1: Extracting SIFT Features")
    
    def run_feature_matching(self, use_gpu=True, exhaustive=False, overlap=10, max_matches=65536):
        """
        Match features between images
        
        Args:
            use_gpu: Use GPU for matching
            exhaustive: If True, use exhaustive matcher (slower but more robust).
                       If False, use sequential matcher (faster).
            overlap: Number of overlapping images to match (for sequential matcher)
            max_matches: Maximum number of matches between image pairs (default 65536)
        """
        if exhaustive:
            print(f"Using exhaustive matcher (may take longer)...")
            cmd = [
                "colmap", "exhaustive_matcher",
                "--database_path", str(self.database_path),
                "--SiftMatching.max_num_matches", str(max_matches)
            ]
        else:
            print(f"Using sequential matcher with overlap={overlap}...")
            cmd = [
                "colmap", "sequential_matcher",
                "--database_path", str(self.database_path),
                "--SequentialMatching.overlap", str(overlap),
                "--SequentialMatching.loop_detection", "1",
                "--SiftMatching.max_num_matches", str(max_matches)
            ]
        
        # Add GPU flag only if explicitly disabled (GPU is default in newer COLMAP)
        if not use_gpu:
            cmd.extend(["--SiftMatching.gpu_index", "-1"])
        
        run_with_progress(cmd, "Step 2: Matching Features Between Images")
    
    def run_sparse_reconstruction(self, min_model_size=3):
        """
        Run sparse 3D reconstruction
        
        Args:
            min_model_size: Minimum number of images for a model (lower = more lenient)
        """
        self.sparse_dir.mkdir(exist_ok=True)
        
        cmd = [
            "colmap", "mapper",
            "--database_path", str(self.database_path),
            "--image_path", str(self.image_dir),
            "--output_path", str(self.sparse_dir),
            "--Mapper.min_model_size", str(min_model_size),
            "--Mapper.init_min_tri_angle", "2",  # Lower from default 4 (more lenient)
            "--Mapper.abs_pose_min_num_inliers", "15",  # Lower from default 30
            "--Mapper.abs_pose_min_inlier_ratio", "0.15",  # Lower from default 0.25
            "--Mapper.ba_local_max_num_iterations", "40",  # More iterations for better convergence
            "--Mapper.ba_global_max_num_iterations", "100"
        ]
        run_with_progress(cmd, "Step 3: Sparse 3D Reconstruction (Mapper)")
    
    def export_to_ply(self):
        """Export point cloud to PLY format - uses largest model automatically"""
        # Find the model with the most points
        models = []
        for model_dir in self.sparse_dir.iterdir():
            if model_dir.is_dir() and (model_dir / "points3D.bin").exists():
                models.append(model_dir)
        
        if not models:
            raise FileNotFoundError("No COLMAP models found in sparse directory")
        
        # Use the last model (typically the largest in sequential reconstruction)
        # or we could analyze to find the one with most images
        model_dir = sorted(models)[-1]
        print(f"Using model: {model_dir.name}")
        
        output_path = self.workspace / "point_cloud.ply"
        
        cmd = [
            "colmap", "model_converter",
            "--input_path", str(model_dir),
            "--output_path", str(output_path),
            "--output_type", "PLY"
        ]
        subprocess.run(cmd, check=True)
        print(f"Point cloud exported to: {output_path}")
    
    def run_full_pipeline(self, use_gpu=True, exhaustive=False, overlap=10, min_model_size=3, 
                         max_features=32768, max_matches=65536):
        """
        Run complete COLMAP pipeline
        
        Args:
            use_gpu: Use GPU acceleration
            exhaustive: Use exhaustive matcher instead of sequential (slower but better for difficult videos)
            overlap: Number of overlapping images for sequential matcher
            min_model_size: Minimum images per model (lower = more lenient)
            max_features: Maximum features per image (increase if seeing clamping warnings)
            max_matches: Maximum matches between image pairs
        """
        print("\n" + "="*60)
        print("🚀 COLMAP RECONSTRUCTION PIPELINE")
        print("="*60)
        
        self.run_feature_extraction(use_gpu=use_gpu, max_features=max_features)
        
        self.run_feature_matching(use_gpu=use_gpu, exhaustive=exhaustive, overlap=overlap, 
                                 max_matches=max_matches)
        
        self.run_sparse_reconstruction(min_model_size=min_model_size)
        
        print(f"\n{'='*60}")
        print("Step 4: Exporting Point Cloud")
        print(f"{'='*60}")
        self.export_to_ply()
        
        print("\n" + "="*60)
        print("✅ RECONSTRUCTION COMPLETE!")
        print("="*60)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # List available extracted videos
    frames_dir = Path("extracted_frames")
    if frames_dir.exists():
        available = [f.name for f in frames_dir.iterdir() if f.is_dir()]
        if available:
            print("Available extracted video clips:")
            for i, name in enumerate(sorted(available), 1):
                print(f"  {i}. {name}")
            print()
    
    # Check for command line arguments
    video_names = None
    use_gpu = True
    exhaustive = False
    overlap = 10
    min_model_size = 3
    max_features = 32768
    max_matches = 65536
    
    # Parse flags
    args = sys.argv[1:]
    flags_to_remove = []
    
    if "--no-gpu" in args:
        use_gpu = False
        flags_to_remove.append("--no-gpu")
        print("GPU disabled for COLMAP")
    
    if "--exhaustive" in args:
        exhaustive = True
        flags_to_remove.append("--exhaustive")
        print("Using exhaustive matcher (slower but more robust)")
    
    if "--overlap" in args:
        idx = args.index("--overlap")
        overlap = int(args[idx + 1])
        flags_to_remove.extend(["--overlap", args[idx + 1]])
        print(f"Sequential matcher overlap: {overlap}")
    
    if "--min-model-size" in args:
        idx = args.index("--min-model-size")
        min_model_size = int(args[idx + 1])
        flags_to_remove.extend(["--min-model-size", args[idx + 1]])
        print(f"Minimum model size: {min_model_size}")
    
    if "--max-features" in args:
        idx = args.index("--max-features")
        max_features = int(args[idx + 1])
        flags_to_remove.extend(["--max-features", args[idx + 1]])
        print(f"Maximum features per image: {max_features}")
    
    if "--max-matches" in args:
        idx = args.index("--max-matches")
        max_matches = int(args[idx + 1])
        flags_to_remove.extend(["--max-matches", args[idx + 1]])
        print(f"Maximum matches per image pair: {max_matches}")
        idx = args.index("--min-model-size")
        min_model_size = int(args[idx + 1])
        flags_to_remove.extend(["--min-model-size", args[idx + 1]])
        print(f"Minimum model size: {min_model_size}")
    
    # Remove flags from args
    for flag in flags_to_remove:
        if flag in args:
            args.remove(flag)
    
    if len(args) > 0:
        # Use specific videos
        video_names = args
        print(f"Processing specific clips: {video_names}\n")
    else:
        # Interactive selection
        print("Options:")
        print("  1. Reconstruct ALL extracted videos")
        print("  2. Reconstruct specific videos")
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            print("\nEnter video clip names (comma-separated, without .mp4):")
            print("Example: clip_6_hallway_solo, clip_7_down_stairs_solo")
            video_input = input("> ").strip()
            video_names = [v.strip() for v in video_input.split(',')]
    
    # Determine workspace directory
    # If processing single video, use video-specific workspace to keep videos separate
    workspace_name = None
    if video_names and len(video_names) == 1:
        workspace_name = video_names[0]
        print(f"Using video-specific workspace: colmap_workspace_{workspace_name}\n")
    
    reconstructor = ColmapReconstructor(video_name=workspace_name)
    reconstructor.setup_images(video_names=video_names)
    reconstructor.run_full_pipeline(
        use_gpu=use_gpu,
        exhaustive=exhaustive,
        overlap=overlap,
        min_model_size=min_model_size,
        max_features=max_features,
        max_matches=max_matches
    )
