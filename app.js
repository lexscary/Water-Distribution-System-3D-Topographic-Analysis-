import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// ============================================
// GLOBAL STATE
// ============================================
let scene, camera, renderer, controls;
let terrainMesh, wireframeMesh, contourLines, markers, gridHelper, pipelinePath;
let topoData = null;
let lightRotating = false;
let directionalLight, ambientLight;
let colorScheme = 'terrain';

// ============================================
// COLOR SCHEMES
// ============================================
const COLOR_SCHEMES = {
    terrain: [
        { stop: 0.0, color: new THREE.Color(0x2563eb) },   // Blue (lowest)
        { stop: 0.2, color: new THREE.Color(0x06b6d4) },   // Cyan
        { stop: 0.4, color: new THREE.Color(0x10b981) },   // Green
        { stop: 0.6, color: new THREE.Color(0xfbbf24) },   // Yellow
        { stop: 0.8, color: new THREE.Color(0xf97316) },   // Orange
        { stop: 1.0, color: new THREE.Color(0xdc2626) }    // Red (highest)
    ],
    rainbow: [
        { stop: 0.0, color: new THREE.Color(0x9333ea) },   // Purple
        { stop: 0.2, color: new THREE.Color(0x3b82f6) },   // Blue
        { stop: 0.4, color: new THREE.Color(0x06b6d4) },   // Cyan
        { stop: 0.6, color: new THREE.Color(0x10b981) },   // Green
        { stop: 0.8, color: new THREE.Color(0xfbbf24) },   // Yellow
        { stop: 1.0, color: new THREE.Color(0xef4444) }    // Red
    ],
    grayscale: [
        { stop: 0.0, color: new THREE.Color(0x1f2937) },
        { stop: 0.5, color: new THREE.Color(0x6b7280) },
        { stop: 1.0, color: new THREE.Color(0xe5e7eb) }
    ],
    heatmap: [
        { stop: 0.0, color: new THREE.Color(0x1e1b4b) },   // Dark blue
        { stop: 0.3, color: new THREE.Color(0x7c2d12) },   // Dark orange
        { stop: 0.6, color: new THREE.Color(0xdc2626) },   // Red
        { stop: 0.8, color: new THREE.Color(0xfbbf24) },   // Yellow
        { stop: 1.0, color: new THREE.Color(0xfef08a) }    // Light yellow
    ]
};

// ============================================
// INITIALIZATION
// ============================================
async function init() {
    // Load topographic data
    await loadTopographicData();

    // Setup Three.js scene
    setupScene();
    setupCamera();
    setupRenderer();
    setupLights();
    setupControls();

    // Create 3D terrain
    createTerrain();
    createMarkers();
    createPipelinePath();
    createContourLines();

    // Setup UI event listeners
    setupEventListeners();

    // Hide loading screen
    document.getElementById('loading-screen').classList.add('hidden');

    // Start animation loop
    animate();
}

// ============================================
// DATA LOADING
// ============================================
async function loadTopographicData() {
    try {
        const response = await fetch('topographic_data.json');
        topoData = await response.json();

        // Update UI with actual data
        document.getElementById('point-count').textContent = topoData.metadata.survey_points;
        document.getElementById('min-elevation').textContent =
            topoData.metadata.bounds.elevation.min.toFixed(2) + 'm';
        document.getElementById('max-elevation').textContent =
            topoData.metadata.bounds.elevation.max.toFixed(2) + 'm';
        document.getElementById('relief').textContent =
            (topoData.metadata.bounds.elevation.max - topoData.metadata.bounds.elevation.min).toFixed(2) + 'm';

        // Update pipeline stats if available
        const waterPoints = topoData.points.filter(p => p.source === 'water_dist');
        if (waterPoints.length === 2) {
            const stationA = waterPoints.find(p => p.station === 'A');
            const stationB = waterPoints.find(p => p.station === 'B');

            const horizontalDist = Math.sqrt(
                Math.pow(stationB.northing - stationA.northing, 2) +
                Math.pow(stationB.easting - stationA.easting, 2)
            );
            const elevGain = stationB.elevation - stationA.elevation;

            document.getElementById('pipeline-distance').textContent = horizontalDist.toFixed(1) + 'm';
            document.getElementById('elevation-gain').textContent = elevGain.toFixed(2) + 'm';
            document.getElementById('pipeline-slope').textContent = (elevGain / horizontalDist * 100).toFixed(2) + '%';
        }

        console.log('Loaded topographic data:', topoData.metadata);
    } catch (error) {
        console.error('Failed to load topographic data:', error);
        alert('Failed to load topographic data. Please ensure topographic_data.json exists.');
    }
}

