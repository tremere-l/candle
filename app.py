import streamlit as st
import pandas as pd
import analyze_network
import streamlit.components.v1 as components
import numpy as np
from datetime import timedelta

# Set page config
st.set_page_config(layout="wide", page_title="Signal Visualizer")

st.title("Network Signal Visualization Tool")

# Sidebar for file upload
st.sidebar.header("Upload Data")
uploaded_files = st.sidebar.file_uploader("Upload CSV Signal Data", accept_multiple_files=True, type=['csv'])

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using NumPy for vectorization.
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

if uploaded_files:
    with st.spinner("Loading and Analyzing Data..."):
        # Load data from uploaded files
        df_list = []
        total_duration_seconds = 0
        total_distance_km = 0
        
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Pre-process for metrics (Per file to avoid gap issues)
                # 1. Clean Coordinates
                df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
                df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
                df_clean = df.dropna(subset=['Latitude', 'Longitude'])
                df_clean = df_clean[(df_clean['Latitude'] != 0) & (df_clean['Longitude'] != 0)]
                
                if not df_clean.empty:
                    # 2. Handle Time
                    # Try parsing time - assuming standard format, allow inference
                    df_clean['Time'] = pd.to_datetime(df_clean['Time'], errors='coerce')
                    df_clean = df_clean.dropna(subset=['Time']).sort_values('Time')
                    
                    if not df_clean.empty:
                        # Calculate Duration for this file
                        start_time = df_clean['Time'].iloc[0]
                        end_time = df_clean['Time'].iloc[-1]
                        duration = (end_time - start_time).total_seconds()
                        total_duration_seconds += duration
                        
                        # Calculate Distance for this file
                        lats = df_clean['Latitude'].values
                        lons = df_clean['Longitude'].values
                        
                        # Vectorized distance calculation between consecutive points
                        if len(lats) > 1:
                            dists = calculate_haversine_distance(
                                lats[:-1], lons[:-1], 
                                lats[1:], lons[1:]
                            )
                            total_distance_km += np.sum(dists)

                df_list.append(df)
            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
        
        if df_list:
            combined_df = pd.concat(df_list, ignore_index=True)
            
            # Run Analysis
            valid_df, no_signal_df = analyze_network.analyze_data(combined_df)
            
            # Format Duration
            total_duration_str = str(timedelta(seconds=int(total_duration_seconds)))
            
            # Display Statistics
            st.subheader("Signal Statistics")
            
            # Row 1: Basic Counts
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(combined_df))
            with col2:
                st.metric("Valid Signal Points", len(valid_df))
            with col3:
                st.metric("Dead Zones (Confirmed)", len(no_signal_df))
            with col4:
                 if not valid_df.empty:
                    avg_signal = valid_df['SignalStrength_dBm'].mean()
                    st.metric("Avg Signal (dBm)", f"{avg_signal:.2f}")
                 else:
                    st.metric("Avg Signal (dBm)", "N/A")

            # Row 2: Cumulative Metrics
            col5, col6, col7, col8 = st.columns(4)
            with col5:
                st.metric("Total Duration", total_duration_str)
            with col6:
                st.metric("Total Distance", f"{total_distance_km:.2f} km")
            with col7:
                # Placeholder for potential future metric
                pass
            with col8:
                pass

            # Basic Charts
            if not valid_df.empty:
                st.subheader("Data Distribution")
                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    st.write("**Network Type Distribution**")
                    net_type_counts = valid_df['NetworkType'].value_counts()
                    st.bar_chart(net_type_counts)
                
                with chart_col2:
                    st.write("**Frequency Band Distribution**")
                    band_counts = valid_df['Band'].value_counts()
                    st.bar_chart(band_counts)

            # Tabs for Maps
            st.subheader("Interactive Maps")
            tab1, tab2 = st.tabs(["Signal Quality Map", "Frequency Bands Map"])
            
            # Map rendering function to avoid code duplication
            def render_map(mode, height=700):
                m = analyze_network.generate_map(valid_df, no_signal_df, mode=mode, return_map=True)
                if m:
                    # Get HTML representation of the map
                    map_html = m.get_root().render()
                    components.html(map_html, height=height)
                else:
                    st.warning(f"Could not generate {mode} map (no data).")

            with tab1:
                st.write("Displays signal strength (Green=Good, Orange=Fair, Red=Poor) and Dead Zones (Black).")
                render_map('quality')
            
            with tab2:
                st.write("Displays frequency bands used (Colors per band) and Dead Zones (Black).")
                render_map('bands')
        else:
            st.warning("No valid CSV files uploaded.")

else:
    # Instructions when no file is uploaded
    st.info("Please upload CSV files from the sidebar to start analysis.")
    st.markdown("""
    ### How to use
    1. Click **Browse files** in the sidebar.
    2. Select one or more CSV files containing signal data.
    3. The application will automatically combine them, analyze signal quality, and generate interactive maps.
    
    ### Expected Data Format
    The CSV files should contain columns such as:
    - `Latitude`, `Longitude`: GPS coordinates
    - `SignalStrength_dBm`: Signal strength in dBm
    - `NetworkType`: e.g., LTE, 5G
    - `Band`: Frequency band identifier
    - `Time`: Timestamp
    """)
