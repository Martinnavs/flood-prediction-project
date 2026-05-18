# Data Engineering Architecture: CHIRPS Rainfall Extraction Pipeline

## Overview
This repository contains a high-performance data engineering pipeline designed to extract, process, and aggregate historical rainfall data for all municipalities in the Philippines (ADM3 level) for the period **2022–2025**. 

The resulting dataset is engineered specifically for a machine learning model predicting **urban flood vulnerability**. It is designed to be merged with OpenStreetMap (OSM) infrastructure data, VIIRS night lights, and localized poverty metrics.

---

## 1. Data Source Selection

### Why CHIRPS Gridded Data?
The foundation of this dataset relies on the **Climate Hazards Group InfraRed Precipitation with Station data (CHIRPS)**.
* **The Problem with Station Data (NOAA GSOM):** The Philippines possess a limited number of physical synoptic weather stations. Relying on station data results in massive spatial gaps (NaN values) for the majority of municipalities.
* **The CHIRPS Advantage:** CHIRPS provides a continuous $5\text{km} \times 5\text{km}$ raster grid generated via satellite imagery calibrated with ground stations. This ensures every single ADM3 polygon receives a mathematically sound rainfall estimate with zero missing values.

### Why not PAGASA CliMap?
While the Philippine atmospheric agency (PAGASA) offers accurate data, their portal is optimized for climate change projections and long-term baselines (10-to-30-year averages). It does not provide a programmatic way to bulk-download continuous historical monthly time-series data for all 1,600+ municipalities simultaneously.

---

## 2. Pipeline Architecture

### Why the ClimateSERV API?
The pipeline was pivoted from a local raster-processing model to a server-side API model using the **NASA/SERVIR ClimateSERV API**.
* **Bandwidth Efficiency:** Instead of downloading ~1.5GB of global raster data, the pipeline offloads the heavy geospatial computation (Zonal Statistics) to NASA's clusters.
* **The API Solution:** The server calculates the spatial intersection and returns a lightweight CSV containing only the final numerical values.

### Bypassing the Official Wrapper
During development, processing complex coastal municipalities resulted in `414 URI Too Large` errors.
* **The Bug:** The official `climateserv` Python wrapper mistakenly passes spatial geometry via the URL query string.
* **The Engineering Fix:** We abandoned the package and wrote a custom Python function using the `requests` library to forcefully package the GeoJSON payload into the **HTTP POST body**. This makes the pipeline invulnerable to URL character limits.

---

## 3. Engineering Decisions

### 1. The Join Key: PSGC
Instead of municipality names, the pipeline utilizes the official **Philippine Standard Geographic Code (PSGC)** for file naming and indexing.
* **Rationale:** The Philippines has many municipalities with identical names across different provinces. Using the unique PSGC guarantees perfect, collision-free joins when merging with OSM, VIIRS, and poverty datasets.

### 2. Geometry Optimization
* **Simplification:** We apply a $0.01$ degree tolerance simplification (~1km) to the ADM3 polygons. Since CHIRPS resolution is ~5.5km, sub-meter coastline precision adds zero value but exponentially increases API failure rates.
* **Islands:** The pipeline programmatically extracts the largest single landmass by area for island municipalities to comply with API limitations.

### 3. Temporal Aggregation Strategy
* **Transformation:** The pipeline intercepts daily JSON responses and utilizes Pandas to resample the data to the start of the month (`MS`), applying a `.sum()` aggregation.
* **Rationale:** Urban flooding is driven by cumulative water volume capacity. Summing the daily spatial averages provides the physically accurate metric of total water volume that fell on the municipality that month.

### 4. Idempotency and Fault Tolerance
The script implements a strict `os.path.exists()` check. If the network drops or the session times out, the script can be re-run safely. It will skip completed municipalities and resume exactly where it stopped, ensuring zero duplicated work or API calls.
