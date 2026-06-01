import xarray as xr
import numpy as np
import os
from scipy import stats

def find_inversion_depth_intensity(dataset):
    # 1. Create the lightweight container for your final Xarray output
    results = xr.Dataset(
        coords={
            "time": dataset.time, 
            "pressure_level":dataset.pressure_level,
            "latitude": dataset.latitude, 
            "longitude": dataset.longitude
        }
    )

    # 2. Extract raw NumPy arrays from the dataset up front
    # This reads the whole 2MB file into memory as raw matrices
    times = dataset.time.values
    lats = dataset.latitude.values
    lons = dataset.longitude.values
    p_levels = dataset.pressure_level.values  # 1D array of pressure values
    
    # Extract 4D data arrays (time, pressure, latitude, longitude)
    t_array = dataset.t.values
    q_array = dataset.q.values

    #3d data array for surfacce pressure
    sfc_p = dataset.sp.values
    sfc_t = dataset.t2m.values 

    # 3. Pre-allocate empty NumPy arrays for the outputs
    shape = (len(times), len(lats), len(lons))
    out_intensity = np.full(shape, np.nan, dtype='float32')
    out_depth = np.full(shape, np.nan, dtype='float32')
    out_surface_temp = np.full(shape, np.nan, dtype='float32')
    out_inversion_top = np.full(shape, np.nan, dtype='float32')
    out_inversion_top_p = np.full(shape, np.nan, dtype='float32')


    # Constants 
    Rd = 287 
    g = 9.8    

    # 4. Process using raw index tracking (Extremely fast in NumPy)
    for t_idx in range(len(times)):
        #print(f"Processing time index: {t_idx+1} / {len(times)}")
        
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
               
                # 1. Find the index of next pressure level 
                sp = sfc_p[t_idx, lat_idx, lon_idx]
                next_p_idx = np.argmin(np.where(p_levels <= sp, sp-p_levels, np.inf))
                    
                # 2. Set your ground conditions at this physical boundary level
                p1 = sp
                t1 = sfc_t[t_idx, lat_idx, lon_idx]
                q1 = q_array[t_idx, next_p_idx-1, lat_idx, lon_idx]
                
                sfc_temp = t1
                current_depth = 0.0
                inv_top_temp = np.nan
                inv_top_p = np.nan

                # Search vertically upward through the indices of the pressure levels
                for p_idx in range(next_p_idx, len(p_levels)):
                    p2 = p_levels[p_idx]
                    t2 = t_array[t_idx, p_idx, lat_idx, lon_idx]
                    q2 = q_array[t_idx, p_idx, lat_idx, lon_idx]
                    
                    if t1 > t2: #Top = highest peak thats greater or equal than the one below it
                        # Inversion peak located
                        inv_top_temp = t1
                        inv_top_p = p_levels[p_idx - 1] # Level below current is the max
                        break
                    else:
                        # Inversion layer continues; calculate layer thickness
                        Tavg = (t1 + t2) / 2.0
                        Qavg = (q1 + q2) / 2.0
                        logp = np.log(p1 / p2)
                        
                        current_depth += (Rd * (1.0 + 0.6 * Qavg) * Tavg * logp) / g
                        
                        # Advance pointers up to the next layer
                        t1, q1, p1 = t2, q2, p2

                # Store directly into the allocated NumPy arrays via indices
                out_surface_temp[t_idx, lat_idx, lon_idx] = sfc_temp
                out_inversion_top[t_idx, lat_idx, lon_idx] = inv_top_temp
                out_inversion_top_p[t_idx, lat_idx, lon_idx] = inv_top_p
                out_depth[t_idx, lat_idx, lon_idx] = current_depth
                out_intensity[t_idx, lat_idx, lon_idx] = inv_top_temp - sfc_temp

    # 5. Package the completed NumPy arrays back into the final Xarray Dataset
    dim3 = ["time", "latitude", "longitude"]
    results["intensity"] = (dim3, out_intensity)
    results["depth"] = (dim3, out_depth)
    results["surface_temp"] = (dim3, out_surface_temp)
    results["inversion_top"] = (dim3, out_inversion_top)
    results["inversion_top_pressurelv"] = (dim3, out_inversion_top_p)

    dims_4d = ["time", "pressure_level", "latitude", "longitude"]
    results["temperature"] = (dims_4d, t_array)

    # Re-apply scientific Metadata
    results.intensity.attrs = {'units': 'K', 'long_name': 'Inversion Temperature Intensity'}
    results.depth.attrs = {'units': 'm', 'long_name': 'Inversion Layer Thickness'}
    results.surface_temp.attrs = {'units': 'K', 'long_name': 'Surface temperature'}
    results.inversion_top.attrs = {'units': 'K', 'long_name': 'Inversion top temperature'}
    results.inversion_top_pressurelv.attrs = {'units': 'hPa', 'long_name': 'Inversion top pressure level'}

    results.temperature.attrs = {'units': 'K', 'long_name': 'Atmospheric Temperature'}
    results.attrs["Month"] = dataset.attrs["Month"]

    return results

