import xarray as xr
import numpy as np
import os
from scipy import stats
import itertools
import pandas as pd
from pathlib import Path

def Era5_find_inversion_depth_intensity(dataset):
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

    #3d data array for surface pressure
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
                        inv_top_p = p1 # Level below current is the max
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

def Era5_save_results(dataset, location):
    if os.path.isfile(location):
        print(f"{location} Dataset present")
        return(xr.open_dataset(location,  chunks={'time': 10}),location)
    #so to obtain new datasets for the same name, need to delete past ones or move them into another folder
    else:
        result = Era5_find_inversion_depth_intensity(dataset)
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

def calculate_zonal_averages(dataset, north:float, south:float, west:float, east:float, zoneName,foldername):
    # 1. Determine coordinate directions (Your existing slice configuration)  #STILL PROBLEM
    if dataset.latitude[0] > dataset.latitude[-1]:
        lat_slice = slice(north, south)
    else:
        lat_slice = slice(south, north)

    if dataset.longitude[0] < dataset.longitude[-1]:
        lon_slice = slice(west, east)  # Note: Standard convention is west to east
    else:
        lon_slice = slice(east, west)


    # 2. Extract the spatial bounding box
    zone = dataset.sel(latitude=lat_slice, longitude=lon_slice) #BREAKSDOWN HERE

    # =========================================================================
    # ADAPTED TWO-STEP AREA AVERAGE
    # =========================================================================

    # Step 1: Take the Zonal Mean
    # This averages along the lines of longitude, collapsing 'longitude'
    # and leaving you with a 1D profile across latitudes.   
    zonal_mean = zone.mean(dim="longitude", skipna=True)    
  
    # Step 2a: Calculate Cosine Weights using the remaining latitude coordinates
    weights = np.cos(np.deg2rad(zonal_mean.latitude))

    # Step 2b: Apply the weights and take the weighted mean across latitudes
    weighted_lat = zonal_mean.weighted(weights)
    spatial_averages = weighted_lat.mean(dim="latitude", skipna=True)
    # =========================================================================

    # 3. Initialize your clean output Dataset
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


#ABOVE WERE FIRST ATTEMPS OF RECREATING RESULTS, BELOW IS THE ACTUALLY USED CODES          

