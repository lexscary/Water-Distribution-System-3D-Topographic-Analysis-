import streamlit as st
import streamlit.components.v1 as components
import json
import os

# Set page config
st.set_page_config(layout="wide", page_title="3D Topographic Analysis", page_icon="⛰️")

# Read Data
try:
    with open('topographic_data.json', 'r') as f:
        topo_data = json.load(f)
    topo_json_str = json.dumps(topo_data)
except FileNotFoundError:
    st.error("topographic_data.json not found!")
    st.stop()

# Read CSS
try:
    with open('styles.css', 'r') as f:
        css_content = f.read()
except FileNotFoundError:
    css_content = ""

# Read JS
try:
    with open('app.js', 'r') as f:
        js_content = f.read()
        # Remove imports since we are inlining and using importmap
        # We need to strip the import lines to prevent syntax errors in non-module environments if not handled carefully
        # But we will use type="module" so imports work if they point to URLs. 
        # The user's app.js imports from 'three' and 'three/...'. 
        # Our import map in HTMl handles this.
except FileNotFoundError:
    js_content = "console.error('app.js not found');"

# Construct HTML Wrapper
# We need to inject the data into a global variable BEFORE app.js runs, 
# and we need to modify app.js to use that global variable instead of fetching.
# OR we can just mock fetch.

# Let's mock fetch for topographic_data.json to return our data immediately?
# Or easier: modify the JS execution.

# Modification:
# 1. Inject `window.embeddedTopoData = ...`
# 2. Override `loadTopographicData` in the script to use this data.

override_js = """
// Override loadTopographicData to use embedded data
async function loadTopographicData() {
    topoData = window.embeddedTopoData;
    
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
        
        const dist = Math.sqrt(
            Math.pow(stationB.northing - stationA.northing, 2) + 
            Math.pow(stationB.easting - stationA.easting, 2)
        );
        const elevGain = stationB.elevation - stationA.elevation;
        
        document.getElementById('pipeline-distance').textContent = dist.toFixed(1) + 'm';
        document.getElementById('elevation-gain').textContent = elevGain.toFixed(2) + 'm';
        document.getElementById('pipeline-slope').textContent = (elevGain / dist * 100).toFixed(2) + '%';
    }
}
"""

# HTML Template
html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Topographic Map Visualization</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {css_content}
        /* Adjustments for iframe */
        body {{ background: transparent; overflow: hidden; }}
        #terrain-canvas {{ position: absolute; }}
    </style>
    <!-- Import Map -->
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/examples/jsm/controls/OrbitControls.js": "https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js"
        }}
    }}
    </script>