def find_inversion_trend(dataset):
    # 1. Coordinate arrays
    latitudes = dataset.latitude.values
    longitudes = dataset.longitude.values
    times = dataset.time.values                  # 1D time array: shape (T,)
    p_levels = dataset.pressure_level.values    # 1D pressure array: shape (P,)

    # 2. Extract Variable arrays with raw NumPy shapes
    intensities = dataset.intensity.values        # 3D array: shape (T, lat, lon)
    depths = dataset.depth.values                # 3D array: shape (T, lat, lon)
    temperatures = dataset.temperature.values    # 4D array: shape (T, p, lat, lon)

    # 3. Pre-calculate Time-series Regression Constants (The Shared X-axis)
    n_times = len(times)
    t_mean = np.mean(times)
    t_diff = times - t_mean
    t_var = np.sum(t_diff**2)  # Shared denominator for slope: sum((x - x_mean)^2)
    
    # Degrees of freedom for the Wald Test t-distribution
    df_pool = n_times - 2
    # Pre-calculated standard error denominator factor for the independent variable
    sqrt_t_var = np.sqrt(t_var)

    # =========================================================================
    # VECTORIZED 3D REGRESSION (Inversion Intensity & Depth)
    # =========================================================================
    # Broadcasting axis 0 (Time) requires extending t_diff to shape (T, 1, 1)
    t_diff_3d = t_diff[:, None, None]
    times_3d = times[:, None, None]

    # --- Intensity Calculations ---
    intensity_mean = np.mean(intensities, axis=0)
    cov_intensity = np.sum(t_diff_3d * (intensities - intensity_mean), axis=0)
    slope_I = cov_intensity / t_var
    intercept_I = intensity_mean - slope_I * t_mean

    # Vectorized residuals and R2
    pred_I = slope_I[None, :, :] * times_3d + intercept_I[None, :, :]
    ss_res_I = np.sum((intensities - pred_I)**2, axis=0)
    ss_tot_I = np.sum((intensities - intensity_mean)**2, axis=0)
    r2_I = 1.0 - (ss_res_I / (ss_tot_I + 1e-10)) # 1e-10 prevents zero-variance division errors
    
    # Vectorized Two-Tailed p-values via Student's t-distribution
    se_I = np.sqrt(ss_res_I / df_pool) / sqrt_t_var
    t_stat_I = slope_I / (se_I + 1e-10)
    pval_I = stats.t.sf(np.abs(t_stat_I), df=df_pool) * 2

    # --- Depth Calculations ---
    depth_mean = np.mean(depths, axis=0)
    cov_depth = np.sum(t_diff_3d * (depths - depth_mean), axis=0)
    slope_D = cov_depth / t_var
    intercept_D = depth_mean - slope_D * t_mean

    pred_D = slope_D[None, :, :] * times_3d + intercept_D[None, :, :]
    ss_res_D = np.sum((depths - pred_D)**2, axis=0)
    ss_tot_D = np.sum((depths - depth_mean)**2, axis=0)
    r2_D = 1.0 - (ss_res_D / (ss_tot_D + 1e-10))
    
    se_D = np.sqrt(ss_res_D / df_pool) / sqrt_t_var
    t_stat_D = slope_D / (se_D + 1e-10)
    pval_D = stats.t.sf(np.abs(t_stat_D), df=df_pool) * 2

    # =========================================================================
    # VECTORIZED 4D REGRESSION (Profile Temperature)
    # =========================================================================
    # For a 4D array (Time, Pressure, Lat, Lon), extend time vectors to shape (T, 1, 1, 1)
    t_diff_4d = t_diff[:, None, None, None]
    times_4d = times[:, None, None, None]

    temp_mean = np.mean(temperatures, axis=0)
    cov_temp = np.sum(t_diff_4d * (temperatures - temp_mean), axis=0)
    slope_T = cov_temp / t_var 
    intercept_T = temp_mean - slope_T * t_mean

    # Vectorized residuals and R2
    pred_T = slope_T[None, :, :, :] * times_4d + intercept_T[None, :, :, :]
    ss_res_T = np.sum((temperatures - pred_T)**2, axis=0)
    ss_tot_T = np.sum((temperatures - temp_mean)**2, axis=0)
    r2_T = 1.0 - (ss_res_T / (ss_tot_T + 1e-10))
    
    # Vectorized Two-Tailed p-values
    se_T = np.sqrt(ss_res_T / df_pool) / sqrt_t_var
    t_stat_T = slope_T *10/ (se_T + 1e-10)
    pval_T = stats.t.sf(np.abs(t_stat_T), df=df_pool) * 2

    # =========================================================================
    # Section 5: Package Data Back to Xarray
    # =========================================================================
    dims = ["latitude", "longitude"]
    dataset["intensityTrend"] = (dims, (slope_I * 10).astype('float32'))  # Scale to per decade
    dataset["intensityR2"] = (dims, r2_I.astype('float32'))
    dataset["intensityPval"] = (dims, pval_I.astype('float32'))
    
    dataset["depthTrend"] = (dims, (slope_D * 10).astype('float32'))      # Scale to per decade
    dataset["depthR2"] = (dims, r2_D.astype('float32'))
    dataset["depthPval"] = (dims, pval_D.astype('float32'))

    dim4 = ["pressure_level", "latitude", "longitude"]
    dataset["temperatureTrend"] = (dim4, (slope_T * 10).astype('float32')) # Scale to per decade
    dataset["temperatureR2"] = (dim4, r2_T.astype('float32'))
    dataset["temperaturePval"] = (dim4, pval_T.astype('float32'))

    #alpha = 0.05 rule for accepting the trend values
    dataset["intensityTrend"] = dataset["intensityTrend"].where(dataset["intensityPval"] <= 0.05)
    dataset["depthTrend"] = dataset["depthTrend"].where(dataset["depthPval"] <= 0.05)

    # Apply Metadata Attributes
    dataset.intensityTrend.attrs = {"units": "K/decade", "long_name": "Trend in Inversion Intensity"}
    dataset.intensityR2.attrs = {"units": "1", "long_name": "R-squared for Inversion Intensity Trend"}
    dataset.intensityPval.attrs = {"units": "1", "long_name": "p-value for Inversion Intensity Trend"}
    
    dataset.depthTrend.attrs = {"units": "m/decade", "long_name": "Trend in Inversion Depth"}
    dataset.depthR2.attrs = {"units": "1", "long_name": "R-squared for Inversion Depth Trend"}
    dataset.depthPval.attrs = {"units": "1", "long_name": "p-value for Inversion Depth Trend"}
    
    dataset.temperatureTrend.attrs = {"units": "K/decade", "long_name": "Trend in per-pressure-level temperature"}
    dataset.temperatureR2.attrs = {"units": "1", "long_name": "R-squared for per-pressure-level temperature trend"}
    dataset.temperaturePval.attrs = {"units": "1", "long_name": "p-value for per-pressure-level temperature trend"}
    
    return dataset

