import DownloadData
import FormatData
import Calculation
import Plotting
import xarray as xr
import os

def process_era5_data():
    dataset = DownloadData.era5_monthly_level_data_load()
    spData = DownloadData.era5_monthly_surface_data_load()
    dataset = FormatData.era5_data_format1(dataset,spData)
    figures_folder = "Figures/ERA5/arctic"
    results_folder = "Data&Model/ERA5/arctic/results/"

    #OBTAINING THE RESULTING DATASETS
    results = []
    file_locations = []

    months = ["dec","jan","feb"]
    filenames = [f"{results_folder}Arctic_{month}_results.nc" for month in months]
    for i in range(len(dataset)):
        #dec,jan,feb
        result, location = Calculation.Era5_save_results(dataset[i],filenames[i])
        results.append(result)
        file_locations.append(location)

    #CALCULATING ZONAL DATA    
    Greenland_result, Greenland_filename = Calculation.calculate_zonal_averages(results[2],90,83,-100,0,"Greenland_feb",results_folder)
    ChukchiSea_result, ChukchiSea_filename = Calculation.calculate_zonal_averages(results[0],75,69,-180,-150,"ChukchiSea_dec",results_folder)
    

    #PLOTTING ZONAL DATA
    Plotting.era5_vertical_plot(ChukchiSea_result, figures_folder,description= "ChukchiSea" ,month="December")
    Plotting.era5_timeseries_plot(ChukchiSea_result, figures_folder, description= "ChukchiSea", month="December")
    Plotting.era5_vertical_plot(Greenland_result, figures_folder,description= "Greenland" ,month="February")
    Plotting.era5_timeseries_plot(Greenland_result, figures_folder, description= "Greenland", month="February")
 

    #PLOTTING THE AVERAGE INTENSITY,DEPTH AND THEIR TRENDS ON THE ARCTIC CIRCLE
    Plotting.era5_monthly_globe_plot(results,figures_folder)


    #PLOTTING THE VERTICAL AND TIMESERIES PLOTS FOR THE 4 POINTS OF INTERESTS
    pts_of_interest = Calculation.find_trend_extremum(results, showPoints=False)
 

    for point in pts_of_interest:  #error around here
        if point[3] == "January":
            data = results[1].sel(latitude = point[1],longitude = point[2])
        elif point[3] == "February":
            data = results[2].sel(latitude = point[1],longitude = point[2])
        elif point[3] == "December":
            data = results[0].sel(latitude = point[1],longitude = point[2])
        else:
            raise Exception("Point of interest is in the wrong month")
        Plotting.vertical_plot(data, figures_folder, description= point[0], month= point[3])
        Plotting.timeseries_plot(data, figures_folder, description= point[0], month=point[3])
    
    print("DONE")

#ABOVE WERE FIRST ATTEMPS OF RECREATING RESULTS, BELOW IS THE ACTUALLY USED CODES 

def process_radiosonde_data():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    os.makedirs(csvFolder, exist_ok=True)
    figFolder = "Figures/Radiosonde"
    os.makedirs(figFolder, exist_ok=True)
    station_numbers = ["71082","71917","71924","04320" ,"01028", "01004"]
    coordinates = [[82.493, -62.344],[79.989,-85.938], [74.705,-94.969],[76.769,-18.672] , [74.504, 19.001], [78.923, 11.923]]


    for station_number,  coordinate in zip(station_numbers,  coordinates):
        station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number)
        radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, coordinate)
        radiosonde_data_res = Calculation.radiosonde_climatology(radiosonde_data)
        print(f"{station_number} completed")
        Plotting.climatology_plots(radiosonde_data_res,figFolder)
    

