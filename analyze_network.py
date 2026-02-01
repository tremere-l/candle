import pandas as pd
import glob
import os
import folium
from folium.plugins import HeatMap, MarkerCluster
import numpy as np
from sklearn.neighbors import BallTree

def load_data(data_dir):
    all_files = glob.glob(os.path.join(data_dir, "*.csv"))
    df_list = []
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    if not df_list:
        return pd.DataFrame()
        
    combined_df = pd.concat(df_list, ignore_index=True)
    return combined_df

def analyze_data(df):
    print("=== Network Quality Analysis ===")
    
    # Filter invalid coordinates
    # Ensure Lat/Lon are numeric
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    
    df_clean = df[
        (df['Latitude'].notna()) & 
        (df['Longitude'].notna()) & 
        (df['Latitude'] != 0) & 
        (df['Longitude'] != 0)
    ].copy()
    print(f"Total data points: {len(df)}")
    print(f"Valid location points: {len(df_clean)}")
    
    if df_clean.empty:
        print("No valid location data found.")
        return df_clean

    # Filter for Valid Signal Data (excluding placeholders)
    # Assuming -999 or extremely low values are invalid. Standard min is usually around -140.
    # Also exclude unrealistic positive values (e.g. Integer.MAX_VALUE)
    df_valid_signal = df_clean[
        (df_clean['SignalStrength_dBm'] > -150) & 
        (df_clean['SignalStrength_dBm'] < 0)
    ].copy()
    
    print(f"Valid signal points (dBm > -150): {len(df_valid_signal)}")
    print(f"Percentage of valid signal data: {len(df_valid_signal)/len(df_clean)*100:.2f}%")

    if df_valid_signal.empty:
        print("No valid signal data found for detailed analysis.")
        return df_clean, pd.DataFrame()

    # Identify "Confirmed No Signal" areas
    # Criteria: Invalid signal (-150 dBm or less) AND no valid signal points within 10 meters.
    df_invalid_signal = df_clean[df_clean['SignalStrength_dBm'] <= -150].copy()
    
    confirmed_no_signal_df = pd.DataFrame()
    
    if not df_invalid_signal.empty and not df_valid_signal.empty:
        print("\n--- Identifying Confirmed No Signal Zones (10m radius check) ---")
        
        # Convert lat/lon to radians for BallTree (requires radians)
        valid_coords = np.radians(df_valid_signal[['Latitude', 'Longitude']].values)
        invalid_coords = np.radians(df_invalid_signal[['Latitude', 'Longitude']].values)
        
        # Build tree on valid points
        tree = BallTree(valid_coords, metric='haversine')
        
        # Query radius: 10 meters. Earth radius ~ 6371000 meters.
        # Radius in radians = 10 / 6371000
        radius_radians = 10 / 6371000
        
        # query_radius returns an array of arrays of indices. 
        # count_only=True returns the count of neighbors.
        counts = tree.query_radius(invalid_coords, r=radius_radians, count_only=True)
        
        # Filter: Keep points with 0 valid neighbors
        no_signal_mask = counts == 0
        confirmed_no_signal_df = df_invalid_signal[no_signal_mask].copy()
        
        print(f"Total invalid signal points: {len(df_invalid_signal)}")
        print(f"Confirmed No Signal points (no valid signal within 10m): {len(confirmed_no_signal_df)}")
        print(f"Percentage of No Signal areas in invalid data: {len(confirmed_no_signal_df)/len(df_invalid_signal)*100:.2f}%")

    # Network Type Analysis (on valid data)
    print("\n--- Network Type Distribution (Valid Signals) ---")
    print(df_valid_signal['NetworkType'].value_counts(normalize=True).mul(100).round(2).astype(str) + '%')
    
    # Band Analysis (on valid data)
    print("\n--- Frequency Band Distribution (Valid Signals) ---")
    print(df_valid_signal['Band'].value_counts(normalize=True).mul(100).round(2).astype(str) + '%')
    
    # Signal Strength Analysis (on valid data)
    print("\n--- Signal Strength (dBm) Statistics (Valid Signals) ---")
    print(df_valid_signal['SignalStrength_dBm'].describe())
    
    return df_valid_signal, confirmed_no_signal_df

