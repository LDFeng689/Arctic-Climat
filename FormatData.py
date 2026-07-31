import xarray as xr
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

def era5_data_format(dataloc, spData):
        #load the data
        arcticData = xr.open_dataset(dataloc,  chunks={'time': 10})
        arcticData = arcticData.rename({"valid_time":"time"})
        arcticData = arcticData.sel(time =slice('1979','2014'))

        #separate the data by month
        arcticData_jan = arcticData.sel(time = (arcticData.time.dt.month == 1))
        arcticData_feb = arcticData.sel(time = (arcticData.time.dt.month == 2))
        arcticData_dec = arcticData.sel(time = (arcticData.time.dt.month == 12))

        datasets = [arcticData_dec, arcticData_jan, arcticData_feb]

        # Rebuild the list with the updated coordinate copies
        datasets = [ds.assign_coords(time=ds.time.dt.year.values) for ds in datasets]

        # Unpack them back into your monthly variables
        arcticData_jan, arcticData_feb, arcticData_dec = datasets


        #Add meta data for months since now all the time data are in years
        datasets[0].attrs["Month"] = "December"
        datasets[1].attrs["Month"] = "January"
        datasets[2].attrs["Month"] = "February"
        
        spDatasets = era5_sp_data_format(spData)

        arcticDatasets = []
        #merge datasets
        for arcticData, spData in zip(datasets, spDatasets):
                ds = xr.merge([arcticData,spData], compat="override")
                arcticDatasets.append(ds)

        #print(arcticDatasets[0])
        print("ERA5 Datasets Formatted")
        return arcticDatasets

def era5_sp_data_format(dataloc):
        spData = xr.open_dataset(dataloc, engine = "netcdf4" ,chunks={'time': 10})
        
        spData = spData.rename({"valid_time":"time"})   #tbd
        spData = spData.sel(time =slice('1979','2014'))

        #Change the surface pressure levels from pa to hpa
        spData.sp.values = spData.sp.values/100


        #separate the data by month
        spData_jan = spData.sel(time = (spData.time.dt.month == 1))
        spData_feb = spData.sel(time = (spData.time.dt.month == 2))
        spData_dec = spData.sel(time = (spData.time.dt.month == 12))

        datasets = [spData_dec, spData_jan, spData_feb]

        # Rebuild the list with the updated coordinate copies
        datasets = [ds.assign_coords(time=ds.time.dt.year.values) for ds in datasets]

        # Unpack them back into your monthly variables
        spData_jan, spData_feb, spData_dec = datasets

        #Add meta data for months since now all the time data are in years
        datasets[0].attrs["Month"] = "December"
        datasets[1].attrs["Month"] = "January"
        datasets[2].attrs["Month"] = "February"

        return datasets

def radiosonde_assemble_to_nc(csvFolder,coords = ["latitude", "longitude"], overwrite =False):
        years = [f for f in os.listdir(csvFolder) if os.path.isdir(os.path.join(csvFolder,f))]
        monthsN = ["Dec", "Jan", "Feb"]
        monthsI = ["12", "01","02"]
        site_name = os.path.basename(csvFolder)
        
        
        ncFolder = f"Data&Model/Radiosonde/NC"
        os.makedirs(ncFolder, exist_ok=True)
        location = f"{ncFolder}/{site_name}.nc"
        

        if os.path.isfile(location) and overwrite == False:    #Skip if already exist and don't want to do changes to it
                print(f"{site_name} NC file already assembled")
                ds = xr.open_dataset(location)
                return ds
        print(f"Assembling NC file for {site_name}")

        yearlyDailyData = []
        yearlyMonthlyData = []

        for monthI,monthN in zip(monthsI,monthsN):
                

                for year in years:
                        month_path = os.path.join(csvFolder, year, monthN)
                        if not os.path.isdir(month_path):
                                continue
                        
                        monthly_avg_data, daily_data = radiosonde_monthly_average(month_path, int(year), int(monthI))
                        yearlyMonthlyData.append(monthly_avg_data)
                        yearlyDailyData.append(daily_data)
                if not yearlyMonthlyData:
                        continue
                print(f"{monthN} done")

        daily = xr.concat(yearlyDailyData, dim = 'time', data_vars="all", coords="minimal",combine_attrs="override")
        monthly = xr.concat(yearlyMonthlyData, dim = 'time_monthly', data_vars="all", coords="minimal",combine_attrs="override")
        monthly_renamed = monthly.rename_vars({
                v: f"{v}_monthly" for v in monthly.data_vars if v != "time_monthly"
        })

        ds = xr.merge([monthly_renamed,daily], combine_attrs="drop_conflicts")    
        #ds.attrs["Month"] = month #Add metadata for corresponding month in the nc file
        ds.attrs["SiteName"] = site_name
        ds = ds.assign_coords(coordinates = coords)
        ds['coordinates'].attrs["Description"] = "[Latitude,Longitude]"    


        for var in ds.data_vars:
        # If variable is stored as an object array, force convert it to float
                if ds[var].dtype == object:
                        # Convert values using pd.to_numeric
                        cleaned_vals = pd.to_numeric(ds[var].values.ravel(), errors='coerce').reshape(ds[var].shape)
                        ds[var] = (ds[var].dims, cleaned_vals)
                #Turn all temperature values into kelvin
                if 'temp' in var.lower():
                        ds[var] = ds[var] + 273.15
                        ds[var].attrs["units"] = "K"




        ds = ds.dropna(dim="pressure", how="all")  #See if it fixes things
        ds.to_netcdf(location, mode='w')   
        return ds
        

