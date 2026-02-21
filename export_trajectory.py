"""
Step 3: Export camera trajectory from COLMAP output
"""
import numpy as np
import json
from pathlib import Path
import struct


def read_next_bytes(fid, num_bytes, format_char_sequence, endian_character="<"):
    """Read and unpack the next bytes from a binary file."""
    data = fid.read(num_bytes)
    return struct.unpack(endian_character + format_char_sequence, data)


def read_cameras_binary(path_to_model_file):
    """
    Read COLMAP cameras.bin file
    Returns: dict of camera_id -> camera params
    """
    cameras = {}
    with open(path_to_model_file, "rb") as fid:
        num_cameras = read_next_bytes(fid, 8, "Q")[0]
        for _ in range(num_cameras):
            camera_properties = read_next_bytes(fid, 24, "iiQQ")
            camera_id = camera_properties[0]
            model_id = camera_properties[1]
            width = camera_properties[2]
            height = camera_properties[3]
            num_params = 4  # Assuming OPENCV model
            params = read_next_bytes(fid, 8 * num_params, "d" * num_params)
            cameras[camera_id] = {
                "id": camera_id,
                "model": model_id,
                "width": width,
                "height": height,
                "params": params
            }
    return cameras


def read_images_binary(path_to_model_file):
    """
    Read COLMAP images.bin file to get camera poses
    Returns: dict of image_id -> image data
    """
    images = {}
    with open(path_to_model_file, "rb") as fid:
        num_reg_images = read_next_bytes(fid, 8, "Q")[0]
        for _ in range(num_reg_images):
            binary_image_properties = read_next_bytes(fid, 64, "idddddddi")
            image_id = binary_image_properties[0]
            qw = binary_image_properties[1]
            qx = binary_image_properties[2]
            qy = binary_image_properties[3]
            qz = binary_image_properties[4]
            tx = binary_image_properties[5]
            ty = binary_image_properties[6]
            tz = binary_image_properties[7]
            camera_id = binary_image_properties[8]
            
            # Read image name
            image_name = ""
            current_char = read_next_bytes(fid, 1, "c")[0]
            while current_char != b"\x00":
                image_name += current_char.decode("utf-8")
                current_char = read_next_bytes(fid, 1, "c")[0]
            
            # Read 2D points
            num_points2D = read_next_bytes(fid, 8, "Q")[0]
            x_y_id_s = read_next_bytes(fid, 24 * num_points2D, "ddq" * num_points2D)
            
            images[image_id] = {
                "id": image_id,
                "qvec": np.array([qw, qx, qy, qz]),
                "tvec": np.array([tx, ty, tz]),
                "camera_id": camera_id,
                "name": image_name
            }
    
    return images


def qvec_to_rotation_matrix(qvec):
    """Convert quaternion to rotation matrix"""
    qvec = qvec / np.linalg.norm(qvec)
    w, x, y, z = qvec
    
    return np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*w*z, 2*x*z + 2*w*y],
        [2*x*y + 2*w*z, 1 - 2*x*x - 2*z*z, 2*y*z - 2*w*x],
        [2*x*z - 2*w*y, 2*y*z + 2*w*x, 1 - 2*x*x - 2*y*y]
    ])


def find_largest_model(sparse_base_dir="colmap_workspace/sparse"):
    """
    Find the COLMAP model with the most registered images
    Returns the path to the largest model directory
    """
    sparse_path = Path(sparse_base_dir)
    
    if not sparse_path.exists():
        raise FileNotFoundError(f"Sparse directory not found: {sparse_base_dir}")
    
    models = []
    for model_dir in sparse_path.iterdir():
        if model_dir.is_dir() and (model_dir / "images.bin").exists():
            try:
                images = read_images_binary(model_dir / "images.bin")
                models.append((model_dir, len(images)))
            except:
                continue
    
    if not models:
        raise FileNotFoundError("No valid COLMAP models found")
    
    # Return the model with the most images
    largest_model = max(models, key=lambda x: x[1])
    print(f"Found {len(models)} model(s). Using model '{largest_model[0].name}' with {largest_model[1]} images.")
    return largest_model[0]


def find_all_models(sparse_base_dir="colmap_workspace/sparse"):
    """
    Find all COLMAP models in the sparse directory
    Returns: list of (model_dir, num_images) tuples sorted by model number
    """
    sparse_path = Path(sparse_base_dir)
    
    if not sparse_path.exists():
        raise FileNotFoundError(f"Sparse directory not found: {sparse_base_dir}")
    
    models = []
    for model_dir in sorted(sparse_path.iterdir()):
        if model_dir.is_dir() and (model_dir / "images.bin").exists():
            try:
                images = read_images_binary(model_dir / "images.bin")
                models.append((model_dir, len(images)))
            except:
                continue
    
    if not models:
        raise FileNotFoundError("No valid COLMAP models found")
    
    total_images = sum(count for _, count in models)
    print(f"Found {len(models)} reconstruction(s) with {total_images} total images:")
    for model_dir, count in models:
        print(f"  - Model {model_dir.name}: {count} images")
    
    return models


