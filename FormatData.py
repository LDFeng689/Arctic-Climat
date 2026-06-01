import xarray as xr

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





if __name__ == "__main__":
        from DownloadData import era5_data_load, era5_sp_data_load
        dataloc = era5_data_load()
        dataloc2 = era5_sp_data_load()
        ds = era5_data_format(dataloc,dataloc2)

        '''
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
        



