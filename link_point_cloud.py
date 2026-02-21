"""
Helper script to create symlink for point cloud from video-specific workspace
"""
import sys
from pathlib import Path

def link_point_cloud(video_name=None):
    """
    Create symlink from video-specific workspace to public directory
    
    Args:
        video_name: Video clip name (e.g., "clip_6_hallway_solo")
    """
    public_dir = Path("public")
    public_dir.mkdir(exist_ok=True)
    
    # Determine workspace directory
    if video_name:
        workspace = Path(f"colmap_workspaces/colmap_workspace_{video_name}")
        if not workspace.exists():
            print(f"Warning: Video-specific workspace not found: {workspace}")
            print("Falling back to default workspace")
            workspace = Path("colmap_workspaces/colmap_workspace")
    else:
        workspace = Path("colmap_workspaces/colmap_workspace")
    
    point_cloud = workspace / "point_cloud.ply"
    
    if not point_cloud.exists():
        print(f"Error: Point cloud not found at {point_cloud}")
        print("\nMake sure you've run:")
        print(f"  python run_colmap.py {video_name if video_name else ''}")
        sys.exit(1)
    
    # Create symlink
    link_path = public_dir / "point_cloud.ply"
    
    # Remove existing symlink if it exists
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    
    # Create new symlink
    relative_path = Path("..") / workspace / "point_cloud.ply"
    link_path.symlink_to(relative_path)
    
    print(f"✓ Linked point cloud from {workspace} to {link_path}")
    print(f"  Point cloud size: {point_cloud.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    video_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if video_name:
        print(f"Linking point cloud for video: {video_name}")
    else:
        print("Linking point cloud from default workspace")
    
    link_point_cloud(video_name)
