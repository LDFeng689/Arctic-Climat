import xarray as xr

def era5_data_format(dataloc):
        #load the data
        arcticData = xr.open_dataset(dataloc,  chunks={'time': 10})
        arcticData = arcticData.rename({"valid_time":"time"})
        
        #print(arcticData)

        #separate the data by month
        arcticData_jan = arcticData.sel(time = (arcticData.time.dt.month == 1))
        arcticData_feb = arcticData.sel(time = (arcticData.time.dt.month == 2))
        arcticData_dec = arcticData.sel(time = (arcticData.time.dt.month == 12))
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
        
        return [arcticData_jan, arcticData_feb, arcticData_dec]


if __name__ == "__main__":
        from DownloadData import era5_data_load
        dataloc = era5_data_load()
        era5_data_format(dataloc)