def merge_all_models(sparse_base_dir="colmap_workspace/sparse"):
    """
    Merge all COLMAP reconstructions into a single unified image dict
    
    Returns: dict of image_id -> image data from all models combined
    """
    models = find_all_models(sparse_base_dir)
    
    all_images = {}
    image_id_offset = 0
    
    for model_dir, _ in models:
        images = read_images_binary(model_dir / "images.bin")
        # Offset image IDs to avoid collisions
        for img_id, img_data in images.items():
            new_id = img_id + image_id_offset
            all_images[new_id] = img_data
        image_id_offset += max(images.keys()) + 1
    
    print(f"Merged {len(all_images)} total frames from {len(models)} reconstructions")
    return all_images


def export_trajectory_json(sparse_dir=None, 
                           output_path="public/trajectory.json",
                           fps=12,
                           video_name=None,
                           workspace_base="colmap_workspaces/colmap_workspace"):
    """
    Export camera trajectory to JSON for Three.js visualization
    
    Args:
        sparse_dir: Path to specific COLMAP model directory, or None to auto-detect largest
        output_path: Where to save the trajectory JSON
        fps: Frames per second for playback
        video_name: Optional filter - only export frames from this video (e.g., "clip_6")
                   Also used to find video-specific workspace directory
        workspace_base: Base workspace directory name
    
    Format:
    {
        "frames": [
            {
                "timestamp": 0.0,
                "position": [x, y, z],
                "rotation": [qw, qx, qy, qz],
                "image_name": "frame_000000.jpg"
            },
            ...
        ]
    }
    """
    # Determine workspace path
    if video_name:
        video_workspace = Path(f"{workspace_base}_{video_name}")
        if video_workspace.exists():
            workspace_path = video_workspace
            print(f"Using video-specific workspace: {video_workspace}")
        else:
            workspace_path = Path(workspace_base)
    else:
        workspace_path = Path(workspace_base)
    
    sparse_base = workspace_path / "sparse"
    
    # Read COLMAP binary files from largest model
    if sparse_dir is not None:
        # Use specific model directory
        cameras = read_cameras_binary(Path(sparse_dir) / "cameras.bin")
        images = read_images_binary(Path(sparse_dir) / "images.bin")
    else:
        # Use largest model only
        sparse_path = find_largest_model(sparse_base)
        cameras = read_cameras_binary(sparse_path / "cameras.bin")
        images = read_images_binary(sparse_path / "images.bin")
    
    # Filter by video name if specified
    if video_name:
        images = {k: v for k, v in images.items() if video_name in v["name"]}
        print(f"Filtered to {len(images)} frames from video containing '{video_name}'")
    
    # Sort images by name to maintain temporal order
    sorted_images = sorted(images.values(), key=lambda x: x["name"])
    
    frames = []
    positions = []
    
    for idx, img in enumerate(sorted_images):
        # COLMAP stores camera-to-world transformation
        # We need world position of camera
        R = qvec_to_rotation_matrix(img["qvec"])
        t = img["tvec"]
        
        # Camera position in world coordinates
        camera_position = -R.T @ t
        
        # Transform from COLMAP coordinates to Three.js coordinates
        # COLMAP: X=right, Y=down, Z=forward
        # Three.js: X=right, Y=up, Z=back
        # We need to: negate Y (flip up/down) and negate Z (flip forward/back)
        camera_position_threejs = np.array([
            -camera_position[0],  # Negate X to fix mirrored turn
            -camera_position[1],  # Negate Y (up/down flip)
            camera_position[2]    # Keep Z
        ])
        
        positions.append(camera_position_threejs)
        
        # Calculate camera forward direction for visualization
        # In camera space, forward is -Z axis
        forward_cam = np.array([0, 0, -1])
        forward_world = R @ forward_cam
        forward_threejs = np.array([
            -forward_world[0],
            -forward_world[1],
            forward_world[2]
        ])
        
        frame = {
            "timestamp": idx / fps,
            "position": camera_position_threejs.tolist(),
            "rotation": img["qvec"].tolist(),
            "forward": forward_threejs.tolist(),
            "image_name": img["name"]
        }
        frames.append(frame)
    
    # Compute approximate ground plane alignment
    # Find the average vertical (Y) position to help with visualization
    positions_array = np.array(positions)
    if len(positions_array) > 0:
        centroid = positions_array.mean(axis=0)
        y_range = positions_array[:, 1].max() - positions_array[:, 1].min()
    else:
        centroid = [0, 0, 0]
        y_range = 0
    
    trajectory = {
        "frames": frames,
        "total_frames": len(frames),
        "fps": fps,
        "duration": len(frames) / fps,
        "metadata": {
            "centroid": centroid.tolist(),
            "y_range": float(y_range),
            "note": "Coordinate system: X=right, Y=up, Z=forward (Three.js convention)"
        }
    }
    
    output = Path(output_path)
    output.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output, 'w') as f:
        json.dump(trajectory, f, indent=2)
    
    print(f"Trajectory exported to {output_path}")
    print(f"Total frames: {len(frames)}")
    print(f"Duration: {trajectory['duration']:.2f}s")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export camera trajectory from COLMAP reconstruction")
    parser.add_argument("--video-name", type=str, help="Filter to specific video (e.g., 'clip_6')")
    parser.add_argument("--output", type=str, default="public/trajectory.json", help="Output file path")
    parser.add_argument("--fps", type=int, default=12, help="Frames per second for playback")
    
    args = parser.parse_args()
    
    export_trajectory_json(
        video_name=args.video_name,
        output_path=args.output,
        fps=args.fps
    )
