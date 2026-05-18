# A guide in filling out the data dir

Given the size of the datasets used in the `data_extraction` transforms, we've decided to remove it from the repository and instead create a guide on how to replicate the local version of `data/`.

Use the main repo's README to locate and download the datasets used. Once downloaded, populate `data/` given the following tree structure:

```
.
└── data/
    └── ph_adm3_municities/
        └── <Paste the unzipped files of the PSGC (City/Munipality level) here>
    └── nightlight_viirs/
        └── <Paste the TIF files from Zenodo here>
    └── openstreetmap/
        └── philippines-220101-free.shp/ (this is the output of the unzipped file from Geofabrik)
        └── philippines-230101-free.shp/ (this is the output of the unzipped file from Geofabrik)
        └── philippines-240101-free.shp/ (this is the output of the unzipped file from Geofabrik)
        └── philippines-250101-free.shp/ (this is the output of the unzipped file from Geofabrik)
    └── ph_cop30_tiles/
        └── Copernicus_DSM_COG_10_N21_00_E121_00_DEM.tif
        └── ...
    └── rainfall/
        └── chirp-v3.0.2022.01.tif
        └── ...
    └── flood_control_projects/
        └── flood_control_projects.json (scraped data)
    └── groundsource.parquet <rename the Zenodo file>
    └── README.md
    └── <processed datasets>
```
