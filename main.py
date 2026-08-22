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
    station_numbers = ["71082","04220"] 
   
    for station_number in station_numbers:
        station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number, overwrite=False)
        data_Lack = Plotting.radiosonde_data_count(csvFolder, figFolder, station_number)
        radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, overwrite=True)
        radiosonde_data = Calculation.radiosonde_daily_climatology(radiosonde_data)
        radiosonde_results = Calculation.radiosonde_monthly_climatology(radiosonde_data, data_Lack, overwrite= True)
        print(f"{station_number} completed")
        Plotting.climatology_plots(radiosonde_results,figFolder)
        Plotting.vapor_presence_plot(radiosonde_data,figFolder)


    

def process_era5_site_data():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    figFolder = "Figures/ERA5"
    os.makedirs(figFolder, exist_ok=True)
    station_numbers = ["04220"] #["71082","04220"]
    coordinates = [[68.708, -52.852]] #[[82.493, -62.344],[68.708, -52.852]]
    for station_number, coordinate in zip(station_numbers, coordinates):
        dataFolder = f"Data&Model/ERA5/{station_number}"
        os.makedirs(dataFolder, exist_ok=True)
        print(f"Processing {station_number}")
        exp_coordinates = Calculation.radiosonde_coordinates(os.path.join(csvFolder,station_number), [coordinate[0],coordinate[1],coordinate[0],coordinate[1]])
        print(exp_coordinates)
        #exp_coordinates = [84.7769, -81.5466, 78.6372, -47.5212] #from executing the above code

        surfaceDataHourly = DownloadData.era5_hourly_surface_data_load(exp_coordinates, station_number, overwrite= False)
        levelDataHourly = DownloadData.era5_download(dataset = "reanalysis-era5-pressure-levels",
                                                    product_type= ["reanalysis"],
                                                    variables= ["specific_humidity","temperature"],
                                                    filename = f"Data&Model/ERA5/{station_number}/ERA5_hourly_level_{station_number}_raw.nc", 
                                                    coordinate=exp_coordinates, 
                                                    siteID = station_number,
                                                    overwrite = True)
        
        hourlyData = FormatData.era5_data_format(levelDataHourly, surfaceDataHourly, siteID = station_number, timePeriod = "daily", overwrite=True)
        dailyData = Calculation.era5_daily_climatology(hourlyData, overwrite= True)
        resultsData = Calculation.era5_monthly_climatology(dailyData, overwrite=True)
        Plotting.climatology_plots(resultsData, figFolder)

def one_time(dataset = "radiosonde"):
    if dataset == "radiosonde":
        csvFolder = "Data&Model/Radiosonde/CSV/"
        figFolder = "Figures/Radiosonde"
        station_number = "71082" #"71081"
        station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number, overwrite=False)
        data_Lack = Plotting.radiosonde_data_count(csvFolder, figFolder, station_number)
        radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, overwrite=True)
        radiosonde_data = Calculation.radiosonde_daily_climatology(radiosonde_data)
        radiosonde_results = Calculation.radiosonde_monthly_climatology(radiosonde_data,data_Lack, overwrite= True)
        Plotting.climatology_plots(radiosonde_results, figFolder)

    if dataset == "ERA5":
        csvFolder = "Data&Model/Radiosonde/CSV/"
        figFolder = "Figures/ERA5"
        os.makedirs(figFolder, exist_ok=True)
        station_number = "71082"
        coordinate = [82.493, -62.344]

        dataFolder = f"Data&Model/ERA5/{station_number}"
        os.makedirs(dataFolder, exist_ok=True)
        print(f"Processing {station_number}")
        #exp_coordinates = Calculation.radiosonde_coordinates(os.path.join(csvFolder,station_number), [coordinate[0],coordinate[1],coordinate[0],coordinate[1]])
        #print(exp_coordinates)
        exp_coordinates = [84.7769, -81.5466, 78.6372, -47.5212] #from executing the above code

        surfaceDataHourly = DownloadData.era5_hourly_surface_data_load(exp_coordinates, station_number, overwrite= False)
        levelDataHourly = DownloadData.era5_download(dataset = "reanalysis-era5-pressure-levels",
                                                    product_type= ["reanalysis"],
                                                    variables= ["specific_humidity","temperature"],
                                                    filename = f"Data&Model/ERA5/{station_number}/ERA5_hourly_level_{station_number}_raw.nc", 
                                                    coordinate=exp_coordinates, 
                                                    siteID = station_number,
                                                    overwrite = False)
        
        hourlyData = FormatData.era5_data_format(levelDataHourly, surfaceDataHourly, siteID = station_number, timePeriod = "daily", overwrite=False)
        dailyData = Calculation.era5_daily_climatology(hourlyData, overwrite= True)
        resultsData = Calculation.era5_monthly_climatology(dailyData, overwrite=True)
        Plotting.climatology_plots(resultsData, figFolder)



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