def calculate_monthly_averages(dataset):
    # 1. Initialize the 2D empty sections directly in the dataset using NumPy arrays
    # This matches the shape of your spatial grid (latitude, longitude)
    shape_2d = (len(dataset.latitude), len(dataset.longitude))
    
    dataset["avgIntensity"] = (["latitude", "longitude"], np.full(shape_2d, np.nan, dtype='float32'))
    dataset["avgDepth"] = (["latitude", "longitude"], np.full(shape_2d, np.nan, dtype='float32'))
    
    # Add Metadata
    dataset.avgIntensity.attrs = {'units': 'K', 'long_name': 'Average Inversion Temperature Intensity'}
    dataset.avgDepth.attrs = {'units': 'm', 'long_name': 'Average Inversion Layer Thickness'} # Note: changed 'hPa' to 'm' to match depth units

    # 2. Extract raw NumPy arrays from the dataset up front (Extremely fast)
    # These arrays are 3D: (time, latitude, longitude)
    intensity_array = dataset.intensity.values
    depth_array = dataset.depth.values

    # Get coordinate lengths for the loop limits
    num_times = intensity_array.shape[0]
    num_lats = intensity_array.shape[1]
    num_lons = intensity_array.shape[2]

    # 3. Pre-allocate empty 2D NumPy arrays to store the calculated sums/averages
    out_avg_intensity = np.zeros(shape_2d, dtype='float32')
    out_avg_depth = np.zeros(shape_2d, dtype='float32')

    # 4. Iterate using integer index positions instead of coordinate labels
    #print("Starting spatial averaging calculation...")
    for lat_idx in range(num_lats):
        for lon_idx in range(num_lons):
            
            sum_intensity = 0.0
            sum_depth = 0.0
            
            # Sum up values over all time steps for this specific pixel
            for t_idx in range(num_times):
                sum_intensity += intensity_array[t_idx, lat_idx, lon_idx]
                sum_depth += depth_array[t_idx, lat_idx, lon_idx]
            
            # Compute the average and store it in our 2D output arrays
            out_avg_intensity[lat_idx, lon_idx] = sum_intensity / num_times
            out_avg_depth[lat_idx, lon_idx] = sum_depth / num_times

    # 5. Pack the completed 2D NumPy arrays back into the final Xarray variables
    dataset["avgIntensity"].values = out_avg_intensity
    dataset["avgDepth"].values = out_avg_depth

    #print("Averaging complete!")
    return dataset

