import geopandas as gpd
import pandas as pd
import rasterio
import os

from rasterstats import zonal_stats

def extract_raster_stats(
    gdf: gpd.GeoDataFrame,
    raster_path: str,
    feature_name: str,
    time_suffix: str = None
) -> gpd.GeoDataFrame:
    """
    Universal function to extract zonal statistics from any raster 
    and bind them to a GeoDataFrame.
    """
    print(f"Processing {os.path.basename(raster_path)}...")

    # Get the CRS and NoData of the raster
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        raster_nodata_val = src.nodata
        print(f" -> CRS: {raster_crs} | NoData: {raster_nodata_val}")
    
    # 2. Reproject polygons to match raster (use a temp copy for the math)
    _gdf = gdf.to_crs(raster_crs)
    
    # 3. Run Zonal Statistics
    stats = zonal_stats(
        vectors=_gdf, 
        raster=raster_path,
        stats=['mean', 'max', 'std'], 
        nodata=raster_nodata_val,
        all_touched=True  
    )
    
    # 4. Construct the column suffix
    col_suffix = f"_{feature_name}_{time_suffix}" if time_suffix else f"_{feature_name}"

    # 5. Bind data safely (handling None values)
    # We apply this to the ORIGINAL gdf, so its CRS remains unchanged for mapping later
    gdf[f'mean{col_suffix}'] = [x['mean'] if x['mean'] is not None else np.nan for x in stats]
    gdf[f'max{col_suffix}']  = [x['max']  if x['max']  is not None else np.nan for x in stats]
    gdf[f'std{col_suffix}']  = [x['std']  if x['std']  is not None else np.nan for x in stats]
    
    return gdf