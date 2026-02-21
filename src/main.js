import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';

class EnvironmentViewer {
    constructor() {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(
            75,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );
        
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setClearColor(0x1a1a1a);
        
        document.getElementById('canvas-container').appendChild(this.renderer.domElement);
        
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        
        this.trajectory = null;
        this.currentFrame = 0;
        this.isPlaying = false;
        
        // Container for all reconstruction elements (for rotation)
        this.reconstructionGroup = new THREE.Group();
        this.scene.add(this.reconstructionGroup);
        
        this.setupScene();
        this.setupControls();
        this.loadData();
        this.animate();
    }
    
    setupScene() {
        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 10);
        this.scene.add(directionalLight);
        
        // Grid - keep in world space so it stays horizontal
        const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
        this.scene.add(gridHelper);
        
        // Axes helper - keep in world space so it stays axis-aligned
        const axesHelper = new THREE.AxesHelper(5);
        this.scene.add(axesHelper);
        
        // Camera path line
        this.pathLine = null;
        
        // Current position marker
        const markerGeometry = new THREE.SphereGeometry(0.15, 16, 16);
        const markerMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        this.positionMarker = new THREE.Mesh(markerGeometry, markerMaterial);
        this.reconstructionGroup.add(this.positionMarker);
        
        this.camera.position.set(5, 3, 8);
        this.camera.lookAt(0, 0, 0);
    }
    
    setupControls() {
        const timeline = document.getElementById('timeline');
        const playBtn = document.getElementById('play-btn');
        const resetBtn = document.getElementById('reset-btn');
        
        timeline.addEventListener('input', (e) => {
            this.currentFrame = parseInt(e.target.value);
            this.updatePosition();
        });
        
        playBtn.addEventListener('click', () => {
            this.isPlaying = !this.isPlaying;
            playBtn.textContent = this.isPlaying ? 'Pause' : 'Play';
        });
        
        resetBtn.addEventListener('click', () => {
            this.currentFrame = 0;
            this.isPlaying = false;
            playBtn.textContent = 'Play';
            this.updatePosition();
        });
        
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }
    
    async loadData() {
        // Load point cloud
        const plyLoader = new PLYLoader();
        try {
            const geometry = await plyLoader.loadAsync('/point_cloud.ply');
            geometry.computeVertexNormals();
            
            // Apply the same coordinate transformation as the trajectory
            // COLMAP: X=right, Y=down, Z=forward -> Three.js: X=right, Y=up, Z=back
            const positions = geometry.attributes.position;
            for (let i = 0; i < positions.count; i++) {
                const x = positions.getX(i);
                const y = positions.getY(i);
                const z = positions.getZ(i);
                
                // Apply same transformation as trajectory
                positions.setX(i, -x);  // Negate X
                positions.setY(i, -y);  // Negate Y
                positions.setZ(i, z);   // Keep Z
            }
            positions.needsUpdate = true;
            
            const material = new THREE.PointsMaterial({
                size: 0.05,
                vertexColors: true
            });
            
            const pointCloud = new THREE.Points(geometry, material);
            this.reconstructionGroup.add(pointCloud);
            
            console.log('Point cloud loaded and transformed');
        } catch (error) {
            console.error('Error loading point cloud:', error);
        }
        
        // Load trajectory
        try {
            const response = await fetch('/trajectory.json');
            this.trajectory = await response.json();
            
            this.createPathVisualization();
            this.updateStats();
            this.alignToGroundPlane();
            
            // Setup timeline
            const timeline = document.getElementById('timeline');
            timeline.max = this.trajectory.frames.length - 1;
            
        } catch (error) {
            console.error('Error loading trajectory:', error);
        }
    }
    
    createPathVisualization() {
        if (!this.trajectory || this.trajectory.frames.length === 0) return;
        
        const points = this.trajectory.frames.map(frame => 
            new THREE.Vector3(...frame.position)
        );
        
        const pathGeometry = new THREE.BufferGeometry().setFromPoints(points);
        const pathMaterial = new THREE.LineBasicMaterial({ 
            color: 0x00ff00,
            linewidth: 2
        });
        
        this.pathLine = new THREE.Line(pathGeometry, pathMaterial);
        this.reconstructionGroup.add(this.pathLine);
    }
    
    alignToGroundPlane() {
        if (!this.trajectory || this.trajectory.frames.length === 0) return;
        
        // Get all positions
        const positions = this.trajectory.frames.map(f => new THREE.Vector3(...f.position));
        
        // Sort by Z (forward progression) to segment the path
        const indexed = positions.map((p, i) => ({ pos: p, idx: i }));
        indexed.sort((a, b) => a.pos.z - b.pos.z);
        
        // Find flat segments (ground plane) by analyzing Y-variation in sliding windows
        const WINDOW_SIZE = 30; // frames
        const segments = [];
        
        for (let i = 0; i <= indexed.length - WINDOW_SIZE; i++) {
            const window = indexed.slice(i, i + WINDOW_SIZE);
            const windowPositions = window.map(w => w.pos);
            
            // Calculate Y variance in this window
            const yValues = windowPositions.map(p => p.y);
            const yMean = yValues.reduce((a, b) => a + b, 0) / yValues.length;
            const yVariance = yValues.reduce((sum, y) => sum + (y - yMean) ** 2, 0) / yValues.length;
            
            segments.push({
                startIdx: i,
                positions: windowPositions,
                yVariance: yVariance,
                size: WINDOW_SIZE
            });
        }
        
        // Sort by variance to find flattest segments
        segments.sort((a, b) => a.yVariance - b.yVariance);
        
        // Use ALL segments with low variance (not just the single flattest)
        // This captures the entire flat walking path, including turns
        const FLAT_VARIANCE_THRESHOLD = 0.05; // Segments flatter than this are considered ground
        const flatSegments = segments.filter(s => s.yVariance < FLAT_VARIANCE_THRESHOLD);
        
        // If we don't have enough flat segments, use the top 25% flattest ones
        const minFlatSegments = Math.max(10, Math.floor(segments.length * 0.25));
        const groundSegments = flatSegments.length >= minFlatSegments 
            ? flatSegments 
            : segments.slice(0, minFlatSegments);
        
        console.log(`Found ${segments.length} total segments. Using ${groundSegments.length} flattest segments for ground plane.`);
        console.log(`Flattest segment Y-variance: ${segments[0].yVariance.toFixed(4)}, threshold: ${FLAT_VARIANCE_THRESHOLD}`);
        
        // Combine all ground segment positions
        const groundPositions = [];
        groundSegments.forEach(seg => {
            seg.positions.forEach(p => groundPositions.push(p));
        });
        
        // Remove duplicates (since windows overlap)
        const uniqueGroundPositions = [];
        const seen = new Set();
        groundPositions.forEach(p => {
            const key = `${p.x.toFixed(3)},${p.y.toFixed(3)},${p.z.toFixed(3)}`;
            if (!seen.has(key)) {
                seen.add(key);
                uniqueGroundPositions.push(p);
            }
        });
        
        console.log(`Ground plane fitted to ${uniqueGroundPositions.length} points from flat segments`);
        
        console.log(`Ground plane fitted to ${uniqueGroundPositions.length} points from flat segments`);
        
        // Calculate centroid of all ground points
        const centroid = new THREE.Vector3();
        uniqueGroundPositions.forEach(p => centroid.add(p));
        centroid.divideScalar(uniqueGroundPositions.length);
        
        console.log('Ground centroid:', centroid.x.toFixed(3), centroid.y.toFixed(3), centroid.z.toFixed(3));
        
        console.log('Fitting plane to ground segment to correct tilt...');
        
        // Fit plane to the GROUND SEGMENT only (not all points)
        // This finds the true ground orientation even with stairs in the video
        let bestNormal = new THREE.Vector3(0, 1, 0);
        let minError = Infinity;
        
        // Sample many directions on a sphere to find best-fit plane normal
        for (let theta = 0; theta < Math.PI; theta += Math.PI / 20) {
            for (let phi = 0; phi < 2 * Math.PI; phi += Math.PI / 20) {
                const nx = Math.sin(theta) * Math.cos(phi);
                const ny = Math.cos(theta);
                const nz = Math.sin(theta) * Math.sin(phi);
                
                // Calculate sum of squared distances from GROUND POINTS to plane with this normal
                let error = 0;
                uniqueGroundPositions.forEach(p => {
                    const dx = p.x - centroid.x;
                    const dy = p.y - centroid.y;
                    const dz = p.z - centroid.z;
                    const dist = nx * dx + ny * dy + nz * dz;
                    error += dist * dist;
                });
                
                if (error < minError) {
                    minError = error;
                    bestNormal.set(nx, ny, nz);
                }
            }
        }
        
        // Ensure normal points upward (positive Y component preferred)
        if (bestNormal.y < 0) bestNormal.negate();
        
        console.log('Ground plane normal (from flattest segment):', bestNormal.x.toFixed(3), bestNormal.y.toFixed(3), bestNormal.z.toFixed(3));
        console.log('Plane fit error:', minError.toFixed(3));
        
        // Calculate rotation to align normal with Y-axis (0, 1, 0)
        const targetUp = new THREE.Vector3(0, 1, 0);
        const quaternion = new THREE.Quaternion();
        quaternion.setFromUnitVectors(bestNormal, targetUp);
        
        // Apply rotation to reconstruction group
        this.reconstructionGroup.setRotationFromQuaternion(quaternion);
        
        // After rotation, recalculate world positions and offset to ground
        this.reconstructionGroup.updateMatrixWorld();
        const worldPositions = positions.map(p => {
            const wp = p.clone();
            this.reconstructionGroup.localToWorld(wp);
            return wp;
        });
        
        const minY = Math.min(...worldPositions.map(p => p.y));
        const maxY = Math.max(...worldPositions.map(p => p.y));
        
        // Position reconstruction so minimum Y is at ground (Y=0)
        this.reconstructionGroup.position.y = -minY;
        
        console.log('After alignment - Y range:', minY.toFixed(3), 'to', maxY.toFixed(3), ', Y variation:', (maxY - minY).toFixed(3));
    }
    
    updatePosition() {
        if (!this.trajectory || this.trajectory.frames.length === 0) return;
        
        const frame = this.trajectory.frames[this.currentFrame];
        this.positionMarker.position.set(...frame.position);
        
        // Update timeline slider
        document.getElementById('timeline').value = this.currentFrame;
        
        // Update time display
        const currentTime = this.currentFrame / this.trajectory.fps;
        const totalTime = this.trajectory.duration;
        document.getElementById('time-display').textContent = 
            `${currentTime.toFixed(2)}s / ${totalTime.toFixed(2)}s`;
    }
    
    updateStats() {
        if (!this.trajectory) return;
        
        const stats = document.getElementById('stats');
        const metadata = this.trajectory.metadata || {};
        const yRange = metadata.y_range || 0;
        
        stats.innerHTML = `
            <p>Total Frames: ${this.trajectory.frames.length}</p>
            <p>Duration: ${this.trajectory.duration.toFixed(2)}s</p>
            <p>FPS: ${this.trajectory.fps}</p>
            <p>Y Range: ${yRange.toFixed(2)} units</p>
            <p style="font-size: 0.8em; color: #aaa;">Red sphere = camera position</p>
            <p style="font-size: 0.8em; color: #aaa;">Green line = path</p>
        `;
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.isPlaying && this.trajectory) {
            this.currentFrame = (this.currentFrame + 1) % this.trajectory.frames.length;
            this.updatePosition();
        }
        
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize viewer
new EnvironmentViewer();
