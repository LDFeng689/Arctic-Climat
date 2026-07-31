import DownloadData
import FormatData
import Calculation
import Plotting
import xarray as xr
import os

def process_era5_data():
    dataset = DownloadData.era5_data_load()
    spData = DownloadData.era5_sp_data_load()
    dataset = FormatData.era5_data_format(dataset,spData)
    figures_folder = "Figures/ERA5/"
    results_folder = "Data&Model/ERA5/Results/"

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



def process_radiosonde_data():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    os.makedirs(csvFolder, exist_ok=True)
    figFolder = "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde"
    os.makedirs(figFolder, exist_ok=True)
    station_numbers = ["71082","71917","71924","04320" ,"01028", "01004"]
    coordinates = [[82.493, -62.344],[79.989,-85.938], [74.705,-94.969],[76.769,-18.672] , [74.504, 19.001], [78.923, 11.923]]


    for station_number,  coordinate in zip(station_numbers,  coordinates):
        station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number)
        radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, coordinate)
        radiosonde_data_res = Calculation.radiosonde_climatology(radiosonde_data)
        print(f"{station_number} completed")
        #Plotting.radiosonde_plots(radiosonde_data_res,figFolder, station_number)
    

def one_time():
    csvFolder = "Data&Model/Radiosonde/CSV/"
    figFolder = "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde"
    station_number = "71924"
    coordinate = [74.705,-94.969]
    station_folder_csv = DownloadData.radiosonde_data_download(csvFolder,station_number, overwrite=True)
    radiosonde_data = FormatData.radiosonde_assemble_to_nc(station_folder_csv, coordinate, overwrite=True)
    radiosonde_results = Calculation.radiosonde_climatology(radiosonde_data, overwrite= True)
    Plotting.radiosonde_plots(radiosonde_results, figFolder, station_number)



if __name__ == "__main__":
    #process_era5_data()
    one_time()
    #process_radiosonde_data()


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