def radiosonde_daily_climatology(dataset):
    site_name = dataset.attrs["SiteName"]
    output_location = f"Data&Model/Radiosonde/NC/{site_name}_daily.nc"
    temp_location   = f"Data&Model/Radiosonde/NC/{site_name}_daily.tmp.nc"

    print(f"Calculating Daily Climatology for {site_name}") 

    mixR = dataset.mixRatio.values
    temp = dataset.temperature.values
    time  = dataset.time.values  
    pressure = dataset.pressure.values
    print(pressure)

    dim = len(time)
    sbi_strength    = np.full(dim, np.nan, dtype="float32")
    sbi_depth       = np.full(dim, np.nan, dtype="float32")
    sbi_intensity   = np.full(dim, np.nan, dtype="float32")
    sbi_frequency = np.full(dim, 0.0, dtype="float32")

    inversion_top_pressure = np.full(dim, np.nan, dtype="float32")
    inversion_top_temp   = np.full(dim, np.nan, dtype="float32")

    surface_temp     = np.full(dim, np.nan, dtype="float32")

    hasV = np.full(dim, 1.0, dtype="float32") #To check if a day has not enough 

    # Constants 
    Rd = 287 
    g = 9.8  

    #1. Search Inversion Top
    for t_idx in range(len(time)):

        #Find surface temperature location
        t1_idx = int(np.argmax(~np.isnan(temp[t_idx])))
        surface_temp[t_idx] = temp[t_idx][t1_idx]
        t1 = temp[t_idx][t1_idx]
        print(temp[t_idx])
        inversionFound = False
        p1 = pressure[t1_idx]
        v1 = mixR[t_idx,t1_idx]
        if np.isnan(v1): 
            v1 = 0.0
        depth = 0.0
       

        for p_idx in range(t1_idx+1,len(pressure)):
            t2 = temp[t_idx,p_idx]
            p2 = pressure[p_idx]
            v2 = mixR[t_idx, p_idx]

            if np.isnan(t2) or np.isnan(p2):
                break

            if np.isnan(v2) and t2 > t1:
                #Only flag if its before the inversion layer
                hasV[t_idx] = 0.0

            if t1 > t2: #Top = highest peak thats greater or equal than the one below it
                if (t1 - surface_temp[t_idx]) >= 0.05:
                    # Inversion peak located
                    #Log in the data
                    inversion_top_temp[t_idx] = t1
                    inversion_top_pressure[t_idx] = p1
                    sbi_depth[t_idx] = depth
                    sbi_strength[t_idx] = t1 - surface_temp[t_idx]
                    sbi_frequency[t_idx] = 1.0
                    inversionFound = True

                    if sbi_depth[t_idx] !=0:
                        sbi_intensity[t_idx] = sbi_strength[t_idx]/sbi_depth[t_idx]
                    else:
                        sbi_intensity[t_idx] = np.nan
                    break
                else:
                    #else triggers if the temperature we found is not enough meaning its basically the surface layer that failed
                    break
            else:
                # Inversion layer continues; calculate layer thickness
                Tavg = (t1 + t2) / 2.0
                Qavg = (v1 + v2) / 2.0
                logp = np.log(p1 / p2)
                
                depth += (Rd * (1.0 + 0.6 * Qavg) * Tavg * logp) / g                             

            # Advance pointers up to the next layer
            t1, p1, v1 = t2,p2, v2 
        if not inversionFound:
            sbi_intensity[t_idx] = np.nan
            sbi_strength[t_idx] = np.nan
            sbi_depth[t_idx] = np.nan

    # 2. Assign the Core SBI Diagnostic Arrays
    dataset["sbi_strength"]       = (("time",), sbi_strength, {"units": "K", "long_name": "Inversion Strength (T_top - T_sfc)"})
    dataset["sbi_depth"]          = (("time",), sbi_depth, {"units": "m", "long_name": "Inversion Depth (z_top - z_sfc)"})
    dataset["sbi_intensity"]      = (("time",), sbi_intensity, {"units": "K km-1", "long_name": "Inversion Lapse Rate / Intensity"})
    dataset["sbi_frequency"] = (("time",), sbi_frequency, {"units": "1", "long_name": "SBI Occurrence Flag (1=True, 0=False)"})

    #Assign Inversion Top Variables
    dataset["inversion_top_pressure"] = (("time",), inversion_top_pressure, {"units": "hPa", "long_name": "Inversion Top Pressure"})
    dataset["inversion_top_temp"]     = (("time",), inversion_top_temp, {"units": "K", "long_name": "Inversion Top Temperature"})

    #Assign Surface State Variables
    dataset["surface_temp"]   = (("time",), surface_temp, {"units": "K", "long_name": "Surface Temperature"})
    dataset["hasV"]   = (("time",), hasV, {"long_name": "Mixing ratio availability diagnostic"})

    # 3. Save/Export the updated Dataset to NetCDF
    dataset.to_netcdf(temp_location)
    dataset.close()
    os.replace(temp_location,output_location)
    return dataset
    
