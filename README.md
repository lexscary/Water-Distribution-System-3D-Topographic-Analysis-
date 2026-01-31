# Water Distribution System - 3D Topographic Analysis

Interactive 3D visualization of the York University water distribution system alignment.

## Overview
This application renders a high-fidelity **Three.js** 3D environment embedded within **Streamlit**. It visualizes the terrain, pipeline alignment, and water stations (A & B) using a custom mesh generation algorithm.

## Features
- **3D Terrain**: Real-time rendering of 717 survey points.
- **Pipeline Alignment**: Visualized path from T-Joint (Station A) to Reservoir (Station B).
- **Interactive Controls**:
    - **Vertical Exaggeration**: Adjust terrain height scale.
    - **Lighting**: Dynamic sun rotation and intensity.
    - **Camera Views**: Presets for Top, North, South, and Default.
    - **Color Schemes**: Switch between Terrain, Rainbow, Grayscale, and Heatmap.

## How it Works
The application uses a hybrid approach:
- **Frontend**: Standard HTML/CSS/JS (Three.js) for maximum visual quality.
- **Backend/Host**: Python (Streamlit) serves the content, allowing for easy cloud deployment.

## Installation / Local Run

1. Clone the repository.
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deployment
This repository is optimized for **Streamlit Community Cloud**.
- **Main file path**: `app.py`