def radiosonde_monthly_average(monthlyFolder, year, month):
        csvFiles = [os.path.join (monthlyFolder, file) for file in os.listdir(monthlyFolder) if file.endswith(".csv") and os.path.isfile(os.path.join(monthlyFolder, file))]

        unwanted_dims = ["time","longitude","latitude"]
        target_pressures = [1000.0, 975.0, 950.0, 925.0, 900.0, 875.0, 850.0, 825.0, 800.0, 775.0,
                                750.0, 700.0, 650.0, 600.0, 550.0, 500.0, 450.0, 400.0, 350.0, 300.0,
                                250.0, 225.0, 200.0, 175.0, 150.0, 125.0, 100.0, 70.0, 50.0, 30.0,
                                20.0,  10.0,   7.0,   5.0,   3.0,   2.0,   1.0]
        # 1. Define your name clean-up mapping
        rename_dict = {
        "pressure_hPa": "pressure",
        "geopotential height_m": "geopotential_height",
        "temperature_C": "temperature",
        "dew point temperature_C": "dew_point",
        "ice point temperature_C": "ice_point",
        "relative humidity_%": "relative_humidity",
        "humidity wrt ice_%": "humidity_wrt_ice",
        "mixing ratio_g/kg": "mixing_ratio",
        "wind direction_degree": "wind_direction",
        "wind speed_m/s": "wind_speed"
        }

        # 2. Define the corresponding units for attributes
        units_dict = {
        "pressure": "hPa",
        "geopotential_height": "m",
        "temperature": "degree_Celsius",
        "dew_point": "degree_Celsius",
        "ice_point": "degree_Celsius",
        "relative_humidity": "%",
        "humidity_wrt_ice": "%",
        "mixing_ratio": "g/kg",
        "wind_direction": "degrees",
        "wind_speed": "m/s"
        }
        dailyData = []
        for csvFile in csvFiles:
                #Initial load and cleaning of the csv
                data = pd.read_csv(csvFile)
                data = data.drop(columns = unwanted_dims, errors = 'ignore')
                data = data.rename(columns=rename_dict)
                data = data.drop_duplicates(subset=["pressure"], keep="first")
                data = data.set_index("pressure")

                #Turn to Xarray and interpolate over pressure levels
                ds = data.to_xarray()
                ds = ds.interp(pressure = target_pressures, method = 'linear')

                #obtain the time values
                
                filename = Path(csvFile).stem
                
                day, hour = filename.split("_")
                ds = ds.expand_dims(time = [datetime(int(year),int(month),int(day),int(hour))])

                #Add metadata to the variables
                for var_name, unit in units_dict.items():
                        if var_name in ds:
                                ds[var_name].attrs["units"] = unit

                        # Also tag the pressure coordinate axis attributes
                        ds["pressure"].attrs["units"] = "hPa"
                        ds["pressure"].attrs["standard_name"] = "air_pressure"
                dailyData.append(ds)


        daily_dataset = xr.concat(dailyData, dim= "time", data_vars="all", coords="all", combine_attrs="override")  #concat to a new "day" dimensions that will disappear when averaging
        monthly_data = daily_dataset.groupby("time.hour").mean(dim = "time", keep_attrs = True)
        new_timestamps = [
        datetime(year, month, 1, h) for h in monthly_data["hour"].values
        ]

        # 3. Attach the new timestamps and swap the dimension name to 'time_monthly'
        monthly_data = (
                monthly_data
                .assign_coords(time_monthly=("hour", new_timestamps))  # Attach new coordinate
                .swap_dims({"hour": "time_monthly"})                  # Set it as the primary dimension
                .drop_vars("hour")                                    # Drop the old 'hour' coordinate
                )

        return monthly_data, daily_dataset
        
#now need to figure out the time indices

               




if __name__ == "__main__":
        radiosonde_assemble_to_nc("D:/McGill/Atoc396/ArcticClimat/Data&Model/Radiosonde/CSV/71917", [79.989,-85.938], overwrite=True)



        '''
        from DownloadData import era5_data_load, era5_sp_data_load
        dataloc = era5_data_load()
        dataloc2 = era5_sp_data_load()
        ds = era5_data_format(dataloc,dataloc2)

        
        jan = ds[1]
        print(jan.sp.sel(time= 1990, 
                        #pressure_level=1000, 
                        latitude=70,
                        longitude = 0,
                        method = 'nearest').values)
        #print(jan.attrs['Month'])
        
        '''
#pressurelv = arcticData_jan.isobaricInhPa.values


"""

#how to access the latitude, longitudes, time, pressure levels
latitudes = arcticData.latitude.values
longitudes = arcticData.longitude.values
times = arcticData_jan.time.values
pressurelvs = arcticData_jan.pressure_level.values

#problem can't access specific values if im in the month divided subdataset

#how to access a specific value of temperature or specific humidity
temp = arcticData_jan.t.sel(time= times[0], 
                        pressure_level=850, 
                        latitude=70,
                        longitude = 0,
                        #method = 'nearest'
        ).values
print(temp)
"""
        



