import xarray as xr
import numpy as np
import os
from scipy import stats

def find_inversion_depth_intensity(dataset):
    # 1. Create the lightweight container for your final Xarray output
    results = xr.Dataset(
        coords={
            "time": dataset.time, 
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

    # 3. Pre-allocate empty NumPy arrays for the outputs
    shape = (len(times), len(lats), len(lons))
    out_intensity = np.full(shape, np.nan, dtype='float32')
    out_depth = np.full(shape, np.nan, dtype='float32')
    out_surface_temp = np.full(shape, np.nan, dtype='float32')
    out_inversion_top = np.full(shape, np.nan, dtype='float32')
    out_inversion_top_p = np.full(shape, np.nan, dtype='float32')

    # Constants 
    Rd = 287.05 
    g = 9.81    

    # 4. Process using raw index tracking (Extremely fast in NumPy)
    for t_idx in range(len(times)):
        #print(f"Processing time index: {t_idx+1} / {len(times)}")
        
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
                
                # Base Surface conditions at the first pressure index [0]
                P1 = p_levels[0]
                T1 = t_array[t_idx, 0, lat_idx, lon_idx]
                H1 = q_array[t_idx, 0, lat_idx, lon_idx]
                
                sfc_temp = T1
                current_depth = 0.0
                inv_top_temp = np.nan
                inv_top_p = np.nan

                # Search vertically upward through the indices of the pressure levels
                for p_idx in range(1, len(p_levels)):
                    P2 = p_levels[p_idx]
                    T2 = t_array[t_idx, p_idx, lat_idx, lon_idx]
                    H2 = q_array[t_idx, p_idx, lat_idx, lon_idx]
                    
                    if T1 >= T2:
                        # Inversion peak located
                        inv_top_temp = T1
                        inv_top_p = p_levels[p_idx - 1] # Level below current is the max
                        break
                    else:
                        # Inversion layer continues; calculate layer thickness
                        Tavg = (T1 + T2) / 2.0
                        Havg = (H1 + H2) / 2.0
                        logp = np.log(P1 / P2)
                        
                        current_depth += (Rd * (1.0 + 0.608 * Havg) * Tavg * logp) / g
                        
                        # Advance pointers up to the next layer
                        T1, H1, P1 = T2, H2, P2

                # Store directly into the allocated NumPy arrays via indices
                out_surface_temp[t_idx, lat_idx, lon_idx] = sfc_temp
                out_inversion_top[t_idx, lat_idx, lon_idx] = inv_top_temp
                out_inversion_top_p[t_idx, lat_idx, lon_idx] = inv_top_p
                out_depth[t_idx, lat_idx, lon_idx] = current_depth
                out_intensity[t_idx, lat_idx, lon_idx] = inv_top_temp - sfc_temp

    # 5. Package the completed NumPy arrays back into the final Xarray Dataset
    dims = ["time", "latitude", "longitude"]
    results["intensity"] = (dims, out_intensity)
    results["depth"] = (dims, out_depth)
    results["surface_temp"] = (dims, out_surface_temp)
    results["inversion_top"] = (dims, out_inversion_top)
    results["inversion_top_pressurelv"] = (dims, out_inversion_top_p)

    # Re-apply scientific Metadata
    results.intensity.attrs = {'units': 'K', 'long_name': 'Inversion Temperature Intensity'}
    results.depth.attrs = {'units': 'm', 'long_name': 'Inversion Layer Thickness'}
    results.surface_temp.attrs = {'units': 'K', 'long_name': 'Surface temperature'}
    results.inversion_top.attrs = {'units': 'K', 'long_name': 'Inversion top temperature'}
    results.inversion_top_pressurelv.attrs = {'units': 'hPa', 'long_name': 'Inversion top pressure level'}

    return results

def find_trend(dataset):
    #Change the time coordinate to only be in years
    years = dataset.time.dt.year.values
    dataset = dataset.assign_coords(time = years)
    #Coordinate arrays
    latitudes = dataset.latitude.values
    longitudes = dataset.longitude.values
    times = dataset.time.values


    #Variable array with (time,lat,lon) dimensions
    intensities = dataset.intensity.values
    depths = dataset.depth.values

    #Pre-allocate empty numpy arrays for the outputs
    shape = (len(latitudes),len(longitudes))
    out_intensityTrend = np.full(shape,np.nan,dtype="float32")
    out_depthTrend = np.full(shape,np.nan,dtype="float32")


    for lat_idx in range(len(latitudes)):
        for lon_idx in range(len(longitudes)):
            slopeI, interceptI, rI, pI, seI = stats.linregress(times, intensities[:,lat_idx,lon_idx])
            slopeD, interceptD, rD, pD, seD = stats.linregress(times, depths[:,lat_idx,lon_idx])
            out_intensityTrend[lat_idx,lon_idx] = slopeI
            out_depthTrend[lat_idx,lon_idx] = slopeD
    
    dims = ["latitude","longitude"]
    dataset["intensityTrend"] = (dims, out_intensityTrend)
    dataset["depthTrend"] = (dims,out_depthTrend)

    dataset.intensityTrend.attrs = {"units": "K/decade", "long_name": "Trend in Inversion Intensity"}
    dataset.depthTrend.attrs = {"units": "m/decade", "long_name": "Trend in Inversion Depth"}
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
    result = find_inversion_depth_intensity(dataset)
    result = find_trend(result)
    result = calculate_monthly_averages(result)
    result.to_netcdf(location, mode='w')


if __name__ == "__main__":
    from DownloadData import era5_data_load
    from FormatData import era5_data_format
    era5data = era5_data_load()
    era5_monthly_data = era5_data_format(era5data) #list with jan,feb,dec data
    jan_results = find_inversion_depth_intensity(era5_monthly_data[0])
    jan_results = find_trend(jan_results)
    jan_results = calculate_monthly_averages(jan_results)
    jan_results.to_netcdf("D:/McGill/Atoc396/ArcticClimat/Data&Model/ERA5data_arctic_jan_results.nc", mode = 'w')
    
    
