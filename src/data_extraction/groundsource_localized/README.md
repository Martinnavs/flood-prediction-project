# Data Engineering Architecture: Groundsource Urban Flood Event Processing Pipeline

## Overview
This document describes the data engineering design for processing the **Groundsource flood events dataset** into a model-ready target table for the Philippines.

The pipeline transforms raw Groundsource spatiotemporal flood observations into **city-month labels** representing **Reported Active Flood Days** for the period **2022–2025**. The resulting dataset is engineered for downstream use in the urban flood vulnerability modeling pipeline and is designed to join cleanly with rainfall, flood control, VIIRS night lights, OSM, and other municipality-level features.

This design follows the project proposal’s target definition:  
- one flood event spanning multiple dates contributes one active flood day for each calendar day in the interval  
- multiple flood records affecting the same city on the same date count as **one** active flood day  
- the final analytical grain is **city-month** using **PSGC** as the primary key :contentReference[oaicite:0]{index=0}

---

## 1. Data Source Selection

### Why Groundsource?
The target variable depends on a source that provides:
- explicit flood-event timing
- localized spatial information
- coverage across the Philippines
- sufficient recency for the 2022–2025 study window

Groundsource is suitable because it provides flood observations with:
- `start_date`
- `end_date`
- geometry
- high-volume global coverage derived from news reporting

This makes it appropriate for constructing **reported flood activity labels** at city level, especially where conventional local administrative flood archives are incomplete or not uniformly accessible.

### Why not use only disaster databases or station-based reporting?
Traditional disaster databases tend to focus on:
- severe events only
- coarser administrative geographies
- lower event counts
- inconsistent local coverage

For this project, the modeling target is not “major disaster declarations,” but **reported active flood days** at the city-month level. Groundsource is more aligned with that target because it captures localized and repeated reporting signals that are more granular than global disaster registries.

### Known limitations of Groundsource
Groundsource is not a direct physical measurement system. It is a **news-derived event archive**, so it reflects:
- reporting intensity
- language coverage
- media density
- extraction and geocoding noise

The dataset is also **entity-based rather than meteorology-based**, meaning one real-world flood may appear as several localized records if multiple affected places are mentioned separately. This is acceptable for the project, but it requires careful deduplication at the city-day level.

---

## 2. Pipeline Architecture

The pipeline is split into two logical stages:

### Stage 1: Urban city tagging and event-window preparation
This stage:
- reads the raw Groundsource parquet
- parses event dates
- restricts the data to the study period using interval overlap logic
- joins Groundsource geometries to Philippine city boundaries
- retains only urban city records
- writes an intermediate event-level table

### Stage 2: Active flood day expansion and monthly aggregation
This stage:
- reads the intermediate tagged event table
- expands each event interval into daily rows
- collapses duplicate records at the `(psgc, active_flood_day)` level
- aggregates unique active flood days to `(psgc, month_year)`

This two-stage design keeps:
- spatial attribution logic separate from
- temporal expansion and aggregation logic

That separation makes the pipeline easier to debug and safer to revise when either the geospatial or temporal assumptions change.

---

## 3. Engineering Decisions

### 1. The Join Key: PSGC
Instead of municipality or city names, the pipeline uses the official **Philippine Standard Geographic Code (PSGC)** as the primary key.

#### Rationale
Municipality and city names are not reliable join keys because:
- names can repeat across provinces
- naming conventions may vary across sources
- formatting differences can silently break merges

Using PSGC ensures:
- collision-free joins
- consistent linkage across rainfall, flood control, VIIRS, OSM, and derived target datasets
- reduced ambiguity in downstream feature engineering

City names remain in the dataset as descriptive metadata only.

---

### 2. Study Window Handling: Interval Overlap + Date Clipping
Groundsource records may partially overlap the study window even if their `start_date` falls outside it. For example, an event can begin in late December 2021 and continue into January 2022.

#### Decision
The pipeline keeps only records whose event interval overlaps the study window:

