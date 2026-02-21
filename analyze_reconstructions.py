import struct
from pathlib import Path
import sys

def read_images_binary(path):
    images = {}
    with open(path, 'rb') as f:
        num_images = struct.unpack('<Q', f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack('<I', f.read(4))[0]
            qw, qx, qy, qz = struct.unpack('<dddd', f.read(32))
            tx, ty, tz = struct.unpack('<ddd', f.read(24))
            camera_id = struct.unpack('<I', f.read(4))[0]
            name = b''
            while True:
                char = f.read(1)
                if char == b'\x00':
                    break
                name += char
            name = name.decode('utf-8')
            num_points2D = struct.unpack('<Q', f.read(8))[0]
            f.read(num_points2D * 24)  # Skip point2D data
            images[image_id] = name
    return images

def read_points3D_binary(path):
    points3D = {}
    with open(path, 'rb') as f:
        num_points = struct.unpack('<Q', f.read(8))[0]
        for _ in range(num_points):
            point3D_id = struct.unpack('<Q', f.read(8))[0]
            xyz = struct.unpack('<ddd', f.read(24))
            rgb = struct.unpack('<BBB', f.read(3))
            error = struct.unpack('<d', f.read(8))[0]
            track_length = struct.unpack('<Q', f.read(8))[0]
            f.read(track_length * 8)  # Skip track data
            points3D[point3D_id] = xyz
    return points3D

workspace = sys.argv[1] if len(sys.argv) > 1 else "colmap_workspaces/colmap_workspace_clip_10_up_stairs_solo"
sparse_dir = Path(workspace) / "sparse"

print(f"Analyzing reconstructions in {workspace}\n")
print("=" * 70)

total_images = 0
all_reconstructions = []

for i in range(10):  # Check up to 10 reconstructions
    recon_dir = sparse_dir / str(i)
    images_bin = recon_dir / "images.bin"
    points_bin = recon_dir / "points3D.bin"
    
    if not images_bin.exists():
        break
    
    images = read_images_binary(str(images_bin))
    points = read_points3D_binary(str(points_bin)) if points_bin.exists() else {}
    
    if images:
        names = sorted(images.values())
        first_frame = int(names[0].split('_')[-1].split('.')[0])
        last_frame = int(names[-1].split('_')[-1].split('.')[0])
        
        all_reconstructions.append({
            'id': i,
            'num_images': len(images),
            'num_points': len(points),
            'first_frame': first_frame,
            'last_frame': last_frame,
            'frame_range': f"{first_frame}-{last_frame}"
        })
        
        total_images += len(images)
        
        print(f"Reconstruction {i}:")
        print(f"  Images: {len(images)}")
        print(f"  Points: {len(points)}")
        print(f"  Frame range: {first_frame} - {last_frame} ({last_frame - first_frame + 1} frames)")
        print(f"  First: {names[0]}")
        print(f"  Last: {names[-1]}")
        print()

print("=" * 70)
print(f"Total reconstructions: {len(all_reconstructions)}")
print(f"Total images reconstructed: {total_images}")
print()

# Check for gaps or overlaps
all_reconstructions.sort(key=lambda x: x['first_frame'])
print("Frame coverage:")
for i, recon in enumerate(all_reconstructions):
    print(f"  Recon {recon['id']}: frames {recon['frame_range']}")
    if i > 0:
        prev_last = all_reconstructions[i-1]['last_frame']
        curr_first = recon['first_frame']
        if curr_first > prev_last + 1:
            print(f"    ⚠️  GAP: {prev_last + 1} to {curr_first - 1} ({curr_first - prev_last - 1} frames missing)")
        elif curr_first <= prev_last:
            print(f"    ⚠️  OVERLAP: {curr_first} to {prev_last}")