def save_results(dataset, location):
    if os.path.isfile(location):
        print(f"{location} Dataset present")
        return(xr.open_dataset(location,  chunks={'time': 10}),location)
    #so to obtain new datasets for the same name, need to delete past ones or move them into another folder
    else:
        result = find_inversion_depth_intensity(dataset)
        print(f"Done {location} step1 ")
        result = find_inversion_trend(result)
        print(f"Done {location} step2 ")
        result = calculate_monthly_averages(result)
        print(f"Done {location} step3 ")
        result = result.drop_vars("temperature") #delete the raw temperature data from the dataset after usage since its not really a result
        result.to_netcdf(location, mode='w')
        print(f"Done {location} completly ")    
        result.close()
        return(result, location)

def calculate_zonal_averages(dataset, north, south, west, east, zoneName,foldername):
    # 1. Handle Latitude Ordering for ERA5 grids
    if dataset.latitude[0] > dataset.latitude[-1]:
        lat_slice = slice(north, south)
    else:
        lat_slice = slice(south, north)

    if dataset.longitude[0] < dataset.longitude[-1]:
        lon_slice = slice(east, west)
    else:
        lon_slice = slice(west, east) 

    # 2. Extract the spatial bounding box (Trim the global data down to your zone)
    zone = dataset.sel(
        latitude=lat_slice,
        longitude=lon_slice
    )
    


    # 3. Calculate Cosine Weights using the sliced zone's latitude array
    weights = np.cos(np.deg2rad(zone.latitude))
    
    # 4. Apply the spatial weighting environment to the zone
    weighted_zone = zone.weighted(weights)
    
    # 5. Compute the spatial mean over the horizontal dimensions
    # This automatically collapses ['latitude', 'longitude'] for ALL variables
    # at once, managing all times and pressure levels instantly!
    spatial_averages = weighted_zone.mean(dim=["latitude", "longitude"], skipna = True)

    # 6. Initialize your clean output Dataset
    # Coords match the collapsed state: time remains intact, pressure_level remains intact
    results = xr.Dataset()

    # 7. Extract and assign the spatial averages into the final container
    # 3D Variables collapse down to 1D arrays of shape (len(time))
    results["depth"] = spatial_averages.depth
    results["surface_temp"] = spatial_averages.surface_temp
    results["inversion_top"] = spatial_averages.inversion_top
    results["inversion_top_pressurelv"] = spatial_averages.inversion_top_pressurelv
    results["intensity"] = spatial_averages.intensity
    

    # 4D Profile Trends collapse down to a 1D array of shape (len(pressure_level))
    # Note: Trends are already time-independent static profiles, so we take the first index [0] 
    # if it retained a dummy time axis, or just extract it directly.
    
    #if "time" in spatial_averages.temperatureTrend.dims:
     #   results[f"avg_temp_trend_{zoneName}"] = spatial_averages.temperatureTrend.isel(time=0)
    #else:

    results[f"temperatureTrend"] = spatial_averages.temperatureTrend

    # 8. Re-apply descriptive metadata attributes
    results["depth"].attrs = {"units": "m", "long_name": f"Area-averaged Inversion Depth for {zoneName}"}
    results["surface_temp"].attrs = {"units": "K", "long_name": f"Area-averaged Surface Temperature for {zoneName}"}
    results["inversion_top"].attrs = {"units": "K", "long_name": f"Area-averaged Inversion Top Temperature for {zoneName}"}
    results["inversion_top_pressurelv"].attrs = {"units": "hPa", "long_name": f"Area-averaged Inversion Top Pressure Level for {zoneName}"}
    results["intensity"].attrs = {"units": "K", "long_name": f"Area-averaged Inversion Intensity for {zoneName}"}
    results["temperatureTrend"].attrs = {"units": "K/decade", "long_name": f"Area-averaged Temperature Trend Profile for {zoneName}"}
    
    # Attach a global tracking attribute naming the region
    results.attrs["region_name"] = zoneName
    results.attrs["spatial_extent"] = f"N:{north}, S:{south}, W:{west}, E:{east}"

    filename = f"{foldername}{zoneName}_results.nc"
    results.to_netcdf(filename, mode='w')

    return  results, filename