- `end_date >= 2022-01-01`
- `start_date <= 2025-12-31`

Then it clips:
- `start_date` to the lower study boundary
- `end_date` to the upper study boundary

#### Rationale
Filtering only on `start_date` would incorrectly exclude valid in-window active flood days from boundary-crossing events. Since the target is defined on **active days**, not merely event starts, interval overlap logic is the correct implementation.

This design preserves all valid city-day contributions within 2022–2025 while discarding records entirely outside the study period.

---

### 3. Spatial Attribution Rule: Geometry Intersection with City Boundaries
A Groundsource event may spatially overlap more than one adjacent city. Assigning each event to only one city via a representative point is a lossy simplification.

#### Decision
The preferred design is to spatially join **original Groundsource geometries** against Philippine city polygons using:

- `predicate="intersects"`

#### Rationale
This better matches the project’s target semantics:
- if one reported flood footprint overlaps multiple cities, each affected city should be eligible to receive that city-day flood signal
- adjacency effects are especially relevant in shared urban catchments, floodplains, or river-connected LGUs

This is more faithful than reducing the event to a single representative point and forcing a one-city assignment.

#### Tradeoff
Using `intersects` increases the number of city-event matches. This is intentional and acceptable because the pipeline later deduplicates at the **city-day** level. The true safeguard against double counting is not restrictive spatial assignment, but the downstream collapse of duplicate daily records per city.

---

### 4. Temporal Aggregation Strategy: Daily Expansion Before Monthly Rollup
Groundsource stores event windows, not precomputed day-level records.

#### Decision
Each event is expanded into one row per calendar day from `start_date` to `end_date`, inclusive. After expansion:
- duplicate rows are collapsed at `(psgc, active_flood_day)`
- the resulting unique city-days are aggregated to month-level counts

#### Rationale
This directly implements the proposal’s label definition:
- an event from July 20 to July 23 contributes four active flood days
- multiple overlapping reports in the same city on the same day count only once

This approach is easier to reason about and audit than interval arithmetic on overlapping windows.

---

### 5. Deduplication Rule: Unique City-Day
Groundsource may contain multiple rows referring to the same real-world flooding in the same city-day because:
- the dataset is entity-based
- several nearby places may be reported separately
- overlapping date ranges may exist for related local mentions

#### Decision
The canonical deduplication grain is:

- `(psgc, active_flood_day)`

#### Rationale
This is the smallest grain that aligns with the target definition while preventing overcounting from multiple overlapping event rows.

This decision intentionally allows:
- one flood event to affect multiple cities on the same date
- but prevents one city from receiving more than one active flood day for the same calendar date

---

### 6. Output Grain: City-Month Target Table
The final output of the Groundsource processing stage is a table at the grain:

- `(psgc, month_year)`

with:
- `reported_active_flood_days`

#### Rationale
This matches the target grain defined in the modeling proposal and supports clean integration with other city-month features such as:
- monthly rainfall
- lagged flood control features
- monthly or yearly proxy variables aligned to the panel

A later processing stage will expand this into a **complete city-month panel** by adding explicit zero rows for months with no reported flood activity.

---

## 4. Data Quality and Caveats

### News-derived target caveat
This target measures **reported flooding**, not directly observed hydrological flooding. It should be interpreted as a proxy influenced by:
- physical flood occurrence
- local media activity
- digital visibility
- language and coverage biases

### Boundary sensitivity
Spatial attribution depends on the administrative boundary version used for the Philippine city polygons. Any future changes in PSGC shapefiles or geometry definitions should trigger a re-run of the tagging stage.

### Entity-based duplication
Groundsource may contain several localized rows corresponding to one real-world flood. This is expected behavior and is handled by city-day deduplication rather than being treated as raw-data corruption.

---

## 5. Final Output Specification

### Final target output
**City-month active flood table**
- `psgc`
- `month_year`
- `reported_active_flood_days`
