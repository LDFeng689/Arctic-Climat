import xarray as xr
import numpy as np
import os
from datetime import datetime

era5_path = "Data&Model/ERA5/71082/era5_71082_monthly.nc"
radio_path = "Data&Model/Radiosonde/NC/71082_monthly.nc"

for label, path in [("ERA5", era5_path), ("Radiosonde", radio_path)]:
    print(f"\n{'='*60}")
    print(f"  {label} SBI Trends Table")
    print(f"  File: {path}")
    print(f"{'='*60}")
    
    ds = xr.open_dataset(path)
    
    # Check available variables
    trend_vars = [v for v in ds.data_vars if 'trend' in v.lower()]
    print(f"  Trend variables found: {trend_vars}")
    print(f"  Coordinates: {list(ds.coords)}")
    print(f"  month_hour values: {ds.month_hour.values if 'month_hour' in ds.coords else 'N/A'}")
    
    # Group by month_hour (same logic as trend_table function)
    groupTrend = ds.groupby(ds.month_hour)
    timeKey3 = list(groupTrend.groups.keys())
    sub_data3 = [sub_ds for _, sub_ds in groupTrend]
    timeName3 = [f"{datetime.strptime(key, '%m-%H').strftime('%B %H')} UTC" for key in timeKey3]
    
    print(f"  Column labels: {timeName3}")
    
    freqTrend = [sub_ds["frequency_trend"].values for sub_ds in sub_data3]
    strengthTrend = [sub_ds["strength_trend"].values for sub_ds in sub_data3]
    depthTrend = [sub_ds["depth_trend"].values for sub_ds in sub_data3]
    intensityTrend = [sub_ds["intensity_trend"].values for sub_ds in sub_data3]
    
    row_labels = [
        "Frequency Trend (decade^-1)",
        "Strength Trend (K decade^-1)",
        "Depth Trend (m decade^-1)",
        "Intensity Trend (K m^-1 decade^-1)",
    ]
    
    data_matrix = np.array([
        [np.squeeze(val) for val in freqTrend],
        [np.squeeze(val) for val in strengthTrend],
        [np.squeeze(val) for val in depthTrend],
        [np.squeeze(val) for val in intensityTrend],
    ])
    
    print(f"\n  Data matrix shape: {data_matrix.shape}")
    print(f"\n  {'Column':<30}", end="")
    for col in timeName3:
        print(f"  {col:>18}", end="")
    print()
    print(f"  {'-'*30}", end="")
    for _ in timeName3:
        print(f"  {'-'*18}", end="")
    print()
    
    for i, row_label in enumerate(row_labels):
        print(f"  {row_label:<30}", end="")
        for j in range(len(timeName3)):
            val = data_matrix[i, j]
            if isinstance(val, (float, np.floating, np.float32, np.float64)):
                if np.isnan(val):
                    print(f"  {'NaN':>18}", end="")
                else:
                    print(f"  {float(val):>18.4f}", end="")
            else:
                print(f"  {str(val):>18}", end="")
        print()
    
    ds.close()
    
    # Also print raw values for verification
    print(f"\n  --- Raw Values ---")
    for i, row_label in enumerate(row_labels):
        vals = data_matrix[i]
        print(f"  {row_label}: {vals.tolist()}")
