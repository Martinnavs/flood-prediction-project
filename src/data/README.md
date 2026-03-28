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
    └── groundsource.parquet <rename the Zenodo file>
    └── README.md
    └── <processed datasets>
```