def find_trend_extremum(datasets, showPoints = False):
    #TO CHECK WHY VALUES DON'T MATCH THE PAPER

#NEED TO REMOVE THE VALUES OF ENTRIES WITH PVAL>0.05


# Pass monthly intensity trend
    global_maxITrend_val = -np.inf
    global_minITrend_val = np.inf
    global_maxDTrend_val = -np.inf
    global_minDTrend_val = np.inf
    
    for dataset in datasets:
        # Load the scalar extrema into memory
        local_maxITrend_val = float(dataset.intensityTrend.max().compute())
        local_minITrend_val = float(dataset.intensityTrend.min().compute())
        local_maxDTrend_val = float(dataset.depthTrend.max().compute())
        local_minDTrend_val = float(dataset.depthTrend.min().compute())

        # Max Intensity
        if local_maxITrend_val > global_maxITrend_val:
            global_maxITrend_val = local_maxITrend_val
            # FIX: Append .compute() to the boolean mask condition expression
            cond = (dataset.intensityTrend == local_maxITrend_val).compute()
            global_maxITrend_loc = dataset.where(cond, drop=True)
            
        # Max Depth
        if local_maxDTrend_val > global_maxDTrend_val:
            global_maxDTrend_val = local_maxDTrend_val
            cond = (dataset.depthTrend == local_maxDTrend_val).compute()
            global_maxDTrend_loc = dataset.where(cond, drop=True)

        # Min Intensity
        if local_minITrend_val < global_minITrend_val:
            global_minITrend_val = local_minITrend_val
            cond = (dataset.intensityTrend == local_minITrend_val).compute()
            global_minITrend_loc = dataset.where(cond, drop=True)
            
        # Min Depth
        if local_minDTrend_val < global_minDTrend_val:
            global_minDTrend_val = local_minDTrend_val
            cond = (dataset.depthTrend == local_minDTrend_val).compute()
            global_minDTrend_loc = dataset.where(cond, drop=True)
    if showPoints:
        print(f"The maximum intensity trend of {global_maxITrend_val} K/decade is at latitude:{global_maxITrend_loc.latitude.values.item()}, longitude:{global_maxITrend_loc.longitude.values.item()} in {global_maxITrend_loc.attrs['Month']}")
        print(f"The minimum intensity trend of {global_minITrend_val} K/decade is at latitude:{global_minITrend_loc.latitude.values.item()}, longitude:{global_minITrend_loc.longitude.values.item()} in {global_minITrend_loc.attrs['Month']}")
        print(f"The maximum depth trend of {global_maxDTrend_val} m/decade is at latitude:{global_maxDTrend_loc.latitude.values.item()}, longitude:{global_maxDTrend_loc.longitude.values.item()} in {global_maxDTrend_loc.attrs['Month']}")
        print(f"The minimum depth trend of {global_minDTrend_val} m/decade is at latitude:{global_minDTrend_loc.latitude.values.item()}, longitude:{global_minDTrend_loc.longitude.values.item()} in {global_minDTrend_loc.attrs['Month']}")              
    
    # Complete 2D list matrix return structure
    return [
        ["Point_of_Max_Intensity_Trend", global_maxITrend_loc.latitude.values.item(), global_maxITrend_loc.longitude.values.item(), global_maxITrend_loc.attrs['Month']],
        ["Point_of_Min_Intensity_Trend", global_minITrend_loc.latitude.values.item(), global_minITrend_loc.longitude.values.item(), global_minITrend_loc.attrs['Month']],
        ["Point_of_Max_Depth_Trend",     global_maxDTrend_loc.latitude.values.item(), global_maxDTrend_loc.longitude.values.item(), global_maxDTrend_loc.attrs['Month']],
        ["Point_of_Min_Depth_Trend",     global_minDTrend_loc.latitude.values.item(), global_minDTrend_loc.longitude.values.item(), global_minDTrend_loc.attrs['Month']]
    ]
           


if __name__ == "__main__":
    from DownloadData import era5_data_load
    from FormatData import era5_data_format
    era5data = era5_data_load()
    era5_monthly_data = era5_data_format(era5data) #list with jan,feb,dec data
    #save_results(era5_monthly_data[0],"Data&Model/ERA5data_arctic_jan_results.nc")
    #save_results(era5_monthly_data[1],"Data&Model/ERA5data_arctic_feb_results.nc")
    #save_results(era5_monthly_data[2],"Data&Model/ERA5data_arctic_dec_results.nc")
    
    