// ============================================
// SCENE SETUP
// ============================================
function setupScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e1a);
    scene.fog = new THREE.Fog(0x0a0e1a, 200, 500);
}

function setupCamera() {
    camera = new THREE.PerspectiveCamera(
        60,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.set(80, 60, 80);
    camera.lookAt(0, 0, 0);
}

function setupRenderer() {
    const canvas = document.getElementById('terrain-canvas');
    renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: false
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
}

function setupLights() {
    // Ambient light for base illumination
    ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    // Directional light for shadows and depth
    directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
    directionalLight.position.set(50, 80, 50);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.near = 0.5;
    directionalLight.shadow.camera.far = 500;
    directionalLight.shadow.camera.left = -100;
    directionalLight.shadow.camera.right = 100;
    directionalLight.shadow.camera.top = 100;
    directionalLight.shadow.camera.bottom = -100;
    scene.add(directionalLight);

    // Hemisphere light for natural sky/ground lighting
    const hemiLight = new THREE.HemisphereLight(0x00d4ff, 0x2563eb, 0.3);
    scene.add(hemiLight);
}

function setupControls() {
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 20;
    controls.maxDistance = 200;
    controls.maxPolarAngle = Math.PI / 2 - 0.1; // Prevent going below ground
    controls.autoRotate = false;
    controls.autoRotateSpeed = 0.5;
}

// ============================================
// TERRAIN GENERATION
// ============================================
function createTerrain() {
    if (!topoData || !topoData.points) return;

    const points = topoData.points;
    const bounds = topoData.metadata.bounds;

    // Normalize coordinates to center the terrain at origin
    const centerN = (bounds.northing.min + bounds.northing.max) / 2;
    const centerE = (bounds.easting.min + bounds.easting.max) / 2;
    const centerZ = (bounds.elevation.min + bounds.elevation.max) / 2;

    // Create terrain using a grid-based approach
    const gridSize = 50;
    const rangeN = bounds.northing.max - bounds.northing.min;
    const rangeE = bounds.easting.max - bounds.easting.min;
    const rangeZ = bounds.elevation.max - bounds.elevation.min;

    const geometry = new THREE.PlaneGeometry(100, 100, gridSize - 1, gridSize - 1);
    geometry.rotateX(-Math.PI / 2);

    const positions = geometry.attributes.position;
    const colors = new Float32Array(positions.count * 3);

    // Create elevation map from points using inverse distance weighting
    for (let i = 0; i < positions.count; i++) {
        const x = positions.getX(i);
        const z = positions.getZ(i);

        // Convert grid position to actual coordinates
        const normalizedN = (x + 50) / 100;
        const normalizedE = (z + 50) / 100;
        const actualN = bounds.northing.min + normalizedN * rangeN;
        const actualE = bounds.easting.min + normalizedE * rangeE;

        // Find elevation using inverse distance weighting
        let elevation = interpolateElevation(actualN, actualE, points);

        // Normalize elevation
        const normalizedElev = (elevation - bounds.elevation.min) / rangeZ;

        // Set vertex height (scaled for visual impact)
        const heightScale = 20; // Increased exaggeration for better definition
        const y = (elevation - bounds.elevation.min) * heightScale / rangeZ;
        positions.setY(i, y);

        // Set vertex color based on elevation
        const color = getColorForElevation(normalizedElev);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
    }

    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.computeVertexNormals();

    // Create terrain mesh
    const material = new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.8,
        metalness: 0.2,
        flatShading: false
    });

    terrainMesh = new THREE.Mesh(geometry, material);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = true;
    scene.add(terrainMesh);

    // Create wireframe overlay (initially hidden)
    const wireframeGeometry = geometry.clone();
    const wireframeMaterial = new THREE.MeshBasicMaterial({
        color: 0x00d4ff,
        wireframe: true,
        transparent: true,
        opacity: 0.3
    });
    wireframeMesh = new THREE.Mesh(wireframeGeometry, wireframeMaterial);
    wireframeMesh.visible = false;
    scene.add(wireframeMesh);
}

