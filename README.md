## Data sources

| Main dataset name | Dataset source | Link |
|---|---|---|
| Philippine PSGC (City/Municipality Level) | Github | https://github.com/altcoder/philippines-psgc-shapefiles |
| PH Flood Control Projects | Sumbong sa Pangulo dashboard | https://sumbongsapangulo.ph/flood-control-map |
| Groundsource | Zenodo (v1) | https://zenodo.org/records/18647054 |
| 2022-2024 VIIRS Nightlights* | Zenodo (v0.4) | https://zenodo.org/records/17294744 |
| 2022-2025 OSM data* | Geofabrik | https://download.geofabrik.de/asia/philippines.html# |
| 2022-2025 Monthly rainfall data (except 2024-10 and -11) | CHIRPS v3 | https://data.chc.ucsb.edu/products/CHIRP-v3.0/monthly/global/tifs/ |
| 2024-10 and -11 Monthly rainfall data | CHIRPS v2 | https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/ |
| TWI base data | Copernicus DSM | COP 30 S3 Bucket (see note below) |

For those with `*`, the following files were downloaded:
- VIIRS Nightlights
    - nightlights.average_viirs.v21_m_500m_s_20220101_20221231_go_epsg4326_v20250904.tif
    - nightlights.average_viirs.v21_m_500m_s_20230101_20231231_go_epsg4326_v20250904.tif
    - nightlights.average_viirs.v21_m_500m_s_20240101_20241231_go_epsg4326_v20250904.tif
    - nightlights.pc1_viirs.v21_m_500m_s_20110101_20241231_go_epsg4326_v20251006.tif
    - nightlights.pc2_viirs.v21_m_500m_s_20110101_20241231_go_epsg4326_v20251006.tif
- OSM data
    - philippines-220101-free.shp.zip
    - philippines-230101-free.shp.zip
    - philippines-240101-free.shp.zip
    - philippines-250101-free.shp.zip

For the TWI base data:

- download the Copernicus DEM tiles for **N04-N21** and **E116-E127** using `aws_download.sh`
- the script writes the `.tif` files into `data/ph_cop30_tiles/`.
- after download, build the VRT from inside the tiles folder so that `generate_dem_vrt.sh` can see the `.tif` files

Example:

```bash
cd ph_cop30_tiles
bash aws_download.sh
bash generate_dem_vrt.sh
```

This should produce `philippines_master.vrt` inside `ph_cop30_tiles/`.

If these helper scripts live at the repository root, do **not** refer to them as `src/data/ph_cop30_tiles/aws_download.sh`; update the path in the repo docs to their real location.
