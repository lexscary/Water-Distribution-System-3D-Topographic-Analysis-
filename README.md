# York University Water Distribution - 3D Analysis

A Streamlit application for analyzing and visualizing the topographic alignment of a water distribution pipeline.

## Features
- **3D Terrain Visualization**: Interactive surface plot of the survey area.
- **Pipeline Routing**: Visual path from Station A (T-Joint) to Station B (Reservoir).
- **Interactive Controls**: Adjust vertical exaggeration, color schemes, and layers.
- **Statistics**: Real-time calculation of pipeline slope, distance, and elevation gain.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the Streamlit application:
```bash
streamlit run streamlit_app.py
```

## Data Sources
- Topographic Survey: 715 points (IDs 1-715)
- Water Stations: A (T-Joint) & B (Reservoir)
