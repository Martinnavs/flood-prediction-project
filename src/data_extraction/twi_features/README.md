## TWI processing notebooks

The TWI workflow is split into three notebooks. The core process has not changed; these notebooks now make the validation intent more explicit.

### `0_dataset_validation.ipynb`

Purpose:
- perform a **visual completeness check** for the downloaded Copernicus DEM tiles

What it does:
- loads the available COP30 `.tif` tiles
- builds a merged visualization
- plots the resulting mosaic to confirm that the downloaded tiles form a plausible Philippines-wide footprint

What this validates:
- the DEM tiles are present and readable
- the downloaded set visually covers the Philippines as expected

What this does **not** validate:
- exact tile inventory completeness against the target grid
- downstream TWI correctness
- VRT correctness

Use this notebook as a **sanity check**, not as a full integrity audit.

---

### `1_processing_twi_per_city.ipynb`

Purpose:
- generate **one final TWI raster per city**

What it does:
- loads city boundaries
- extracts a buffered DEM window per city from the master VRT
- runs the hydrology workflow to derive TWI
- clips the result back to the exact city boundary
- writes one `{psgc}_final_twi.tif` output per city

Validation approach:
- this notebook is treated as a **one-off processing notebook**
- after generation, a validation cell checks for potential output issues and displays only problematic rows

Current validation checks include:
- missing output file
- raster cannot be opened
- zero width or height
- raster is entirely nodata

This notebook is meant to confirm:
- every expected city has a corresponding final TWI raster
- the output rasters are minimally valid as raster artifacts

---

### `2_creating_urban_twi_metrics.ipynb`

Purpose:
- convert per-city final TWI rasters into a single **urban TWI metrics table**

What it does:
- reads each city’s final TWI raster
- computes summary statistics per city
- writes a city-level metrics table with:
  - `mean_twi`
  - `max_twi`
  - `std_twi`

Validation approach:
- after extraction, a validation DataFrame is built
- only potential problem rows are shown

Current validation checks include:
- missing raster file
- raster cannot be opened
- zero width or height
- raster is entirely nodata
- missing metrics row
- null summary statistics
- invalid standard deviation values

This notebook is meant to confirm:
- every expected city has a metrics row
- the exported urban TWI metrics are complete enough for downstream use

---

#### Notes

- `0_` is a **visual coverage check**
- `1_` is a **one-off raster generation notebook**
- `2_` is a **one-off metrics materialization notebook**
- the underlying TWI process remains the same; the main improvement is stronger validation around outputs

## Data Engineering Design Document: Geospatial Feature Extraction Pipeline

## 1. Objective
To build an automated, memory-efficient, and idempotent data engineering pipeline that extracts hydrologically sound Topographic Wetness Index (TWI) and other satellite-derived metrics (e.g., Nightlights) for Philippine municipalities. This pipeline generates tabular Machine Learning features at the administrative (barangay/city) level for an AI 221 flood vulnerability model.

## 2. Core Technologies
* **Geospatial Engine:** GDAL (specifically `gdalbuildvrt`, `gdalwarp`)
* **Hydrological Modeling:** WhiteboxTools (Rust-based)
* **Vector Processing:** GeoPandas / Shapely
* **Raster Processing:** Rasterio, `rasterstats`, `rioxarray`
* **Data Manipulation:** Pandas / NumPy

---

## 3. Key Architectural Decisions

### 3.1. Master VRT (Virtual Raster) over Physical Mosaics
* **Decision:** We consolidate the downloaded 30m Copernicus DEM tiles using a Virtual Raster (`.vrt`) instead of merging them into a single massive `.tif` file.
* **Rationale:** A master `.tif` for the Philippines would exceed standard memory limits and storage efficiency. The VRT acts as a lightweight, zero-memory XML index, allowing GDAL to lazy-load only the required pixels for specific cities on demand.

### 3.2. Bounding Box Extraction over Vector Cutlines
* **Decision:** We use GDAL (`gdalwarp -te`) to extract a rectangular bounding box from the VRT, rather than using the exact city boundaries (`-cutline`) for the initial DEM extraction.
* **Rationale:** 1. WhiteboxTools operates fundamentally on raster grids. Feeding it a jagged, irregular polygon creates void spaces that waste CPU cycles.
    2. Buffering a complex polygon in GeoPandas often creates self-intersecting geometries that cause `gdalwarp` to fail silently. Bounding boxes are mathematically stable.

### 3.3. The Hydrological Buffer (Edge-Effect Mitigation)
* **Decision:** We buffer the target city by `0.05` degrees (~5.5km) before extracting the DEM, calculate the TWI, and then precisely trim the result back to the original city borders.
* **Rationale:** Hydrological models (like Flow Accumulation) must know about the surrounding topology. If we clip exactly to the city borders first, water flowing from mountains just outside the city limits would be ignored, creating artificial "dams" at the edges of the dataset and ruining the TWI calculations. 

### 3.4. Absolute Paths for Cross-Language Tooling
* **Decision:** All temporary and final file paths are coerced into absolute system paths using `os.path.abspath()`.
* **Rationale:** WhiteboxTools relies on a compiled Rust executable called by a Python wrapper. Relative paths (like `../../data/`) are evaluated differently by the Rust binary than by the Python kernel, leading to `os error 2: No such file or directory`. Absolute paths guarantee strict file resolution across languages.

### 3.5. Universal Feature Extractor (DRY Principle)
* **Decision:** Zonal statistics are extracted using a single, abstracted function (`extract_raster_stats`) rather than hardcoding separate functions for TWI and Nightlights.
* **Rationale:** Ensures the codebase remains DRY (Don't Repeat Yourself). The function dynamically reads the `CRS` and `NoData` flags from the input raster, making it instantly compatible with any future satellite data added to the project.

### 3.6. Memory Optimization: The "List Accumulator" Pattern
* **Decision:** Inside the municipality iteration loop, we store GeoDataFrame chunks in a Python `list` and perform a single `pd.concat()` outside the loop.
* **Rationale:** Using `pd.concat` or `append` inside a loop is a known Pandas anti-pattern. It causes exponential memory fragmentation as Pandas creates a new object and copies the entire dataset on every iteration. The list accumulator reduces memory overhead to near zero during the loop.

---

## 4. Pipeline Execution Flow

The standard execution flow for a given municipality (`psgc_code`) follows these steps:

1.  **Initialize:** Create absolute paths for temporary processing files.
2.  **Buffer & Bound:** Filter the target city from the administrative GeoDataFrame, buffer it by 0.05 degrees, and calculate the rectangular bounding box (`total_bounds`).
3.  **Smart Clip (GDAL):** Extract the buffered DEM rectangle from the Master VRT using `gdalwarp` (with `-overwrite` for idempotency).
4.  **Hydrology Math (WBT):** * `FillDepressions` (Removes digital artifacts).
    * `Slope` (Calculates gradient).
    * `D-Infinity Flow Accumulation` (Calculates upstream water contribution).
    * `Wetness Index` (Combines Flow and Slope into TWI).
5.  **Precision Trim:** Use `rioxarray` to clip the buffered TWI raster back to the exact administrative boundaries of the city.
6.  **Zonal Stats:** Pass the final TWI raster (and any other rasters like Nightlights) into the universal extractor to calculate `mean`, `max`, and `std` per barangay.
7.  **Cleanup:** Ensure all temporary `.tif` and `.geojson` files are deleted via a `finally` block to prevent disk bloat.



