# Processing Specific Clips - Examples

## Quick Test with Single Clip

**Fastest way to test the pipeline:**

```bash
# 1. Extract frames from one clip
python process_videos.py clip_6_hallway_solo.mp4

# 2. Run COLMAP on that clip
python run_colmap.py clip_6_hallway_solo

# 3. Export and visualize
python export_trajectory.py
ln -sf ../colmap_workspace/point_cloud.ply public/point_cloud.ply
npm run dev
```

---

## Process Multiple Specific Clips

**Example 1: Two hallway clips**
```bash
python process_videos.py clip_6_hallway_solo.mp4 clip_11_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo clip_11_hallway_solo
```

**Example 2: All solo clips (no dog)**
```bash
python process_videos.py clip_6_hallway_solo.mp4 clip_7_down_stairs_solo.mp4 clip_8_walking_solo.mp4 clip_9_walking_solo.mp4 clip_10_up_stairs_solo.mp4 clip_11_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo clip_7_down_stairs_solo clip_8_walking_solo clip_9_walking_solo clip_10_up_stairs_solo clip_11_hallway_solo
```

---

## Interactive Mode

**Don't remember the clip names?**

Just run without arguments and select from a menu:

```bash
# Shows list of all videos, lets you choose
python process_videos.py

# Shows list of extracted clips, lets you choose
python run_colmap.py
```

---

## About the Dog in Videos

**Q: Will the dog cause problems?**

A: COLMAP will still work, but you may see:
- Some "ghost" 3D points where the dog moved
- Slightly reduced reconstruction quality in those areas
- Outlier points that don't belong to the scene

**Q: Should I skip the dog clips?**

A: For best results, **start with the solo clips first**. Once you've tested and it's working, you can experiment with the dog clips to see how COLMAP handles them.

**Q: Can I mix dog and solo clips?**

A: Yes, but it's better to keep them separate. Process solo clips together, and dog clips together.

---

## Recommended First Test

**Start here:**
```bash
python process_videos.py clip_6_hallway_solo.mp4
python run_colmap.py clip_6_hallway_solo --no-gpu
```

This will:
- Process just one short clip
- Use CPU instead of GPU (more compatible)
- Give you quick feedback on whether the pipeline works
- Take less time to complete

If this works, then scale up to more clips or enable GPU.

---

## Switching Between Clips

**To reconstruct a different set of clips:**

```bash
# Delete previous reconstruction
rm -rf colmap_workspace/

# Process new clips
python process_videos.py clip_1_apartment_dog.mp4
python run_colmap.py clip_1_apartment_dog
python export_trajectory.py
```

The extracted frames stay in `extracted_frames/` so you don't need to re-extract if you've already done it.