</head>
<body>
    <canvas id="terrain-canvas"></canvas>

    <header class="app-header">
        <h1>Water Distribution System</h1>
        <p class="subtitle">3D Topographic Analysis - York University</p>
    </header>

    <aside class="info-panel">
        <h2>Terrain Data</h2>
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">Survey Points</span>
                <span class="info-value" id="point-count">-</span>
            </div>
            <div class="info-item">
                <span class="info-label">Min Elevation</span>
                <span class="info-value" id="min-elevation">-</span>
            </div>
            <div class="info-item">
                <span class="info-label">MaxElevation</span>
                <span class="info-value" id="max-elevation">-</span>
            </div>
            <div class="info-item">
                <span class="info-label">Relief</span>
                <span class="info-value" id="relief">-</span>
            </div>
        </div>
        <div class="pipeline-stats">
            <h3>Pipeline Alignment (A → B)</h3>
            <div class="stat-row">
                <span class="stat-label">Horizontal Distance:</span>
                <span class="stat-value" id="pipeline-distance">-</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Elevation Gain:</span>
                <span class="stat-value" id="elevation-gain">-</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Average Slope:</span>
                <span class="stat-value" id="pipeline-slope">-</span>
            </div>
        </div>
        <div class="elevation-legend">
            <h3>Elevation Scale</h3>
            <div class="gradient-bar"></div>
            <div class="legend-labels">
                <span>Low</span>
                <span>Mid</span>
                <span>High</span>
            </div>
        </div>
        <div class="special-points">
            <h3>Water Distribution Stations</h3>
            <div class="point-marker tjoint">
                <span class="marker-icon">📍</span>
                <div class="marker-info">
                    <strong>Station A - T-Joint</strong>
                    <small>Source Point</small>
                </div>
            </div>
            <div class="point-marker reservoir">
                <span class="marker-icon">💧</span>
                <div class="marker-info">
                    <strong>Station B - Reservoir</strong>
                    <small>Target Point</small>
                </div>
            </div>
        </div>
    </aside>

    <aside class="control-panel">
        <h2>Controls</h2>
        <div class="control-group">
            <h3>Camera View</h3>
            <div class="button-group">
                <button class="control-btn active" data-view="default"><span>🎯</span> Default</button>
                <button class="control-btn" data-view="top"><span>⬇️</span> Top</button>
                <button class="control-btn" data-view="north"><span>⬆️</span> North</button>
                <button class="control-btn" data-view="south"><span>⬇️</span> South</button>
            </div>
        </div>
        <div class="control-group">
            <h3>Display Options</h3>
            <label class="checkbox-label"><input type="checkbox" id="show-wireframe"><span>Wireframe</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-contours" checked><span>Contours</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-pipeline" checked><span>Pipeline Route</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-markers" checked><span>Station Markers</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-grid"><span>Grid Helper</span></label>
        </div>
        <div class="control-group">
            <h3>Lighting</h3>
            <label class="slider-label"><span>Intensity</span><input type="range" id="light-intensity" min="0" max="2" step="0.1" value="1.2"><span id="light-value">1.2</span></label>
            <label class="checkbox-label"><input type="checkbox" id="rotate-light"><span>Rotate Light</span></label>
        </div>
        <div class="control-group">
            <h3>Color Scheme</h3>
            <select id="color-scheme" class="select-input">
                <option value="terrain">Terrain</option>
                <option value="rainbow">Rainbow</option>
                <option value="grayscale">Grayscale</option>
                <option value="heatmap">Heatmap</option>
            </select>
        </div>
    </aside>

    <div class="instructions">
        <p><strong>Controls:</strong> Left-click + drag to rotate | Scroll to zoom | Right-click + drag to pan</p>
    </div>

    <div class="loading-screen" id="loading-screen">
        <div class="loader"></div>
        <p>Loading embedded data...</p>
    </div>

    <script>
        // Embed data
        window.embeddedTopoData = {topo_json_str};
    </script>
    
    <script type="module">
        {js_content.replace('loadTopographicData();', '/*loadTopographicData();*/')}
        
        {override_js}
        
        // Re-call init or ensure it runs (original app.js calls init() at the end? No, let's check)
        // Original app.js likely calls init() or it's just defined.
        // We need to call init() manually if it's not called, or let it run.
        // Looking at the file, it defines init() and calls it at the end? 
        // We should ensure we call our overridden version if needed.
        
        // Actually, the original code had:
        // loadTopographicData(); ... then init();
        // Wait, app.js content:
        // -> definition of init()
        // -> init() called at EOF? Or DOMContentLoaded?
        
        // Let's assume the user code calls init(). If so, it will call OUR overridden loadTopographicData because functions are hoisted or we redefined it in the same scope?
        // Ah, "module" scope is strict.
        // We should append our override logic TO the js_content before writing it, OR use a single script block.
        
        // Better approach: Modify js_content string to replace the loadTopographicData function directly.
    </script>
