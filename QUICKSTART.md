# Quick Start Guide

## Full Pipeline for a Single Video

Process any video from start to finish (replace `clip_6_hallway_solo` with your video name):

```bash
python process_videos.py clip_6_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo
python export_trajectory.py --video-name clip_6_hallway_solo
python link_point_cloud.py clip_6_hallway_solo
npm run dev
```

**Quick video switching:**
```bash
# Switch to a different video that's already processed
python export_trajectory.py --video-name clip_10_up_stairs_solo
python link_point_cloud.py clip_10_up_stairs_solo
# Refresh browser
```

---

## Automated Pipeline

Run the complete pipeline interactively:

```bash
./run_pipeline.sh
```

This will guide you through all steps with prompts.

---

## Manual Step-by-Step

### 1. Install Dependencies

**Python:**
```bash
pip install -r requirements.txt
```

**Node.js:**
```bash
npm install
```

**COLMAP:**
```bash
# macOS
brew install colmap

# Linux - see https://colmap.github.io/install.html
```

### 2. Extract Frames

**Option A - Interactive (Recommended):**
```bash
python process_videos.py
```
Choose whether to process all videos or specific clips.

**Option B - Specific clips via command line:**
```bash
python process_videos.py clip_6_hallway_solo.mp4 clip_7_down_stairs_solo.mp4
```

**Options:**
- Adjust `skip_frames` in the script (default: 5 = 12fps from 60fps)
- Uncomment resize line to reduce resolution

**Output:** `extracted_frames/` directory

### 3. Run COLMAP Reconstruction

**Option A - Interactive (Recommended):**
```bash
python run_colmap.py
```
Choose whether to reconstruct all videos or specific clips.

**Option B - Specific clips via command line:**
```bash
python run_colmap.py clip_6_hallway_solo clip_7_down_stairs_solo
```

**Option C - Without GPU:**
```bash
python run_colmap.py --no-gpu
```

**⚠️ This takes several minutes to hours!** Start with 1-2 short clips first.

**Output:** 
- `colmap_workspaces/colmap_workspace_{video_name}/sparse/0/` - reconstruction data
- `colmap_workspaces/colmap_workspace_{video_name}/point_cloud.ply` - 3D point cloud

**Note:** Each video gets its own workspace automatically, so they never mix!

### 4. Export Trajectory

**For a specific video:**
```bash
python export_trajectory.py --video-name clip_6_hallway_solo
```

**Export all reconstructed frames (if you processed multiple videos together):**
```bash
python export_trajectory.py
```

**Output:** `public/trajectory.json`

### 5. Link Point Cloud

**For video-specific workspace:**
```bash
python link_point_cloud.py clip_6_hallway_solo
```

**For default workspace:**
```bash
python link_point_cloud.py
```

This creates a symlink from the video's point cloud to `public/point_cloud.ply`

### 6. Launch Viewer

```bash
npm run dev
```

Open browser to http://localhost:3000

---

## Understanding Multi-Video Processing

### Automatic Video Separation

**Each video automatically gets its own workspace!** When you process a single video, it creates:
- `colmap_workspaces/colmap_workspace_{video_name}/` - dedicated workspace
- Files are completely isolated - videos never mix

**Process as many videos as you want:**

```bash
# Process video 1
python process_videos.py clip_6_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo
python export_trajectory.py --video-name clip_6_hallway_solo
python link_point_cloud.py clip_6_hallway_solo

# Process video 2 - won't affect video 1!
python process_videos.py clip_10_up_stairs_solo.mp4
python run_colmap.py clip_10_up_stairs_solo
python export_trajectory.py --video-name clip_10_up_stairs_solo
python link_point_cloud.py clip_10_up_stairs_solo
```

**Switching between videos:**

```bash
# View video 1
python export_trajectory.py --video-name clip_6_hallway_solo
python link_point_cloud.py clip_6_hallway_solo
# Refresh browser

# View video 2
python export_trajectory.py --video-name clip_10_up_stairs_solo
python link_point_cloud.py clip_10_up_stairs_solo
# Refresh browser
```

### Workspace Structure

