# Technical Design Document: OpenStreetMap Feature Engineering Pipeline

**Project Context:** Feature extraction pipeline for the urban flood vulnerability prediction model.
**Core Tooling:** `geopandas`, `geowrangler` (Thinking Machines)
**Data Source:** OpenStreetMap (OSM) regional extracts via Geofabrik.

---

## 1. Spatial Aggregation Methodology (The Hybrid Zonal Stats Approach)

The primary architectural decision in this pipeline is the bifurcated use of Geowrangler's spatial aggregation modules. To balance computational throughput with geometric accuracy across administrative boundaries (PSGC), we implemented a hybrid approach based on the library's internal mechanics.

### 1.1 Vector Zonal Stats (`geowrangler.vector_zonal_stats`)
* **Target Layers:** Points of Interest (POIs), Buildings, Waterways.
* **Mechanism:** Utilizes spatial joins (`overlap_method="intersects"`) to evaluate boundary overlaps.
* **Rationale:** Spatial joins are highly performant. The Thinking Machines (TM) Poverty Mapping application utilizes this exact method (`vzs.create_zonal_stats`) for counting POIs within household cluster buffers.
* **Trade-off Acceptance:** While a spatial join assigns the full metric value of a feature (e.g., a building's area or a river's length) to all boundaries it touches, buildings and waterways are sufficiently small or linear that edge-case duplication is statistically negligible for the flood model.

### 1.2 Area Zonal Stats (`geowrangler.area_zonal_stats`)
* **Target Layers:** Landuse (Gray Zones and Green Zones).
* **Mechanism:** Executes a strict geometric overlay (`aoi.overlay(data, keep_geom_type=True)`) to calculate the exact `intersect_area` of overlapping polygons.
* **Rationale:** Large continuous polygons, such as regional forests or sprawling commercial districts, frequently straddle multiple PSGC boundaries. Using a simple spatial join would massively inflate coverage metrics by double-counting these large areas. The `area_zonal_stats` module calculates exact proportions (`pct_data` and `pct_aoi`) to apportion area correctly, providing an accurate, uninflated footprint of permeable vs. impermeable surfaces.

---

## 2. Coordinate Reference System (CRS) Selection

Accurate spatial measurements require a planar, metric Coordinate Reference System. Geowrangler explicitly validates this; passing a geographic CRS (like WGS 84 / EPSG:4326) into `azs.validate_area_data()` triggers a `ValueError` to prevent incorrect area computations. This is also strictly enforced in distance calculations.

* **TM Demo Approach:** The TM Poverty Mapping notebook projects geometries to **EPSG:3123** (PRS92 / Philippines Zone 3) before executing buffer and distance operations.
* **Our Pipeline Decision (EPSG:32651):** We cast all datasets to **EPSG:32651** (WGS 84 / UTM zone 51N).
    * *Why we diverged:* While EPSG:3123 is highly accurate for specific central regions in the Philippines, EPSG:32651 is a universally standard UTM zone that provides contiguous, robust coverage across the archipelago. It ensures our square meter ($m^2$) and linear meter ($m$) metrics remain stable and comparable whether we are modeling urban flooding in Metro Manila, Cebu, or Davao.

---

## 3. Feature Classification (`fclass`) Selection

To construct inputs for the hazard-exposure-vulnerability framework, we filtered raw OSM shapefiles into semantic groupings. OpenStreetMap encodes feature types in lowercase strings, necessitating exact string matching.

### 3.1 Resilience Proxies (Vulnerability / Coping Capacity)
* **Selected `fclass`:** `school`, `bank`, `supermarket`, `mall`, `hospital`.
* **Justification:** Following the TM Poverty Mapping methodology, the density of these specific economic and critical infrastructure POIs serves as a proxy for regional wealth and structural development. In a disaster response context, higher densities indicate higher community coping capacity and quicker recovery potential.

### 3.2 Hydrological Hazards
* **Large Waterways:** `river`. Represents primary, regional flood sources.
* **Small Waterways:** `stream`, `canal`, `drain`. Represents secondary, localized drainage networks. Differentiating these allows the model to separate major riverine flooding from urban flash floods caused by insufficient or clogged drainage capacity.

### 3.3 Urban Permeability (Runoff vs. Infiltration)
* **Gray Zones (Impermeable):** `residential`, `industrial`, `commercial`, `retail`. These land uses define the "concrete footprint" of a PSGC. Grouping them accurately captures surfaces that accelerate surface runoff and peak discharge during heavy rainfall events.
* **Green Zones (Permeable):** `forest`, `grass`, `park`, `meadow`, `scrub`. These classifications identify natural retention areas that absorb rainfall, acting as essential environmental buffers against urban inundation.

---

## 4. Technical Safeguards

**StringDType Mitigation:** Modern versions of Pandas introduce `StringDtype`, which frequently clashes with `geopandas` spatial joins that expect traditional NumPy objects. As a design standard, all `fclass` columns are explicitly cast using `.astype(object)` prior to entering the Geowrangler aggregation chain, ensuring pipeline stability during parallel execution.