def process_era5_site_data():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    figFolder = "Figures/ERA5"
    station_number = "71082"
    coordinate = [82.493, -62.344]
    dataFolder = f"Data&Model\ERA5/{station_number}"
    os.makedirs(dataFolder, exist_ok=True)

    #exp_coordinates = Calculation.radiosonde_coordinates(os.path.join(csvFolder,station_number), [coordinate[0],coordinate[1],coordinate[0],coordinate[1]])
    #print(exp_coordinates)
    exp_coordinates = [84.7769, -81.5466, 78.6372, -47.5212] #from executing the above code

    #levelDataHourly = DownloadData.era5_hourly_level_data_load(exp_coordinates, station_number)
    surfaceDataHourly = DownloadData.era5_hourly_surface_data_load(exp_coordinates, station_number)
    #levelDataMonthly = DownloadData.era5_monthly_level_data_load(exp_coordinates, station_number)
    surfaceDataMonthly = DownloadData.era5_monthly_surface_data_load(exp_coordinates, station_number)

    #Longer downloading process because the files are too big
    levelDataHourly = DownloadData.era5_download(dataset = "reanalysis-era5-pressure-levels",
                                                 product_type= ["reanalysis"],
                                                 variables= ["specific_humidity","temperature"],
                                                 filename = f"Data&Model/ERA5/{station_number}/ERA5_hourly_level_{station_number}_raw.nc", 
                                                 coordinate=exp_coordinates, 
                                                 siteID = station_number,
                                                 monthly= False,
                                                 surface = False)
    
    levelDataMonthly = DownloadData.era5_download(dataset = "reanalysis-era5-pressure-levels-monthly-means",
                                                 product_type= ["monthly_averaged_reanalysis_by_hour_of_day"],
                                                 variables= ["specific_humidity","temperature"],
                                                 filename = f"Data&Model/ERA5/{station_number}/ERA5_monthly_level_{station_number}_raw.nc", 
                                                 coordinate=exp_coordinates, 
                                                 siteID = station_number,
                                                 surface = False)

    """
    surfaceDataMonthly = DownloadData.era5_download(dataset = "reanalysis-era5-single-levels-monthly-means_by_hour_of_day",
                                                 product_type= ["monthly_averaged_reanalysis"],
                                                 variables= ["surface_pressure", "2m_temperature"],
                                                 filename = f"Data&Model/ERA5/{station_number}/ERA5_monthly_surface_{station_number}_raw.nc", 
                                                 coordinate=exp_coordinates, 
                                                 siteID = station_number)
    surfaceDataHourly = DownloadData.era5_download(dataset = "reanalysis-era5-single-levels",
                                                     product_type= ["reanalysis"],
                                                     variables= ["2m_temperature","surface_pressure"],
                                                     filename = f"Data&Model/ERA5/{station_number}/ERA5_hourly_surface_{station_number}_raw.nc", 
                                                     coordinate=exp_coordinates, 
                                                     siteID = station_number,
                                                     monthly= False)
    """
    monthlyData = FormatData.era5_data_format(levelDataMonthly, surfaceDataMonthly, siteID = station_number, timePeriod = "monthly")
    hourlyData = FormatData.era5_data_format(levelDataHourly, surfaceDataHourly, siteID = station_number, timePeriod = "hourly")

    resultsData = Calculation.era5_monthly_climatology(hourlyData, monthlyData, station_number, overwrite= True)
    Plotting.climatology_plots(resultsData, figFolder)

def one_time():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    figFolder = "Figures/Radiosonde"
    station_number = "71082" #"04220"
    coordinate = [82.493, -62.344] #[68.708,-52.852]
    station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number, overwrite=False)
    radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, coordinate, overwrite=True)
    radiosonde_results = Calculation.radiosonde_climatology(radiosonde_data, overwrite= True)
    Plotting.climatology_plots(radiosonde_results, figFolder)



if __name__ == "__main__":
    #process_era5_data()
    one_time()
    #process_radiosonde_data()
    #process_era5_site_data()


'''
    results_folder = "Figures/ERA5/"
    
    pts_of_interest = Calculation.find_trend_extremum(datasets)
    for point in pts_of_interest:
        if point[3] == "January":
            data = datasets[1].sel(latitude = point[1],longitude = point[2])
        elif point[3] == "February":
            data = datasets[2].sel(latitude = point[1],longitude = point[2])
        elif point[3] == "December":
            data = datasets[0].sel(latitude = point[1],longitude = point[2])
        else:
            raise Exception("Point of interest is in the wrong month")
        Plotting.vertical_plot(data, results_folder, point[0],point[3])
        Plotting.timeseries_plot(data, point[3],point[0], results_folder)

    Plotting.era5_monthly_globe_plot(datasets,results_folder)
'''    
    #greenland_result, greenland_filename = Calculation.calculate_zonal_averages(datasets[1],90,83,100,0,"Greenland")
    #ChukchiSea_result, ChukchiSea_filename = Calculation.calculate_zonal_averages(datasets[2],75,69,180,150,"ChukchiSea")
    #datasets[0].intensityTrend.to_pandas().to_csv("check.csv",index=True)
    #Calculation.find_trend_extremum(datasets)
    #print(datasets[1].depthTrend.sel(latitude =69, longitude=179.5).values)

    #point = datasets[0].sel(latitude = 67.5, longitude = 135.5)
    #Plotting.vertical_plot(point, "ERA5")
    #Plotting.timeseries_plot(datasets[0],67.5,135.5)
    #Plotting.era5_monthly_globe_plot(datasets,"Results/ERA5/")