// Interpolate elevation using inverse distance weighting
function interpolateElevation(n, e, points, maxNeighbors = 8) {
    // Find nearest neighbors
    const distances = points.map(p => ({
        point: p,
        dist: Math.sqrt(
            Math.pow(p.northing - n, 2) +
            Math.pow(p.easting - e, 2)
        )
    }));

    distances.sort((a, b) => a.dist - b.dist);

    // If we're very close to a point, use it directly
    if (distances[0].dist < 0.001) {
        return distances[0].point.elevation;
    }

    // Inverse distance weighting
    const neighbors = distances.slice(0, maxNeighbors);
    let weightedSum = 0;
    let weightSum = 0;

    neighbors.forEach(({ point, dist }) => {
        const weight = 1 / (dist * dist + 0.001);
        weightedSum += point.elevation * weight;
        weightSum += weight;
    });

    return weightedSum / weightSum;
}

// Get color based on elevation (normalized 0-1)
function getColorForElevation(t) {
    const scheme = COLOR_SCHEMES[colorScheme];

    for (let i = 0; i < scheme.length - 1; i++) {
        const current = scheme[i];
        const next = scheme[i + 1];

        if (t >= current.stop && t <= next.stop) {
            const localT = (t - current.stop) / (next.stop - current.stop);
            return current.color.clone().lerp(next.color, localT);
        }
    }

    return scheme[scheme.length - 1].color.clone();
}

// ============================================
// MARKERS FOR SPECIAL POINTS
// ============================================
function createMarkers() {
    if (!topoData) return;

    markers = new THREE.Group();
    const bounds = topoData.metadata.bounds;
    const rangeN = bounds.northing.max - bounds.northing.min;
    const rangeE = bounds.easting.max - bounds.easting.min;
    const rangeZ = bounds.elevation.max - bounds.elevation.min;
    const heightScale = 20;

    // Find water distribution points
    const waterPoints = topoData.points.filter(p => p.source === 'water_dist');

    waterPoints.forEach(point => {
        // Convert to scene coordinates
        const x = ((point.northing - bounds.northing.min) / rangeN) * 100 - 50;
        const z = ((point.easting - bounds.easting.min) / rangeE) * 100 - 50;
        const y = ((point.elevation - bounds.elevation.min) / rangeZ) * heightScale + 2;

        // Create marker
        const geometry = new THREE.CylinderGeometry(0.5, 0.5, 4, 16);
        const color = point.description.includes('T-joint') ? 0x00d4ff : 0xb030ff;
        const material = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.5,
            roughness: 0.3,
            metalness: 0.7
        });

        const marker = new THREE.Mesh(geometry, material);
        marker.position.set(x, y, z);
        marker.castShadow = true;

        // Add a sphere on top
        const sphereGeometry = new THREE.SphereGeometry(0.8, 16, 16);
        const sphere = new THREE.Mesh(sphereGeometry, material);
        sphere.position.y = 2.5;
        marker.add(sphere);

        markers.add(marker);
    });

    scene.add(markers);
}

