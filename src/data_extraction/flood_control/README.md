# Technical Design Document: National Flood Control Projects (FCP) Feature Extraction Pipeline

## 1. Overview and Engineering Objectives

This document establishes the official technical design, data lineage, and feature engineering rules for processing the Philippine government's Flood Control Projects (FCP) dataset. The pipeline converts unstructured, tabular administrative records of completed civil infrastructure into an analytically sound, multi-dimensional spatiotemporal panel dataset matching the project boundaries (2022–2025 longitudinal study of urban areas).

The structural goals are:

1. **Relational Harmonization:** Map variable bureaucratic location descriptions onto official Philippine Standard Geographic Code (PSGC) `adm3_psgc` keys using optimized string matching.
2. **Feature Extraction:** Translate unstructured text definitions into binary indicators representing engineered characteristics (Interventions, Infrastructure Assets, Protected Entities, and Waterbody Typologies).
3. **Temporal Aggregation:** Transform sparse completion logs into continuous chronological lookbacks on a quarterly grid spacing (3-Month, 6-Month, 9-Month, and 1-Year historical rolling window totals) optimized for target modeling against `Groundsource` active flood days.

---

## 2. Pipeline Execution Schema

The pipeline is split into three decoupled steps to maximize data transparency, preserve raw diagnostic trails, and prevent memory allocation overflows:

```
[ flood_control_projects.json ]
              │
              ▼
   ┌──────────────────────┐
   │    Notebook 1:       │ ──► Parse nested JSON properties into flat format.
   │  Raw JSON Extract    │     Isolate administrative / timestamp outliers.
   └──────────────────────┘
              │
              ▼
    [ flood_control_raw.csv ]
              │
              ▼
   ┌──────────────────────┐
   │    Notebook 2:       │ ──► Execute string remapping & fuzzy string joins
   │  PSGC City Alignment │     against official ADM3 boundary lists.
   └──────────────────────┘     Isolate to urban centers (geo_level == "City").
              │
              ▼
  [ flood_control_per_city.csv ]
              │
              ▼
   ┌──────────────────────┐
   │    Notebook 3:       │ ──► Execute text mining & keyword classification.
   │ Rollup & Sliding Lags│     Construct quarterly lookup-grid panels with
   └──────────────────────┘     de-fragmented rolling windows.
              │
              ▼
[ urban_flood_control_projects.csv ]

```

---

## 3. Data Integration and Fuzzy PSGC Alignment

The raw procurement dataset records regional variables via unstructured flat text strings (e.g., `MUNTINLUPA CITY`, `CITY OF ALAMINOS (PANGASINAN)`). To bind this dataset cleanly to secondary data blocks (such as `ClimateSERV` weather indicators and nighttime lights), coordinates are replaced with strict relational joins via uniform regional alphanumeric numbers (`adm3_psgc`).

### Harmonization Rules and Pipeline Guards:

* **Fuzzy Pass-1 Iteration:** The system generates a comprehensive cross-product space of all active city-level combinations, comparing raw columns using string similarity algorithms.
* **Fuzzy Pass-2 Normalization:** Outlying patterns where strings prefix or suffix text titles unevenly are cleaned via sub-string stripping:
```python
def get_muni_similarity_score_pass2(muni_str_1: str, muni_str_2: str) -> float:
    muni_str_1 = muni_str_1.replace("city of ", "").replace(" city", "")
    muni_str_2 = muni_str_2.replace("city of ", "").replace(" city", "")
    return Levenshtein.jaro_winkler(muni_str_1, muni_str_2)

```


* **Explicit Exclusion Scopes:** Areas tagged as Municipalities are dropped out of the grid context during joining. For instance, **Pateros** is programmatically flagged and excluded from the output panel. This aligns with the target criteria: focusing the study on urban hubs where news tracking metrics show high visibility.

---

## 4. NLP Feature Extraction Rubric

To capture architectural variations across mitigation structures, the pipeline screens unified descriptions via text mining. Parentheses within patterns are structured as non-capturing groups `(?:...)` to optimize string evaluation and clear memory warning logs:

### 1. Action / Intervention Types

* **`action_construction`**: `construct`
* **`action_rehabilitation`**: `rehab|restor|retrofit`
* **`action_repair`**: `repair`
* **`action_improvement`**: `improv|upgrad`
* **`action_extension`**: `exten|continu`

### 2. Infrastructure Asset Category

* **`asset_drainage_system`**: `drainage|catch basin|box culvert`
* **`asset_slope_protection`**: `slope protection|rockfall|soil nailing`
* **`asset_bank_protection`**: `bank protection|revetment|gabion`
* **`asset_linear_canal`**: `line canal|lined canal|earth canal|open canal`
* **`asset_dike_levee`**: `dike|levee`
* **`asset_coastal_defense`**: `seawall|breakwater|coastal`
* **`asset_active_control`**: `pumping station|floodgate|sluice gate|pump`

### 3. Protected Entities

* **`protects_roadway`**: `\b(?:highway|road|avenue|street|st\.|blvd|boulevard|daang)\b`
* **`protects_education`**: `school|university|college|campus`
* **`protects_residential`**: `home|village|subdivision|housing|residen`
* **`protects_agricultural`**: `\bcis\b|farm|irrig`

### 4. Water Body Typology

* **`waterbody_river`**: `river`
* **`waterbody_creek`**: `creek|estero|stream`
* **`waterbody_coastal`**: `\b(?:sea|bay|gulf|coast|shore)\b`
* **`waterbody_urban_runoff`**: Activated dynamically if no natural water feature is mentioned but local drainage patterns or roadways are present:
```python
# Derived Rule
((waterbody_river == 0) & (waterbody_creek == 0) & (waterbody_coastal == 0) & 
 ((asset_drainage_system == 1) | (protects_roadway == 1)))

```



---

## 5. Strategic Categorization of Costs

Raw contract investments vary significantly across thousands of transactions (ranging from short canal repairs to massive shoreline defenses). This scale variation can destabilize distance-based or regularized estimators (like Gaussian Process Regression) during modeling.

Furthermore, direct contract sums reported across multi-phase records run a high risk of double-counting. To counter these data scale issues, investment parameters are categorized into categorical tiers:

$$\text{Tier} = \begin{cases}
\text{Micro} & \le 5\text{M PHP} \
\text{Small} & > 5\text{M and } \le 20\text{M PHP} \
\text{Medium} & > 20\text{M and } \le 100\text{M PHP} \
\text{Large} & > 100\text{M PHP}
\end{cases}$$

Once binned, fields are one-hot encoded and rolled up using sequential sums. This turns cost parameters into a **Project Volume Count per Tier**. This setup captures structural weights without distorting model inputs with extreme values or double-counting overlapping project records.