def radiosonde_monthly_climatology(datasetD, dataLack = [], overwrite = False):
    site_name = datasetD.attrs["SiteName"]
    output_location = f"Data&Model/Radiosonde/NC/{site_name}_monthly.nc"

    if os.path.isfile(output_location) and overwrite == False:    #Skip if already exist and don't want to do changes to it
        print(f"{site_name} monthly data already calculated")
        ds = xr.open_dataset(output_location)
        return ds
    print(f"Calculating Monthly Climatology for {site_name}")


    #region 0. Remove monthly values where we have not enough mixR data
    # Group by month-year-hour periods to count total days and valid days
    # Create a temporary grouping coordinate for Year-Month-Hour
    ymh_group = datasetD.time.dt.strftime("%Y-%m-%H").rename("ymh")

    # Total profile count per month-hour group vs available valid profiles
    group_total = datasetD["hasV"].groupby(ymh_group).count(dim="time")
    group_valid = datasetD["hasV"].groupby(ymh_group).sum(dim="time")
    group_missing = group_total - group_valid

    # Identify invalid 'ymh' groups where missing profiles > 5
    invalid_groups = group_missing.where(group_missing > 5, drop=True)["ymh"].values

    # To see what are the dates
    #invalid_df = group_missing.where(group_missing > 5, drop=True).to_dataframe(name="missing_count")
    #print(invalid_df)

    # Create a boolean mask matching the original time dimension
    invalid_time_mask = np.isin(ymh_group.values, invalid_groups)

    # Mask target variables in bulk
    datasetD["sbi_depth"] = xr.where(invalid_time_mask, np.nan, datasetD["sbi_depth"])
    datasetD["sbi_intensity"] = xr.where(
        invalid_time_mask, np.nan, datasetD["sbi_intensity"]
    )
    # Clean up helper coordinate
    datasetD = datasetD.drop_vars("hasV")
    #endregion

    # 1. Turn the daily data to monthly data
    time_keys = datasetD.time.dt.strftime("%Y-%m-%H")
    ds_climatology = datasetD.groupby(time_keys).mean(dim="time")
    ds_climatology = ds_climatology.rename({"strftime": "time"})
    ds_climatology["time"] = pd.to_datetime(ds_climatology["time"].values, format="%Y-%m-%H")
    #print(dataLack)
    ds_climatology = ds_climatology.where(~ds_climatology.time.isin(dataLack)) #Remove monthly data from when theres not enough data

    #region 2. Calculate Trends
    pressure = ds_climatology.pressure.values
    shape_pressure = len(pressure)
    month_nums = [1, 2, 12]
    hour_nums = [0, 12]
    month_hour = list(itertools.product(month_nums, hour_nums))
    month_hour_str = [f"{m:02d}-{h:02d}" for m, h in month_hour]

    ds_climatology.coords["month_hour"] = month_hour_str
    ds_climatology.coords["month_hour"].attrs["long_name"] = "Month of Year at Specific hours"
    n_combos = len(month_hour) # 6

    frequency_trend        = np.full(n_combos, np.nan, dtype="float32")
    frequency_trend_r2     = np.full(n_combos, np.nan, dtype="float32")
    frequency_trend_pvalue = np.full(n_combos, np.nan, dtype="float32")

    strength_trend         = np.full(n_combos, np.nan, dtype="float32")
    strength_trend_r2      = np.full(n_combos, np.nan, dtype="float32")
    strength_trend_pvalue  = np.full(n_combos, np.nan, dtype="float32")

    depth_trend            = np.full(n_combos, np.nan, dtype="float32")
    depth_trend_r2         = np.full(n_combos, np.nan, dtype="float32")
    depth_trend_pvalue     = np.full(n_combos, np.nan, dtype="float32")

    intensity_trend        = np.full(n_combos, np.nan, dtype="float32")
    intensity_trend_r2     = np.full(n_combos, np.nan, dtype="float32")
    intensity_trend_pvalue = np.full(n_combos, np.nan, dtype="float32")

    dim = (n_combos, shape_pressure)
    temperature_trend        = np.full(dim, np.nan, dtype="float32")
    temperature_trend_r2     = np.full(dim, np.nan, dtype="float32")
    temperature_trend_pvalue = np.full(dim, np.nan, dtype="float32") 

    for idx, (month, hour) in enumerate(month_hour):
        
            # 1. Create the boolean mask for the current month/hour
            time_mask = (ds_climatology.time.dt.hour == hour) & (ds_climatology.time.dt.month == month)
            
            # 2. Extract matching years to serve as x_time (MUST match y_freq length!)
            x_years = ds_climatology.time.dt.year.values[time_mask]

            # --- 1. SBI Frequency ---
            y_freq = ds_climatology["sbi_frequency"].values[time_mask]
            valid_freq = ~np.isnan(y_freq) & ~np.isnan(x_years)
            if np.sum(valid_freq) > 2:
                res_f = stats.linregress(x_years[valid_freq], y_freq[valid_freq])
                frequency_trend[idx]        = res_f.slope * 10  # convert to per decade
                frequency_trend_r2[idx]     = res_f.rvalue ** 2
                frequency_trend_pvalue[idx] = res_f.pvalue

            # --- 2. SBI Strength ---
            y_str = ds_climatology["sbi_strength"].values[time_mask]
            valid_str = ~np.isnan(y_str) & ~np.isnan(x_years)
            if np.sum(valid_str) > 2:
                res_s = stats.linregress(x_years[valid_str], y_str[valid_str])
                strength_trend[idx]        = res_s.slope * 10
                strength_trend_r2[idx]     = res_s.rvalue ** 2
                strength_trend_pvalue[idx] = res_s.pvalue

            # --- 3. SBI Depth ---
            y_dep = ds_climatology["sbi_depth"].values[time_mask]
            valid_dep = ~np.isnan(y_dep) & ~np.isnan(x_years)
            if np.sum(valid_dep) > 2:
                res_d = stats.linregress(x_years[valid_dep], y_dep[valid_dep])
                depth_trend[idx]        = res_d.slope * 10
                depth_trend_r2[idx]     = res_d.rvalue ** 2
                depth_trend_pvalue[idx] = res_d.pvalue

            # --- 4. SBI Intensity ---
            y_int = ds_climatology["sbi_intensity"].values[time_mask]
            valid_int = ~np.isnan(y_int) & ~np.isnan(x_years)
            if np.sum(valid_int) > 2:
                res_i = stats.linregress(x_years[valid_int], y_int[valid_int])
                intensity_trend[idx]        = res_i.slope * 10
                intensity_trend_r2[idx]     = res_i.rvalue ** 2
                intensity_trend_pvalue[idx] = res_i.pvalue

            # --- 5. Temperature Profile ---
            y_temp = ds_climatology["temperature"].values[time_mask]
            for p_idx, p_val in enumerate(pressure):
                temp = y_temp[:, p_idx]
                valid_temp = ~np.isnan(temp) & ~np.isnan(x_years)
                if np.sum(valid_temp) > 2:               
                    # Fixed typo: changed valid_int -> valid_temp below
                    res_t = stats.linregress(x_years[valid_temp], temp[valid_temp])
                    temperature_trend[idx][p_idx]        = res_t.slope * 10
                    temperature_trend_r2[idx][p_idx]     = res_t.rvalue ** 2
                    temperature_trend_pvalue[idx][p_idx] = res_t.pvalue


    ds_climatology["frequency_trend"] = (("month_hour",), frequency_trend, {"units": "% decade-1", "long_name": "Trend in SBI Frequency"})
    ds_climatology["frequency_trend_r2"] = (("month_hour",), frequency_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Frequency Trend"})
    ds_climatology["frequency_trend_pvalue"] = (("month_hour",), frequency_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Frequency Trend"})


    ds_climatology["strength_trend"] = (("month_hour",), strength_trend, {"units": "K decade-1", "long_name": "Trend in SBI Strength"})
    ds_climatology["strength_trend_r2"] = (("month_hour",), strength_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Strength Trend"})
    ds_climatology["strength_trend_pvalue"] = (("month_hour",), strength_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Strength Trend"})


    ds_climatology["depth_trend"] = (("month_hour",), depth_trend, {"units": "m decade-1", "long_name": "Trend in SBI Depth"})
    ds_climatology["depth_trend_r2"] = (("month_hour",), depth_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Depth Trend"})
    ds_climatology["depth_trend_pvalue"] = (("month_hour",), depth_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Depth Trend"})


    ds_climatology["intensity_trend"] = (("month_hour",), intensity_trend, {"units": "K km-1 decade-1", "long_name": "Trend in SBI Intensity"})
    ds_climatology["intensity_trend_r2"] = (("month_hour",), intensity_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Intensity Trend"})
    ds_climatology["intensity_trend_pvalue"] = (("month_hour",), intensity_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Intensity Trend"})

    ds_climatology["temperature_trend"] = (("month_hour","pressure"), temperature_trend, {"units": "K decade-1", "long_name": "Trend in Temperature"})
    ds_climatology["temperature_trend_r2"] = (("month_hour","pressure"), temperature_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for Temperature Trend"})
    ds_climatology["temperature_trend_pvalue"] = (("month_hour","pressure"), temperature_trend_pvalue, {"units": "1", "long_name": "p-value for Temperature"})

    # endregion

    # 3. Find the secondary indices: impact, diurnal contrast 
    time_diff = np.unique(ds_climatology.time.dt.strftime('%Y-%m').values)
    ds_climatology.coords["year_month"] = time_diff
    ds_climatology["year_month"] = pd.to_datetime(ds_climatology["year_month"].values, format="%Y-%m")
    ds_climatology.coords["year_month"].attrs["long_name"] = "Month of a Year"

    ELR = 0.0065   #Environmental Lapse rate in K/m
    sbiImpact_00 = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 0)).values * ELR + ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 0)).values 
    sbiImpact_12 = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 12)).values * ELR + ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 12)).values     
    sbi_impact = (sbiImpact_00 + sbiImpact_12)/2
    ds_climatology["sbi_impact"] = (("year_month"), sbi_impact, {"units": "K m", "long_name": "Cumulative Thermal Deficit Impact"})

    diurnal_contrast_F = ds_climatology["sbi_frequency"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_frequency"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_F"] = (("year_month",), diurnal_contrast_F, {"units": "%", "long_name": "Diurnal Frequency Contrast (12Z - 00Z)"})

    diurnal_contrast_T = ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_T"] = (("year_month",), diurnal_contrast_T, {"units": "K", "long_name": "Diurnal Strength Contrast (12Z - 00Z)"})

    diurnal_contrast_Z = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_Z"] = (("year_month",), diurnal_contrast_Z, {"units": "m", "long_name": "Diurnal Depth Contrast (12Z - 00Z)"})

    ds_climatology.attrs["SiteName"] = site_name
    ds_climatology.to_netcdf(output_location, mode='w')
    return ds_climatology

def radiosonde_coordinates(csvFolder, coordinate = [45,0,45,0]):
     #N,W,S,E   Initial values as given

    csv_folder = Path(csvFolder)
    origins = ["","","",""]

    # Use rglob to directly match all .csv files regardless of folder depth
    for csv_file in csv_folder.rglob("*.csv"):
        tryPlugin = False
        try:
            # 1. 'usecols' speeds up reading by skipping unused columns
            # 2. 'engine="c"' ensures high-performance parsing
            data = pd.read_csv(csv_file, usecols=["longitude", "latitude"])
        except (ValueError, KeyError):
            # Skip files missing 'longitude' or 'latitude' headers
            continue

        # Convert to numeric safely
        lon = pd.to_numeric(data["longitude"], errors="coerce")
        lat = pd.to_numeric(data["latitude"], errors="coerce")

        # Extract min/max (Pandas automatically drops NaNs)
        min_lon, max_lon = lon.min(), lon.max()
        min_lat, max_lat = lat.min(), lat.max()

        # Update coordinates only if valid numeric bounds were returned
        if pd.notna(max_lon) and max_lon > coordinate[3]:
            coordinate[3] = max_lon
            origins[3] = csv_file
        if pd.notna(min_lon) and min_lon < coordinate[1]:
            coordinate[1] = min_lon
            origins[1] = csv_file
        if pd.notna(max_lat) and max_lat > coordinate[0]:
            coordinate[0] = max_lat
            origins[0] = csv_file
        if pd.notna(min_lat) and min_lat < coordinate[2]:
            coordinate[2] = min_lat
            origins[2] = csv_file
    #print(origins)
    coordinate = [float(x) for x in coordinate]
    return(coordinate)
                            
def era5_daily_climatology(dataset, overwrite = False):
    site_name = dataset.attrs["SiteName"]
    output_location = f"Data&Model/ERA5/{site_name}/era5_{site_name}_daily.nc"

    if os.path.isfile(output_location) and overwrite == False:    #Skip if already exist and don't want to do changes to it
        print(f"{site_name} Daily Climatology already calculated ")
        ds = xr.open_dataset(output_location)
        return ds
    print(f"Calculating ERA5 Daily Climatology for {site_name}")
    
    pressure = dataset.pressure.values  
    temp = dataset.temperature.values
    q_array = dataset.mixRatio.values
    sfc_p = dataset.sp.values
    sfc_t = dataset.t2m.values 

    time = dataset.time.values

    dim= len(time)
    
    sbi_strength    = np.full(dim, np.nan, dtype="float32")
    sbi_depth       = np.full(dim, np.nan, dtype="float32")
    sbi_intensity   = np.full(dim, np.nan, dtype="float32")
    sbi_frequency = np.full(dim, 0.0, dtype="float32")
    inversion_top_pressure = np.full(dim, np.nan, dtype="float32")
    inversion_top_temp   = np.full(dim, np.nan, dtype="float32")
    surface_temp     = np.full(dim, sfc_t, dtype="float32")

    # Constants 
    Rd = 287 
    g = 9.8  

    for t_idx in range(len(time),):

                sfc_temp = sfc_t[t_idx]
                sfc_pressure = sfc_p[t_idx]


                t1,p1 = sfc_temp, sfc_pressure
                next_p_idx = np.argmin(np.where(pressure <= p1, p1-pressure, np.inf)) 
                depth = 0.0
                inversionFound = False
                if next_p_idx == 0:
                    q1 = q_array[t_idx, 0]
                else:
                    q1 = q_array[t_idx, next_p_idx-1]
                
                # Search vertically upward through the indices of the pressure levels
                for p_idx in range(next_p_idx, len(pressure)):
                    p2 = pressure[p_idx]
                    t2 = temp[t_idx, p_idx]
                    q2 = q_array[t_idx, p_idx]
                    
                    if t1 > t2: #Top = highest peak thats greater or equal than the one below it
                        # Inversion peak located
                        if (t1 - sfc_temp) > 0.05:
                            inversion_top_temp[t_idx] = t1
                            inversion_top_pressure[t_idx] = p1
                            sbi_depth[t_idx] = depth
                            sbi_strength[t_idx] = t1 - sfc_temp
                            sbi_frequency[t_idx] = 1.0
                            inversionFound = True

                            if sbi_depth[t_idx] !=0:
                                sbi_intensity[t_idx] = sbi_strength[t_idx]/sbi_depth[t_idx]
                            else:
                                sbi_intensity[t_idx] = 0
                        break   

                    else:
                        # Inversion layer continues; calculate layer thickness
                        Tavg = (t1 + t2) / 2.0
                        Qavg = (q1 + q2) / 2.0
                        logp = np.log(p1 / p2)
                        
                        depth += (Rd * (1.0 + 0.6 * Qavg) * Tavg * logp) / g
                        
                        # Advance pointers up to the next layer
                        t1, q1, p1 = t2, q2, p2

                if not inversionFound:
                    sbi_intensity[t_idx] = np.nan
                    sbi_strength[t_idx] = np.nan
                    sbi_depth[t_idx] = np.nan

    # 1. Assign the Core SBI Diagnostic Arrays
    dim3 = ("time", )
    dataset["sbi_strength"]       = (dim3, sbi_strength, {"units": "K", "long_name": "Inversion Strength (T_top - T_sfc)"})
    dataset["sbi_depth"]          = (dim3, sbi_depth, {"units": "m", "long_name": "Inversion Depth (z_top - z_sfc)"})
    dataset["sbi_intensity"]      = (dim3, sbi_intensity, {"units": "K km-1", "long_name": "Inversion Lapse Rate / Intensity"})
    dataset["sbi_frequency"] = (dim3, sbi_frequency, {"units": "1", "long_name": "SBI Frequency"})

    # 2. Assign Inversion Top Variables
    dataset["inversion_top_pressure"] = (dim3, inversion_top_pressure, {"units": "hPa", "long_name": "Inversion Top Pressure"})
    dataset["inversion_top_temp"]     = (dim3, inversion_top_temp, {"units": "K", "long_name": "Inversion Top Temperature"})

    # 3. Assign Surface State Variables
    dataset["surface_temp"]   = (dim3, surface_temp, {"units": "K", "long_name": "Surface Temperature"})

    # 5. Save/Export the updated Dataset to NetCDF
    dataset.to_netcdf(output_location)
    return dataset

def era5_monthly_climatology(datasetD, overwrite = False):
    site_name = datasetD.attrs["SiteName"]
    output_location = f"Data&Model/ERA5/{site_name}/era5_{site_name}_monthly.nc"

    if os.path.isfile(output_location) and overwrite == False:    #Skip if already exist and don't want to do changes to it
        print(f"{site_name} monthly data already calculated")
        ds = xr.open_dataset(output_location)
        return ds
    print(f"Calculating Monthly Climatology for {site_name}")


    # 1. Turn the daily data to monthly data
    time_keys = datasetD.time.dt.strftime("%Y-%m-%H")
    ds_climatology = datasetD.groupby(time_keys).mean(dim="time")
    ds_climatology = ds_climatology.rename({"strftime": "time"})
    ds_climatology["time"] = pd.to_datetime(ds_climatology["time"].values, format="%Y-%m-%H")

    #region 2. Calculate Trends
    pressure = ds_climatology.pressure.values
    shape_pressure = len(pressure)
    month_nums = [1, 2, 12]
    hour_nums = [0, 12]
    month_hour = list(itertools.product(month_nums, hour_nums))
    month_hour_str = [f"{m:02d}-{h:02d}" for m, h in month_hour]

    ds_climatology.coords["month_hour"] = month_hour_str
    ds_climatology.coords["month_hour"].attrs["long_name"] = "Month of Year at Specific hours"
    n_combos = len(month_hour) # 6

    frequency_trend        = np.full(n_combos, np.nan, dtype="float32")
    frequency_trend_r2     = np.full(n_combos, np.nan, dtype="float32")
    frequency_trend_pvalue = np.full(n_combos, np.nan, dtype="float32")

    strength_trend         = np.full(n_combos, np.nan, dtype="float32")
    strength_trend_r2      = np.full(n_combos, np.nan, dtype="float32")
    strength_trend_pvalue  = np.full(n_combos, np.nan, dtype="float32")

    depth_trend            = np.full(n_combos, np.nan, dtype="float32")
    depth_trend_r2         = np.full(n_combos, np.nan, dtype="float32")
    depth_trend_pvalue     = np.full(n_combos, np.nan, dtype="float32")

    intensity_trend        = np.full(n_combos, np.nan, dtype="float32")
    intensity_trend_r2     = np.full(n_combos, np.nan, dtype="float32")
    intensity_trend_pvalue = np.full(n_combos, np.nan, dtype="float32")

    dim = (n_combos, shape_pressure)
    temperature_trend        = np.full(dim, np.nan, dtype="float32")
    temperature_trend_r2     = np.full(dim, np.nan, dtype="float32")
    temperature_trend_pvalue = np.full(dim, np.nan, dtype="float32") 

    for idx, (month, hour) in enumerate(month_hour):
        
            # 1. Create the boolean mask for the current month/hour
            time_mask = (ds_climatology.time.dt.hour == hour) & (ds_climatology.time.dt.month == month)
            
            # 2. Extract matching years to serve as x_time (MUST match y_freq length!)
            x_years = ds_climatology.time.dt.year.values[time_mask]

            # --- 1. SBI Frequency ---
            y_freq = ds_climatology["sbi_frequency"].values[time_mask]
            valid_freq = ~np.isnan(y_freq) & ~np.isnan(x_years)
            if np.sum(valid_freq) > 2:
                res_f = stats.linregress(x_years[valid_freq], y_freq[valid_freq])
                frequency_trend[idx]        = res_f.slope * 10  # convert to per decade
                frequency_trend_r2[idx]     = res_f.rvalue ** 2
                frequency_trend_pvalue[idx] = res_f.pvalue

            # --- 2. SBI Strength ---
            y_str = ds_climatology["sbi_strength"].values[time_mask]
            valid_str = ~np.isnan(y_str) & ~np.isnan(x_years)
            if np.sum(valid_str) > 2:
                res_s = stats.linregress(x_years[valid_str], y_str[valid_str])
                strength_trend[idx]        = res_s.slope * 10
                strength_trend_r2[idx]     = res_s.rvalue ** 2
                strength_trend_pvalue[idx] = res_s.pvalue

            # --- 3. SBI Depth ---
            y_dep = ds_climatology["sbi_depth"].values[time_mask]
            valid_dep = ~np.isnan(y_dep) & ~np.isnan(x_years)
            if np.sum(valid_dep) > 2:
                res_d = stats.linregress(x_years[valid_dep], y_dep[valid_dep])
                depth_trend[idx]        = res_d.slope * 10
                depth_trend_r2[idx]     = res_d.rvalue ** 2
                depth_trend_pvalue[idx] = res_d.pvalue

            # --- 4. SBI Intensity ---
            y_int = ds_climatology["sbi_intensity"].values[time_mask]
            valid_int = ~np.isnan(y_int) & ~np.isnan(x_years)
            if np.sum(valid_int) > 2:
                res_i = stats.linregress(x_years[valid_int], y_int[valid_int])
                intensity_trend[idx]        = res_i.slope * 10
                intensity_trend_r2[idx]     = res_i.rvalue ** 2
                intensity_trend_pvalue[idx] = res_i.pvalue

            # --- 5. Temperature Profile ---
            y_temp = ds_climatology["temperature"].values[time_mask]
            for p_idx, p_val in enumerate(pressure):
                temp = y_temp[:, p_idx]
                valid_temp = ~np.isnan(temp) & ~np.isnan(x_years)
                if np.sum(valid_temp) > 2:               
                    # Fixed typo: changed valid_int -> valid_temp below
                    res_t = stats.linregress(x_years[valid_temp], temp[valid_temp])
                    temperature_trend[idx][p_idx]        = res_t.slope * 10
                    temperature_trend_r2[idx][p_idx]     = res_t.rvalue ** 2
                    temperature_trend_pvalue[idx][p_idx] = res_t.pvalue


    ds_climatology["frequency_trend"] = (("month_hour",), frequency_trend, {"units": "% decade-1", "long_name": "Trend in SBI Frequency"})
    ds_climatology["frequency_trend_r2"] = (("month_hour",), frequency_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Frequency Trend"})
    ds_climatology["frequency_trend_pvalue"] = (("month_hour",), frequency_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Frequency Trend"})


    ds_climatology["strength_trend"] = (("month_hour",), strength_trend, {"units": "K decade-1", "long_name": "Trend in SBI Strength"})
    ds_climatology["strength_trend_r2"] = (("month_hour",), strength_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Strength Trend"})
    ds_climatology["strength_trend_pvalue"] = (("month_hour",), strength_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Strength Trend"})


    ds_climatology["depth_trend"] = (("month_hour",), depth_trend, {"units": "m decade-1", "long_name": "Trend in SBI Depth"})
    ds_climatology["depth_trend_r2"] = (("month_hour",), depth_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Depth Trend"})
    ds_climatology["depth_trend_pvalue"] = (("month_hour",), depth_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Depth Trend"})


    ds_climatology["intensity_trend"] = (("month_hour",), intensity_trend, {"units": "K km-1 decade-1", "long_name": "Trend in SBI Intensity"})
    ds_climatology["intensity_trend_r2"] = (("month_hour",), intensity_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for SBI Intensity Trend"})
    ds_climatology["intensity_trend_pvalue"] = (("month_hour",), intensity_trend_pvalue, {"units": "1", "long_name": "p-value for SBI Intensity Trend"})

    ds_climatology["temperature_trend"] = (("month_hour","pressure"), temperature_trend, {"units": "K decade-1", "long_name": "Trend in Temperature"})
    ds_climatology["temperature_trend_r2"] = (("month_hour","pressure"), temperature_trend_r2, {"units": "1", "long_name": "Coefficient of Determination (R^2) for Temperature Trend"})
    ds_climatology["temperature_trend_pvalue"] = (("month_hour","pressure"), temperature_trend_pvalue, {"units": "1", "long_name": "p-value for Temperature"})

    # endregion

    # 3. Find the secondary indices: impact, diurnal contrast 
    time_diff = np.unique(ds_climatology.time.dt.strftime('%Y-%m').values)
    ds_climatology.coords["year_month"] = time_diff
    ds_climatology["year_month"] = pd.to_datetime(ds_climatology["year_month"].values, format="%Y-%m")
    ds_climatology.coords["year_month"].attrs["long_name"] = "Month of a Year"

    ELR = 0.0065   #Environmental Lapse rate in K/m
    sbiImpact_00 = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 0)).values * ELR + ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 0)).values 
    sbiImpact_12 = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 12)).values * ELR + ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 12)).values     
    sbi_impact = (sbiImpact_00 + sbiImpact_12)/2
    ds_climatology["sbi_impact"] = (("year_month"), sbi_impact, {"units": "K m", "long_name": "Cumulative Thermal Deficit Impact"})

    diurnal_contrast_F = ds_climatology["sbi_frequency"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_frequency"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_F"] = (("year_month",), diurnal_contrast_F, {"units": "%", "long_name": "Diurnal Frequency Contrast (12Z - 00Z)"})

    diurnal_contrast_T = ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_strength"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_T"] = (("year_month",), diurnal_contrast_T, {"units": "K", "long_name": "Diurnal Strength Contrast (12Z - 00Z)"})

    diurnal_contrast_Z = ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 12)).values - ds_climatology["sbi_depth"].sel(time=(ds_climatology.time.dt.hour == 0)).values
    ds_climatology["diurnal_contrast_Z"] = (("year_month",), diurnal_contrast_Z, {"units": "m", "long_name": "Diurnal Depth Contrast (12Z - 00Z)"})

    ds_climatology.attrs["SiteName"] = site_name
    ds_climatology.to_netcdf(output_location, mode='w')
    return ds_climatology


    




if __name__ == "__main__":


    dataset = xr.open_dataset(r"Data&Model\Radiosonde\NC\71082_daily.nc", chunks={'time': 10})
    radiosonde_monthly_climatology(dataset)


    #radiosonde_climatology(dataset, overwrite=True)
    #era5data = era5_data_load()
    #era5_monthly_data = era5_data_format(era5data) #list with jan,feb,dec data
    #save_results(era5_monthly_data[0],"Data&Model/ERA5data_arctic_jan_results.nc")
    #save_results(era5_monthly_data[1],"Data&Model/ERA5data_arctic_feb_results.nc")
    #save_results(era5_monthly_data[2],"Data&Model/ERA5data_arctic_dec_results.nc")
    
    