</body>
</html>
"""

# Refined JS Injection
# We will inject the data variable at the top of the JS content, and replace the loadTopographicData function implementation.
new_js_content = js_content.replace(
    "async function loadTopographicData() {", 
    "async function loadTopographicData() { topoData = window.embeddedTopoData; " + 
    "/* Original fetch removed */ " + 
    "// Mocking the rest of the function logic explicitly if needed, but the original function had UI updates inside." + 
    "// We can just COPY the UI update logic here or rely on the original function body if we only remove the fetch."
)

# Actually, the original function body relies on `response.json()`.
# Let's replace the whole function using string replacement to be safe.
# Or simpler: simpler replacement of the fetch line.
js_ready = js_content.replace(
    "const response = await fetch('topographic_data.json');", 
    "// const response = await fetch('topographic_data.json');"
).replace(
    "topoData = await response.json();",
    "topoData = window.embeddedTopoData;"
)

# Write the HTML
html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Topographic Map</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {css_content}
        body {{ background: transparent; overflow: hidden; }}
        #terrain-canvas {{ position: absolute; top:0; left:0; width:100%; height:100%; }}
    </style>
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/examples/jsm/controls/OrbitControls.js": "https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js"
        }}
    }}
    </script>
</head>
<body>
    <canvas id="terrain-canvas"></canvas>
    
    <!-- UI Elements from index.html (Simplified or Copied) -->
    <!-- We should really just read index.html body, but I'll reconstruct the key parts for safety or use the file read earlier if I had it fully. -->
    <!-- Since I can't read index.html body easily without parsing, I'll use the hardcoded structure above which mirrors the file I viewed. -->
    
    <header class="app-header">
        <h1>Water Distribution System</h1>
        <p class="subtitle">3D Topographic Analysis - York University</p>
    </header>

    <aside class="info-panel">
        <h2>Terrain Data</h2>
        <div class="info-grid">
            <div class="info-item"><span class="info-label">Survey Points</span><span class="info-value" id="point-count">...</span></div>
            <div class="info-item"><span class="info-label">Min Elevation</span><span class="info-value" id="min-elevation">...</span></div>
            <div class="info-item"><span class="info-label">MaxElevation</span><span class="info-value" id="max-elevation">...</span></div>
            <div class="info-item"><span class="info-label">Relief</span><span class="info-value" id="relief">...</span></div>
        </div>
        <div class="pipeline-stats">
            <h3>Pipeline Alignment (A → B)</h3>
            <div class="stat-row"><span class="stat-label">Horizontal Dist:</span><span class="stat-value" id="pipeline-distance">...</span></div>
            <div class="stat-row"><span class="stat-label">Elevation Gain:</span><span class="stat-value" id="elevation-gain">...</span></div>
            <div class="stat-row"><span class="stat-label">Avg Slope:</span><span class="stat-value" id="pipeline-slope">...</span></div>
        </div>
        <div class="elevation-legend">
            <h3>Elevation Scale</h3>
            <div class="gradient-bar"></div>
            <div class="legend-labels"><span>Low</span><span>Mid</span><span>High</span></div>
        </div>
        <div class="special-points">
            <h3>Water Distribution Stations</h3>
            <div class="point-marker tjoint"><span class="marker-icon">📍</span><div class="marker-info"><strong>Station A</strong><small>T-Joint Source</small></div></div>
            <div class="point-marker reservoir"><span class="marker-icon">💧</span><div class="marker-info"><strong>Station B</strong><small>Reservoir Target</small></div></div>
        </div>
    </aside>

    <aside class="control-panel">
        <h2>Controls</h2>
        <div class="control-group">
            <h3>Camera View</h3>
            <div class="button-group">
                <button class="control-btn active" data-view="default"><span>🎯</span> Default</button>
                <button class="control-btn" data-view="top"><span>⬇️</span> Top</button>
                <button class="control-btn" data-view="north"><span>⬆️</span> North</button>
                <button class="control-btn" data-view="south"><span>⬇️</span> South</button>
            </div>
        </div>
        <div class="control-group">
            <h3>Display</h3>
            <label class="checkbox-label"><input type="checkbox" id="show-wireframe"><span>Wireframe</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-contours" checked><span>Contours</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-pipeline" checked><span>Pipeline</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-markers" checked><span>Markers</span></label>
            <label class="checkbox-label"><input type="checkbox" id="show-grid"><span>Grid</span></label>
        </div>
        <div class="control-group">
            <h3>Lighting</h3>
            <label class="slider-label"><span>Intensity</span><input type="range" id="light-intensity" min="0" max="2" step="0.1" value="1.2"><span id="light-value">1.2</span></label>
            <label class="checkbox-label"><input type="checkbox" id="rotate-light"><span>Rotate</span></label>
        </div>
        <div class="control-group">
            <h3>Colors</h3>
            <select id="color-scheme" class="select-input">
                <option value="terrain">Terrain</option>
                <option value="rainbow">Rainbow</option>
                <option value="grayscale">Grayscale</option>
                <option value="heatmap">Heatmap</option>
            </select>
        </div>
    </aside>

    <div class="loading-screen" id="loading-screen">
        <div class="loader"></div>
        <p>Loading embedded data...</p>
    </div>

    <script>
        window.embeddedTopoData = {topo_json_str};
    </script>
    <script type="module">
        {js_ready}
    </script>
</body>
</html>
"""

# Render with Streamlit
st.title("Water Distribution System - 3D Visualization")
st.markdown("This application embeds the custom Three.js visualization engine.")

components.html(html_content, height=900, scrolling=False)
