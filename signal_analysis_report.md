# Local Network Signal Quality Analysis Report

**Date**: 2026-01-21
**Data Source**: `/Users/tremere/PycharmProjects/signal_visual/signal_data/`
**Data Status**: Cleaned (Duplicates Removed)

## 1. Executive Summary
The local network environment remains exclusively **4G LTE**. The analysis of the expanded and cleaned dataset reveals a more complex coverage picture. While the average signal quality for connected points is **Good to Fair** (-93.5 dBm), there is a significant identification of **potential coverage gaps**, with **8.57%** of the tracking path lacking valid signal data within a 10-meter radius. **Band 40 (2300 MHz)** has emerged as the dominant frequency band, indicating a reliance on high-capacity TDD layers.

## 2. Data Quality Overview
*   **Total Data Points**: 379,022
*   **Valid Location Points**: 330,452 (87.2%)
*   **Valid Signal Samples**: 3,341 (1.01%)
    *   *Note*: The valid signal ratio remains low, consistent with the "background logging" limitations discussed previously. However, the sheer volume of data allows for statistical significance.

## 3. Network Technology & Coverage
*   **Network Type**: **100% 4G LTE**
*   **Coverage Analysis**:
    *   **Confirmed No Signal Zones**: **28,047 points** (8.57% of invalid data).
    *   Unlike the previous smaller dataset, the full dataset reveals distinct areas where no valid signal was recorded within a 10-meter radius. These points are marked in **Black** on the map and may represent actual dead zones, deep indoor areas, or extended periods of modem dormancy.

## 4. Frequency Band Distribution
The network utilizes five distinct LTE frequency bands. Band 40 is now the primary carrier.

| Band | Frequency | Share (Normalized) | Role |
| :--- | :--- | :--- | :--- |
| **Band 40** | 2300 MHz | **34.81%** | **Dominant Capacity Layer**. High-speed TDD layer, likely carrying the bulk of data traffic. |
| **Band 3** | 1800 MHz | **21.76%** | **Core Layer**. Balanced coverage and capacity. |
| **Band 1** | 2100 MHz | **19.37%** | **Capacity Layer**. Supplementary capacity in urban areas. |
| **Band 8** | 900 MHz | **1.77%** | **Coverage Layer**. Low frequency for deep penetration. |
| **Band 5** | 850 MHz | **0.15%** | **New Detection**. Very low usage, possibly roaming or specific localized deployment. |
| *Unknown* | *N/A* | *22.15%* | *Band information unavailable in logs.* |

## 5. Signal Strength Statistics
*   **Average Signal**: **-93.49 dBm** (Good)
*   **Median Signal**: **-93.00 dBm**
*   **Range**:
    *   Max (Best): **-60 dBm**
    *   Min (Worst): **-131 dBm** (Critical/Disconnect)

## 6. Visualization
An updated interactive map has been generated:
*   **File**: `network_quality_map.html`
*   **Updates**:
    *   **Black Markers**: Now visible on the map, indicating "Confirmed No Signal" zones where coverage data is completely absent within 10 meters.
    *   **Band 5**: Added to the dataset (though rare).
    *   **Performance**: Map contains significantly more data points (~31k plotted points).
