import streamlit as st
import json
import pandas as pd
import numpy as np
from scipy.interpolate import griddata
import plotly.graph_objects as go

# Set page config
st.set_page_config(layout="wide", page_title="3D Topographic Analysis", page_icon="⛰️")

# --- DATA LOADING ---
@st.cache_data
def load_data(filepath='topographic_data.json'):
    with open(filepath, 'r') as f:
        data = json.load(f)
    print("Data loaded successfully")
    return data

@st.cache_data
def process_mesh(points_data, resolution=50):
    # Extract coordinates
    points = points_data['points']
    
    # Filter for survey points only for terrain gen
    survey_points = [p for p in points if p.get('source') == 'topo_survey']
    
    x = [p['northing'] for p in survey_points]
    y = [p['easting'] for p in survey_points]
    z = [p['elevation'] for p in survey_points]
    
    # Create grid
    min_n, max_n = min(x), max(x)
    min_e, max_e = min(y), max(y)
    
    grid_x, grid_y = np.mgrid[
        min_n:max_n:complex(0, resolution),
        min_e:max_e:complex(0, resolution)
    ]
    
    # Interpolate using cubic method (scipy's version of IDW-like smoothness)
    grid_z = griddata(
        (x, y), 
        z, 
        (grid_x, grid_y), 
        method='cubic'
    )
    
    # Fill nan edges with nearest to prevent holes
    if np.isnan(grid_z).any():
        grid_z_nearest = griddata(
            (x, y), 
            z, 
            (grid_x, grid_y), 
            method='nearest'
        )
        grid_z = np.where(np.isnan(grid_z), grid_z_nearest, grid_z)
        
    return grid_x, grid_y, grid_z, min_n, max_n, min_e, max_e

# --- MAIN APP ---
def main():
    st.title("⛰️ York University: Water Distribution System Alignment")
    st.markdown("""
    **3D Topographic Visualization** for pipeline alignment between Station A (T-Joint) and Station B (Reservoir).
    """)

    # Load data
    try:
        data = load_data()
        metadata = data['metadata']
        bounds = metadata['bounds']
        
        # --- SIDEBAR CONTROLS ---
        st.sidebar.header("🕹️ Controls")
        
        # Exaggeration Control
        exaggeration = st.sidebar.slider("Vertical Exaggeration", 1.0, 30.0, 20.0, 1.0, 
            help="Scale elevation to make terrain features distinguishable (Default: 20x)")
            
        color_scheme = st.sidebar.selectbox("Color Scheme", 
            ["Earth", "Rainbow", "Viridis", "Jet", "Greys"], index=0)
            
        show_wireframe = st.sidebar.checkbox("Show Wireframe", False)
        show_pipeline = st.sidebar.checkbox("Show Pipeline", True)
        
        # --- STATS PANEL ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Statistics")
        st.sidebar.metric("Survey Points", metadata['survey_points'])
        
        elev_range = f"{bounds['elevation']['min']:.2f}m - {bounds['elevation']['max']:.2f}m"
        relief = f"{bounds['elevation']['max'] - bounds['elevation']['min']:.2f}m"
        st.sidebar.metric("Elevation Range", elev_range, delta=f"Relief: {relief}")
        
        # Pipeline calculations
        stations = [p for p in data['points'] if p.get('source') == 'water_dist']
        if len(stations) == 2:
            st_a = next(p for p in stations if p['station'] == 'A')
            st_b = next(p for p in stations if p['station'] == 'B')
            
            dist = np.sqrt((st_b['northing'] - st_a['northing'])**2 + (st_b['easting'] - st_a['easting'])**2)
            elev_diff = st_b['elevation'] - st_a['elevation']
            slope = (elev_diff / dist) * 100
            
            col1, col2 = st.sidebar.columns(2)
            col1.metric("Pipeline Dist", f"{dist:.1f}m")
            col2.metric("Slope", f"{slope:.2f}%")
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # --- 3D VISUALIZATION ---
    # Process Mesh
    grid_x, grid_y, grid_z, min_n, max_n, min_e, max_e = process_mesh(data)
    
    # Create Plotly Figure
    fig = go.Figure()

    # 1. Terrain Surface
    fig.add_trace(go.Surface(
        x=grid_x, 
        y=grid_y, 
        z=grid_z * exaggeration, # Apply exaggeration
        colorscale=color_scheme,
        showscale=False,
        name='Terrain',
        contours={
            "z": {"show": True, "start": 48, "end": 60, "size": 1, "color": "white", "usecolormap": False}
        },
        opacity=0.9
    ))
    
    # 2. Wireframe (Optional)
    if show_wireframe:
        fig.add_trace(go.Surface(
            x=grid_x, y=grid_y, z=grid_z * exaggeration,
            colorscale=[[0, 'black'], [1, 'black']],
            showscale=False,
            opacity=0.1,
            hidesurface=True,
            contours={'x': {'show': True}, 'y': {'show': True, 'width': 1}}
        ))

    # 3. Stations & Pipeline
    if len(stations) == 2:
        # Station Markers
        st_x = [p['northing'] for p in stations]
        st_y = [p['easting'] for p in stations]
        st_z_base = [p['elevation'] for p in stations]
        st_z_scaled = [z * exaggeration for z in st_z_base]
        st_labels = [f"Station {p['station']}: {p['description']}" for p in stations]
        
        fig.add_trace(go.Scatter3d(
            x=st_x, y=st_y, z=st_z_scaled,
            mode='markers+text',
            marker=dict(size=10, color=['cyan', 'purple'], symbol='diamond'),
            text=[f"A ({st_z_base[0]}m)", f"B ({st_z_base[1]}m)"],
            textposition="top center",
            name='Stations'
        ))
        
        # Pipeline Path (Curved)
        if show_pipeline:
            # Generate parametric curve for sag
            t = np.linspace(0, 1, 50)
            
            # Linear interpolation for X and Y
            path_x = st_x[0] + (st_x[1] - st_x[0]) * t
            path_y = st_y[0] + (st_y[1] - st_y[0]) * t
            
            # Parabolic sag for Z (simple quadratic bezier-like sag)
            # Midpoint sag logic
            z_start = st_z_base[0]
            z_end = st_z_base[1]
            z_mid = (z_start + z_end) / 2 - 1.0 # 1m sag
            
            # Bezier quadratic for Z
            # (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
            path_z = (1-t)**2 * z_start + 2*(1-t)*t * z_mid + t**2 * z_end
            path_z_scaled = path_z * exaggeration
            
            fig.add_trace(go.Scatter3d(
                x=path_x, y=path_y, z=path_z_scaled,
                mode='lines',
                line=dict(color='#ff3d9a', width=6), # Pink glowing pipe
                name='Pipeline'
            ))

    # Layout Updates
    fig.update_layout(
        title="Interactive 3D Terrain Model",
        autosize=True,
        width=1200,
        height=800,
        margin=dict(l=0, r=0, b=0, t=30),
        scene=dict(
            xaxis=dict(title='Northing (m)', showspikes=False),
            yaxis=dict(title='Easting (m)', showspikes=False),
            zaxis=dict(title=f'Elevation (x{exaggeration})', showspikes=False),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5),
                center=dict(x=0, y=0, z=-0.2)
            ),
            aspectratio=dict(x=1, y=1, z=0.4) # Flatter aspect ratio
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.caption("Generated by AI Agent | Data Source: York University Civil Engineering")

if __name__ == "__main__":
    main()