```
colmap_workspaces/
├── colmap_workspace_clip_6_hallway_solo/
│   ├── sparse/
│   ├── images/
│   └── point_cloud.ply
├── colmap_workspace_clip_10_up_stairs_solo/
│   ├── sparse/
│   ├── images/
│   └── point_cloud.ply
└── ...
```

# Export separate trajectories
python export_trajectory.py --video-name clip_6 --output public/trajectory_clip6.json
python export_trajectory.py --video-name clip_10 --output public/trajectory_clip10.json
```

Then modify `src/main.js` to load the specific trajectory file you want to view.

---

## Common Workflows

**Process single clip (recommended):**
```bash
# Extract frames
python process_videos.py clip_6_hallway_solo.mp4

# Reconstruct (creates video-specific workspace: colmap_workspace_clip_6_hallway_solo)
python run_colmap.py clip_6_hallway_solo

# Export trajectory
python export_trajectory.py --video-name clip_6_hallway_solo

# Link point cloud
python link_point_cloud.py clip_6_hallway_solo

# View
npm run dev
```

**Process different clip:**
```bash
# Reconstruct different video (creates separate workspace: colmap_workspace_clip_10_up_stairs_solo)
python run_colmap.py clip_10_up_stairs_solo

# Export and link for new video
python export_trajectory.py --video-name clip_10_up_stairs_solo
python link_point_cloud.py clip_10_up_stairs_solo

# Refresh browser to see new video
```

**Switch back to previous video:**
```bash
# Just re-export and re-link (reconstruction already exists)
python export_trajectory.py --video-name clip_6_hallway_solo
python link_point_cloud.py clip_6_hallway_solo

# Refresh browser
```

**Just visualization:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
```

---

## Recommended Clips for Testing

**Best solo clips (no moving objects):**
- `clip_6_hallway_solo.mp4` - Good for testing
- `clip_7_down_stairs_solo.mp4`
- `clip_8_walking_solo.mp4`
- `clip_9_walking_solo.mp4`
- `clip_10_up_stairs_solo.mp4`
- `clip_11_hallway_solo.mp4`

**Clips with dog (may have artifacts):**
- `clip_1_apartment_dog.mp4`
- `clip_2_hallway_dog.mp4`
- `clip_3_down_stairs_dog.mp4`
- `clip_4_outside_dog.mp4`
- `clip_5_apartment_dog.mp4`

**⚠️ About Moving Objects:**

COLMAP assumes a static scene, so the dog and other moving objects may cause:
- Outlier feature matches
- "Ghost" points in the reconstruction
- Slightly reduced quality

However, COLMAP has built-in outlier rejection that handles moderate dynamic content reasonably well. The reconstruction will still work, but for best quality results, prioritize the "solo" clips or clips where the dog is mostly stationary.ust visualization:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
```

---

## Video Information

**Weird artifacts or ghost points:**
- Likely caused by moving objects (dog, people)
- Try clips without moving objects
- COLMAP's outlier rejection helps but isn't perfect

**Want to reconstruct a different clip:**
- Delete `colmap_workspace/` directory
- Run the pipeline again with new clip selection

You currently have these video clips:
- clip_1_apartment_dog.mp4
- clip_2_hallway_dog.mp4
- clip_3_down_stairs_dog.mp4
- clip_4_outside_dog.mp4
- clip_5_apartment_dog.mp4
- clip_5_up_stairs_dog.mp4
- clip_6_hallway_solo.mp4
- clip_7_down_stairs_solo.mp4
- clip_8_walking_solo.mp4
- clip_9_walking_solo.mp4
- clip_10_up_stairs_solo.mp4
- clip_11_hallway_solo.mp4

**Tip:** Start with a single short clip first to test the pipeline before processing all videos.

---

## Troubleshooting

**COLMAP fails - GPU error:**
Edit `run_colmap.py` and set GPU flags to "0"

**Out of memory:**
- Reduce frame extraction rate (higher skip_frames)
- Uncomment resize in process_videos.py
- Process fewer videos at once

**Point cloud not showing:**
Check browser console and ensure:
- `public/point_cloud.ply` exists
- `public/trajectory.json` exists
- Files are accessible via dev server

**No features matched:**
- Videos may have insufficient texture
- Try different video segments
- Ensure good lighting in source videos