// ============================================
// PIPELINE PATH
// ============================================
function createPipelinePath() {
    if (!topoData) return;

    const waterPoints = topoData.points.filter(p => p.source === 'water_dist');
    if (waterPoints.length !== 2) return;

    const bounds = topoData.metadata.bounds;
    const rangeN = bounds.northing.max - bounds.northing.min;
    const rangeE = bounds.easting.max - bounds.easting.min;
    const rangeZ = bounds.elevation.max - bounds.elevation.min;
    const heightScale = 20;

    const stationA = waterPoints.find(p => p.station === 'A');
    const stationB = waterPoints.find(p => p.station === 'B');

    // Convert to scene coordinates
    const pointA = new THREE.Vector3(
        ((stationA.northing - bounds.northing.min) / rangeN) * 100 - 50,
        ((stationA.elevation - bounds.elevation.min) / rangeZ) * heightScale + 0.5,
        ((stationA.easting - bounds.easting.min) / rangeE) * 100 - 50
    );

    const pointB = new THREE.Vector3(
        ((stationB.northing - bounds.northing.min) / rangeN) * 100 - 50,
        ((stationB.elevation - bounds.elevation.min) / rangeZ) * heightScale + 0.5,
        ((stationB.easting - bounds.easting.min) / rangeE) * 100 - 50
    );

    // Create curved path (catenary-like curve for realistic pipe sag)
    const curve = new THREE.QuadraticBezierCurve3(
        pointA,
        new THREE.Vector3(
            (pointA.x + pointB.x) / 2,
            (pointA.y + pointB.y) / 2 - 1, // Slight sag
            (pointA.z + pointB.z) / 2
        ),
        pointB
    );

    const points = curve.getPoints(50);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);

    // Create glowing pipeline material
    const material = new THREE.LineBasicMaterial({
        color: 0xff3d9a, // Pink color for pipeline
        linewidth: 3,
        transparent: true,
        opacity: 0.8
    });

    pipelinePath = new THREE.Line(geometry, material);
    scene.add(pipelinePath);

    // Add tube mesh for better visibility
    const tubeMaterial = new THREE.MeshStandardMaterial({
        color: 0xff3d9a,
        emissive: 0xff3d9a,
        emissiveIntensity: 0.3,
        transparent: true,
        opacity: 0.6,
        roughness: 0.3,
        metalness: 0.7
    });

    const tubeGeometry = new THREE.TubeGeometry(curve, 50, 0.3, 8, false);
    const tubeMesh = new THREE.Mesh(tubeGeometry, tubeMaterial);
    tubeMesh.castShadow = true;
    pipelinePath.add(tubeMesh);
}