def generate_map(valid_df, no_signal_df, mode='quality', output_file='network_quality_map.html', return_map=False):
    if valid_df.empty and no_signal_df.empty:
        print(f"No data to map for {mode}.")
        return None

    # Center map on the mean of coordinates
    if not valid_df.empty:
        center_lat = valid_df['Latitude'].mean()
        center_lon = valid_df['Longitude'].mean()
        min_lat, max_lat = valid_df['Latitude'].min(), valid_df['Latitude'].max()
        min_lon, max_lon = valid_df['Longitude'].min(), valid_df['Longitude'].max()
    else:
        center_lat = no_signal_df['Latitude'].mean()
        center_lon = no_signal_df['Longitude'].mean()
        min_lat, max_lat = no_signal_df['Latitude'].min(), no_signal_df['Latitude'].max()
        min_lon, max_lon = no_signal_df['Longitude'].min(), no_signal_df['Longitude'].max()
    
    # Create Folium map (prefer_canvas=False for compatibility)
    # Start with no default tiles so we can control layers explicitly
    m = folium.Map(location=[center_lat, center_lon], prefer_canvas=False, tiles=None)
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    # Add Google Maps TileLayer (Standard)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True
    ).add_to(m)

    # Add Google Maps Satellite TileLayer
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add LayerControl to toggle base maps
    folium.LayerControl().add_to(m)

    # Helper functions
    def get_color(signal):
        if signal >= -90: return 'green'
        elif signal >= -105: return 'orange'
        else: return 'red'

    band_colors = {1: 'blue', 3: 'purple', 8: 'darkgreen', 40: 'cadetblue', 5: 'orange', -1: 'gray'}
    def get_band_color(band):
        return band_colors.get(band, 'black')

    import html

    # Downsampling
    # Increased limits significantly to show more points as requested
    MAX_VALID_POINTS = 50000 
    MAX_NO_SIGNAL_POINTS = 30000
    
    if len(valid_df) > MAX_VALID_POINTS:
        print(f"[{mode}] Downsampling Valid Signal points: {len(valid_df)} -> {MAX_VALID_POINTS}")
        valid_plot_df = valid_df.sample(n=MAX_VALID_POINTS, random_state=42)
    else:
        valid_plot_df = valid_df
        
    if not no_signal_df.empty:
        if len(no_signal_df) > MAX_NO_SIGNAL_POINTS:
            print(f"[{mode}] Downsampling No Signal points: {len(no_signal_df)} -> {MAX_NO_SIGNAL_POINTS}")
            no_signal_plot_df = no_signal_df.sample(n=MAX_NO_SIGNAL_POINTS, random_state=42)
        else:
            no_signal_plot_df = no_signal_df
    else:
        no_signal_plot_df = pd.DataFrame()

    # Plot Valid Points
    print(f"[{mode}] Adding valid signal points...")
    for idx, row in valid_plot_df.iterrows():
        # Common popup with improved styling and coordinates
        time_str = html.escape(str(row['Time']))
        type_str = html.escape(str(row['NetworkType']))
        lat_val = float(row['Latitude'])
        lon_val = float(row['Longitude'])
        
        popup_text = f"""
        <div style="min-width: 200px; font-family: sans-serif; font-size: 12px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="font-weight: bold; width: 60px; padding: 2px;">Time:</td><td style="padding: 2px;">{time_str}</td></tr>
                <tr><td style="font-weight: bold; padding: 2px;">Type:</td><td style="padding: 2px;">{type_str}</td></tr>
                <tr><td style="font-weight: bold; padding: 2px;">Band:</td><td style="padding: 2px;">{row['Band']}</td></tr>
                <tr><td style="font-weight: bold; padding: 2px;">Signal:</td><td style="padding: 2px;">{row['SignalStrength_dBm']} dBm</td></tr>
                <tr><td style="font-weight: bold; padding: 2px;">Lat:</td><td style="padding: 2px;">{lat_val:.6f}</td></tr>
                <tr><td style="font-weight: bold; padding: 2px;">Lon:</td><td style="padding: 2px;">{lon_val:.6f}</td></tr>
            </table>
        </div>
        """
        
        if mode == 'quality':
            color = get_color(row['SignalStrength_dBm'])
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=5, color=color, fill=True, fill_color=color, fill_opacity=0.7, popup=popup_text
            ).add_to(m)
        elif mode == 'bands':
            if row['Band'] == -1: continue
            color = get_band_color(row['Band'])
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=5, color=color, fill=True, fill_color=color, fill_opacity=0.7, popup=popup_text
            ).add_to(m)

    # Plot No Signal Points (Always show for context)
    if not no_signal_plot_df.empty:
        print(f"[{mode}] Adding No Signal points...")
        for idx, row in no_signal_plot_df.iterrows():
            lat_val = float(row['Latitude'])
            lon_val = float(row['Longitude'])
            
            no_signal_popup = f"""
            <div style="min-width: 200px; font-family: sans-serif; font-size: 12px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="font-weight: bold; width: 60px; padding: 2px;">Time:</td><td style="padding: 2px;">{html.escape(str(row['Time']))}</td></tr>
                    <tr><td style="font-weight: bold; padding: 2px;">Status:</td><td style="padding: 2px; color: red;">No Signal (Dead Zone)</td></tr>
                    <tr><td style="font-weight: bold; padding: 2px;">Lat:</td><td style="padding: 2px;">{lat_val:.6f}</td></tr>
                    <tr><td style="font-weight: bold; padding: 2px;">Lon:</td><td style="padding: 2px;">{lon_val:.6f}</td></tr>
                </table>
            </div>
            """
            
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=3, color='black', fill=True, fill_color='black', fill_opacity=0.5,
                popup=no_signal_popup
            ).add_to(m)

    # Legend
    legend_html = ""
    if mode == 'quality':
        legend_html = '''
         <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 160px; 
         border:2px solid grey; z-index:9999; font-size:14px; background-color:white; opacity: 0.9; padding: 10px;">
         <b>Signal Quality</b> <br>
         &nbsp; <i class="fa fa-circle" style="color:green"></i> &ge; -90 dBm <br>
         &nbsp; <i class="fa fa-circle" style="color:orange"></i> -105 to -90 <br>
         &nbsp; <i class="fa fa-circle" style="color:red"></i> &lt; -105 dBm <br>
         &nbsp; <i class="fa fa-circle" style="color:black"></i> No Signal <br>
         </div>
         '''
    elif mode == 'bands':
        legend_html = '''
         <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; height: 180px; 
         border:2px solid grey; z-index:9999; font-size:14px; background-color:white; opacity: 0.9; padding: 10px;">
         <b>Frequency Bands</b> <br>
         &nbsp; <i class="fa fa-circle" style="color:purple"></i> Band 3 (1800) <br>
         &nbsp; <i class="fa fa-circle" style="color:blue"></i> Band 1 (2100) <br>
         &nbsp; <i class="fa fa-circle" style="color:cadetblue"></i> Band 40 (2300) <br>
         &nbsp; <i class="fa fa-circle" style="color:darkgreen"></i> Band 8 (900) <br>
         &nbsp; <i class="fa fa-circle" style="color:orange"></i> Band 5 (850) <br>
         &nbsp; <i class="fa fa-circle" style="color:black"></i> No Signal <br>
         </div>
         '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    if return_map:
        return m
        
    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    data_directory = "/Users/tremere/PycharmProjects/signal_visual/signal_data/"
    df = load_data(data_directory)
    if not df.empty:
        valid_df, no_signal_df = analyze_data(df)
        print("\\n--- Generating Quality Map ---")
        generate_map(valid_df, no_signal_df, mode='quality', output_file='network_quality_map.html')
        print("\\n--- Generating Bands Map ---")
        generate_map(valid_df, no_signal_df, mode='bands', output_file='network_bands_map.html')
    else:
        print("No data found.")