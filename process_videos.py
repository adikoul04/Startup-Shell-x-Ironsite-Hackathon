"""
Step 1: Extract frames from video segments
"""
import cv2
import os
from pathlib import Path
from tqdm import tqdm


class VideoFrameExtractor:
    def __init__(self, videos_dir="videos", output_dir="extracted_frames"):
        self.videos_dir = Path(videos_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def extract_frames(self, video_path, skip_frames=5):
        """
        Extract frames from video, skipping frames for efficiency
        
        Args:
            video_path: Path to video file
            skip_frames: Extract every Nth frame (5 = extract 12fps from 60fps)
        """
        video_name = Path(video_path).stem
        output_folder = self.output_dir / video_name
        output_folder.mkdir(exist_ok=True)
        
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Processing {video_name}: {total_frames} frames @ {fps} FPS")
        
        frame_count = 0
        saved_count = 0
        
        with tqdm(total=total_frames) as pbar:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % skip_frames == 0:
                    # Resize to reduce processing time (optional)
                    # frame = cv2.resize(frame, (1280, 720))
                    
                    output_path = output_folder / f"frame_{saved_count:06d}.jpg"
                    cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    saved_count += 1
                
                frame_count += 1
                pbar.update(1)
        
        cap.release()
        
        print(f"Extracted {saved_count} frames from {video_name}")
        return saved_count
    
    def list_videos(self):
        """List all available video files"""
        video_extensions = ['.mp4', '.mov', '.avi', '.MP4', '.MOV']
        video_files = sorted([f for f in self.videos_dir.glob('*') 
                             if f.suffix in video_extensions])
        return video_files
    
    def process_videos(self, video_names=None, skip_frames=5):
        """
        Process specified video files or all videos if none specified
        
        Args:
            video_names: List of video filenames (e.g., ['clip_6_hallway_solo.mp4'])
                        or None to process all videos
            skip_frames: Extract every Nth frame (5 = extract 12fps from 60fps)
        """
        video_extensions = ['.mp4', '.mov', '.avi', '.MP4', '.MOV']
        
        if video_names is None:
            # Process all videos
            video_files = [f for f in self.videos_dir.glob('*') 
                          if f.suffix in video_extensions]
        else:
            # Process specified videos
            video_files = []
            for name in video_names:
                video_path = self.videos_dir / name
                if video_path.exists() and video_path.suffix in video_extensions:
                    video_files.append(video_path)
                else:
                    print(f"Warning: Video not found: {name}")
        
        if not video_files:
            print(f"No videos found to process")
            return
        
        print(f"\nProcessing {len(video_files)} video(s):")
        for vf in video_files:
            print(f"  - {vf.name}")
        print()
        
        for video_path in video_files:
            self.extract_frames(video_path, skip_frames)


if __name__ == "__main__":
    import sys
    
    extractor = VideoFrameExtractor()
    
    # List available videos
    print("Available videos:")
    videos = extractor.list_videos()
    for i, v in enumerate(videos, 1):
        print(f"  {i}. {v.name}")
    print()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Process specific videos passed as arguments
        video_names = sys.argv[1:]
        print(f"Processing specified videos: {video_names}")
        extractor.process_videos(video_names=video_names, skip_frames=5)
    else:
        # No arguments - show options
        print("Options:")
        print("  1. Process ALL videos")
        print("  2. Process specific videos")
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            extractor.process_videos(skip_frames=5)
        elif choice == "2":
            print("\nEnter video filenames (comma-separated):")
            print("Example: clip_6_hallway_solo.mp4, clip_7_down_stairs_solo.mp4")
            video_input = input("> ").strip()
            video_names = [v.strip() for v in video_input.split(',')]
            extractor.process_videos(video_names=video_names, skip_frames=5)
        else:
            print("Invalid choice. Exiting.")