// ============================================
// CONTOUR LINES
// ============================================
function createContourLines() {
    contourLines = new THREE.Group();

    const bounds = topoData.metadata.bounds;
    const numContours = 10;
    const elevStep = (bounds.elevation.max - bounds.elevation.min) / numContours;
    const rangeZ = bounds.elevation.max - bounds.elevation.min;
    const heightScale = 30;

    for (let i = 1; i < numContours; i++) {
        const elevation = bounds.elevation.min + i * elevStep;
        const y = ((elevation - bounds.elevation.min) / rangeZ) * heightScale;

        const geometry = new THREE.RingGeometry(5 * i, 5 * i + 0.2, 64);
        const material = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.15,
            side: THREE.DoubleSide
        });

        const ring = new THREE.Mesh(geometry, material);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = y;
        contourLines.add(ring);
    }

    scene.add(contourLines);
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    // Window resize
    window.addEventListener('resize', onWindowResize);

    // Camera view buttons
    document.querySelectorAll('[data-view]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-view]').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            setCameraView(e.currentTarget.dataset.view);
        });
    });

    // Wireframe toggle
    document.getElementById('show-wireframe')?.addEventListener('change', (e) => {
        if (wireframeMesh) wireframeMesh.visible = e.target.checked;
    });

    // Contours toggle
    document.getElementById('show-contours')?.addEventListener('change', (e) => {
        if (contourLines) contourLines.visible = e.target.checked;
    });

    // Markers toggle
    document.getElementById('show-markers')?.addEventListener('change', (e) => {
        if (markers) markers.visible = e.target.checked;
    });

    // Pipeline toggle
    document.getElementById('show-pipeline')?.addEventListener('change', (e) => {
        if (pipelinePath) pipelinePath.visible = e.target.checked;
    });

    // Grid helper toggle
    document.getElementById('show-grid')?.addEventListener('change', (e) => {
        if (e.target.checked) {
            if (!gridHelper) {
                gridHelper = new THREE.GridHelper(100, 20, 0x00d4ff, 0x444444);
                scene.add(gridHelper);
            }
            gridHelper.visible = true;
        } else if (gridHelper) {
            gridHelper.visible = false;
        }
    });

    // Light intensity
    const lightIntensitySlider = document.getElementById('light-intensity');
    const lightValue = document.getElementById('light-value');
    lightIntensitySlider?.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        if (directionalLight) directionalLight.intensity = value;
        lightValue.textContent = value.toFixed(1);
    });

    // Rotate light
    document.getElementById('rotate-light')?.addEventListener('change', (e) => {
        lightRotating = e.target.checked;
    });

    // Color scheme
    document.getElementById('color-scheme')?.addEventListener('change', (e) => {
        colorScheme = e.target.value;
        updateTerrainColors();
    });
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// ============================================
// CAMERA VIEWS
// ============================================
function setCameraView(view) {
    const distance = 100;
    let position;

    switch (view) {
        case 'top':
            position = { x: 0, y: 120, z: 0 };
            break;
        case 'north':
            position = { x: 0, y: 50, z: distance };
            break;
        case 'south':
            position = { x: 0, y: 50, z: -distance };
            break;
        default: // default
            position = { x: 80, y: 60, z: 80 };
    }

    // Smooth camera transition
    const duration = 1000;
    const startPos = camera.position.clone();
    const startTime = Date.now();

    function animateCamera() {
        const elapsed = Date.now() - startTime;
        const t = Math.min(elapsed / duration, 1);
        const eased = easeInOutCubic(t);

        camera.position.lerpVectors(startPos, new THREE.Vector3(position.x, position.y, position.z), eased);

        if (t < 1) {
            requestAnimationFrame(animateCamera);
        }
    }

    animateCamera();
}

function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// ============================================
// UPDATE TERRAIN COLORS
// ============================================
function updateTerrainColors() {
    if (!terrainMesh || !topoData) return;

    const geometry = terrainMesh.geometry;
    const positions = geometry.attributes.position;
    const colors = geometry.attributes.color;
    const bounds = topoData.metadata.bounds;
    const rangeZ = bounds.elevation.max - bounds.elevation.min;
    const heightScale = 30;

    for (let i = 0; i < positions.count; i++) {
        const y = positions.getY(i);
        const normalizedElev = y / heightScale;
        const color = getColorForElevation(normalizedElev);

        colors.setXYZ(i, color.r, color.g, color.b);
    }

    colors.needsUpdate = true;
}

// ============================================
// ANIMATION LOOP
// ============================================
function animate() {
    requestAnimationFrame(animate);

    // Rotate light if enabled
    if (lightRotating && directionalLight) {
        const time = Date.now() * 0.0005;
        directionalLight.position.x = Math.cos(time) * 80;
        directionalLight.position.z = Math.sin(time) * 80;
    }

    // Update controls
    controls.update();

    // Render scene
    renderer.render(scene, camera);
}

// ============================================
// START APPLICATION
// ============================================
init();
