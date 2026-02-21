# 3D Environment Reconstruction from Egocentric Video

This project reconstructs 3D environments from egocentric 1080p 60fps videos, creating a navigable 3D visualization with camera path tracking.

## Pipeline Overview

The project uses COLMAP for Structure-from-Motion (SfM) reconstruction and Three.js for visualization:

1. **Frame Extraction** - Extract frames from video segments
2. **Feature Detection** - COLMAP extracts and matches features
3. **3D Reconstruction** - Sparse point cloud generation
4. **Trajectory Export** - Extract camera path data
5. **Visualization** - Interactive 3D viewer with timeline

## Prerequisites

### Install COLMAP
- **macOS**: `brew install colmap`
- **Linux**: Follow instructions at https://colmap.github.io/install.html
- **Windows**: Download from https://github.com/colmap/colmap/releases

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Node.js Dependencies
```bash
npm install
```

## Quick Start

**Fastest way to test (single clip):**
```bash
# Install dependencies first
pip install -r requirements.txt
npm install

# Process one clip
python process_videos.py clip_6_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo
python export_trajectory.py
ln -sf ../colmap_workspace/point_cloud.ply public/point_cloud.ply
npm run dev
```

See [EXAMPLES.md](EXAMPLES.md) for more usage examples and [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Usage

### Step 1: Place Videos
Place your video segments in the `videos/` directory.

### Step 2: Extract Frames

**Interactive mode (choose clips):**
```bash
python process_videos.py
```

**Specific clips:**
```bash
python process_videos.py clip_6_hallway_solo.mp4 clip_7_down_stairs_solo.mp4
```

Extracts every 5th frame (12fps from 60fps video) to reduce processing time.

### Step 3: Run COLMAP Reconstruction

**Interactive mode (choose clips):**
```bash
python run_colmap.py
```

**Specific clips:**
```bash
python run_colmap.py clip_6_hallway_solo clip_7_down_stairs_solo
```

**Without GPU:**
```bash
python run_colmap.py --no-gpu
```
This will:
- Extract SIFT features from frames
- Match features between frames
- Run sparse 3D reconstruction
- Export point cloud to PLY format

**Note**: This step can take several hours depending on the number of frames.

### Step 4: Export Trajectory
```bash
python export_trajectory.py
```
Exports camera trajectory to `public/trajectory.json` for visualization.

### Step 5: Start Web Viewer
```bash
npm run dev
```
Open your browser to view the 3D reconstruction.

## Project Structure

```
.
├── videos/                    # Place video files here
├── extracted_frames/          # Generated: Extracted video frames
├── colmap_workspace/          # Generated: COLMAP reconstruction data
│   ├── images/                # Symlinked frames for COLMAP
│   ├── database.db            # COLMAP feature database
│   ├── sparse/                # Sparse reconstruction output
│   └── point_cloud.ply        # Exported point cloud
├── public/
│   ├── trajectory.json        # Camera trajectory data
│   └── point_cloud.ply        # Symlink to point cloud
├── src/
│   └── main.js                # Three.js visualization
├── index.html                 # Main HTML page
├── process_videos.py          # Frame extraction script
├── run_colmap.py              # COLMAP reconstruction script
├── export_trajectory.py       # Trajectory export script
├── requirements.txt           # Python dependencies
└── package.json               # Node.js dependencies
```

## Features

- **3D Point Cloud Visualization** - View reconstructed environment
- **Camera Path** - Green line showing camera trajectory through space
- **Position Marker** - Red sphere showing current position
- **Timeline Scrubbing** - Scroll through time to see position changes
- **Playback Controls** - Play/pause animation of camera movement
- **Interactive Controls** - Orbit, pan, and zoom the 3D view
- **Selective Processing** - Process specific clips instead of all videos at once

## Important Notes

### Moving Objects in Videos
Some videos contain a dog or other moving objects. COLMAP assumes a static scene, so:
- **Moving objects may create "ghost" points** in the reconstruction
- **COLMAP's built-in outlier rejection** helps filter these out
- **For best results**, start with the "solo" clips (no dog)
- The reconstruction will still work with dynamic content, just with some artifacts

### Recommended Testing Order
1. Start with **one short solo clip** (e.g., `clip_6_hallway_solo.mp4`)
2. Verify the pipeline works and view results
3. Scale up to multiple clips or try clips with the dog

## Customization

### Adjust Frame Extraction Rate
In `process_videos.py`, modify `skip_frames` parameter:
```python
extractor.process_all_videos(skip_frames=10)  # Extract every 10th frame (6fps)
```

### Change Visualization Settings
In `src/main.js`, adjust:
- Point cloud size: `size: 0.05`
- Camera FOV: `75`
- Grid size: `GridHelper(20, 20)`
- Path color: `color: 0x00ff00`

## Troubleshooting

### COLMAP GPU Issues
If you don't have a GPU, disable GPU acceleration:
```bash
python run_colmap.py --no-gpu
```

### Memory Issues
Reduce frame extraction rate or image resolution in `process_videos.py`:
```python
frame = cv2.resize(frame, (1280, 720))  # Uncomment this line
```

### Poor Reconstruction Quality
- Ensure videos have good lighting and texture
- Avoid fast camera movements
- Increase frame extraction rate (smaller skip_frames value)
- Process clips without moving objects first

### Artifacts or Ghost Points
- Likely caused by moving objects (dog, people, etc.)
- Try processing only the "solo" clips
- COLMAP's outlier rejection helps but isn't perfect

### Want to Reconstruct Different Clips
```bash
rm -rf colmap_workspace/  # Delete previous reconstruction
python run_colmap.py clip_name  # Reconstruct new clips
```

## Future Enhancements

- Dense reconstruction support
- Mesh generation from point cloud
- Multiple video segment stitching
- Depth estimation pipeline alternative
- NeRF/Gaussian Splatting integration

## License

MIT
