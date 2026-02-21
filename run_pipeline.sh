#!/bin/bash

# 3D Environment Reconstruction Pipeline Runner
# This script guides you through the reconstruction process step by step

set -e  # Exit on error

echo "=========================================="
echo "3D Environment Reconstruction Pipeline"
echo "=========================================="
echo ""

# Check if COLMAP is installed
echo "Checking prerequisites..."
if ! command -v colmap &> /dev/null; then
    echo "❌ COLMAP is not installed!"
    echo "Please install COLMAP first:"
    echo "  macOS: brew install colmap"
    echo "  Linux: See https://colmap.github.io/install.html"
    exit 1
else
    echo "✅ COLMAP found: $(which colmap)"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
else
    echo "✅ Python 3 found: $(which python3)"
fi

# Check Node.js
if ! command -v npm &> /dev/null; then
    echo "❌ Node.js/npm is not installed!"
    exit 1
else
    echo "✅ Node.js found: $(which npm)"
fi

echo ""
echo "=========================================="
echo "Step 1: Installing Dependencies"
echo "=========================================="
echo ""

# Install Python dependencies
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "Installing Node.js dependencies..."
npm install --silent

echo "✅ Dependencies installed"
echo ""

# Count videos
video_count=$(find videos -type f \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" \) 2>/dev/null | wc -l | xargs)

echo "=========================================="
echo "Step 2: Extract Frames from Videos"
echo "=========================================="
echo "Found $video_count video files in videos/ directory"
echo ""

read -p "Extract frames? This may take a while. (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python process_videos.py
    echo "✅ Frame extraction complete"
else
    echo "⏭️  Skipping frame extraction"
fi

echo ""
echo "=========================================="
echo "Step 3: Run COLMAP Reconstruction"
echo "=========================================="
echo "⚠️  WARNING: This step can take several hours!"
echo "It will perform:"
echo "  - Feature extraction"
echo "  - Feature matching"
echo "  - Sparse 3D reconstruction"
echo "  - Point cloud export"
echo ""

read -p "Run COLMAP reconstruction? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python run_colmap.py
    echo "✅ COLMAP reconstruction complete"
else
    echo "⏭️  Skipping COLMAP reconstruction"
fi

echo ""
echo "=========================================="
echo "Step 4: Export Camera Trajectory"
echo "=========================================="
echo ""

read -p "Export trajectory? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python export_trajectory.py
    
    # Symlink point cloud to public directory
    if [ -f "colmap_workspace/point_cloud.ply" ]; then
        ln -sf ../colmap_workspace/point_cloud.ply public/point_cloud.ply
        echo "✅ Point cloud symlinked to public directory"
    fi
    
    echo "✅ Trajectory export complete"
else
    echo "⏭️  Skipping trajectory export"
fi

echo ""
echo "=========================================="
echo "Step 5: Launch Web Viewer"
echo "=========================================="
echo ""

read -p "Start development server? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting web viewer at http://localhost:3000"
    echo "Press Ctrl+C to stop the server"
    npm run dev
else
    echo "⏭️  Skipping web viewer"
    echo ""
    echo "To start the viewer later, run: npm run dev"
fi

echo ""
echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
