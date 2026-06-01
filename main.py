import DownloadData
import FormatData
import Calculation
import Plotting
import xarray as xr

def process_era5_data():
    dataset = DownloadData.era5_data_load()
    spData = DownloadData.era5_sp_data_load()
    dataset = FormatData.era5_data_format(dataset,spData)
    figures_folder = "Figures/ERA5/"
    results_folder = "Data&Model/ERA5/"

    #OBTAINING THE RESULTING DATASETS
    results = []
    file_locations = []

    months = ["dec","jan","feb"]
    filenames = [f"{results_folder}Arctic_{month}_results.nc" for month in months]
    for i in range(len(dataset)):
        #dec,jan,feb
        result, location = Calculation.save_results(dataset[i],filenames[i])
        results.append(result)
        file_locations.append(location)

    #CALCULATING ZONAL DATA    
    Greenland_result, Greenland_filename = Calculation.calculate_zonal_averages(results[2],90,83,100,0,"Greenland_feb",results_folder)
    ChukchiSea_result, ChukchiSea_filename = Calculation.calculate_zonal_averages(results[0],75,69,180,150,"ChukchiSea_dec",results_folder)
    

    #PLOTTING ZONAL DATA
    Plotting.vertical_plot(ChukchiSea_result, figures_folder,description= "ChukchiSea" ,month="December")
    Plotting.timeseries_plot(ChukchiSea_result, figures_folder, description= "ChukchiSea", month="December")
    Plotting.vertical_plot(Greenland_result, figures_folder,description= "Greenland" ,month="February")
    Plotting.timeseries_plot(Greenland_result, figures_folder, description= "Greenland", month="February")
 

    #PLOTTING THE AVERAGE INTENSITY,DEPTH AND THEIR TRENDS ON THE ARCTIC CIRCLE
    Plotting.era5_monthly_globe_plot(results,figures_folder)


    #PLOTTING THE VERTICAL AND TIMESERIES PLOTS FOR THE 4 POINTS OF INTERESTS
    pts_of_interest = Calculation.find_trend_extremum(results, showPoints=True)
 

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


def one_time():
    paths = ["Data&Model/ERA5/Arctic_dec_results.nc",
            "Data&Model/ERA5/Arctic_jan_results.nc",
             "Data&Model/ERA5/Arctic_feb_results.nc"]
    datasets = []
    figures_folder = "Figures/ERA5/"
    results_folder = "Data&Model/ERA5/"
    for path in paths:
        datasets.append(xr.open_dataset(path,  chunks={'time': 10}))
    #Calculation.find_trend_extremum(datasets, showPoints=True)
    


    """

    test_folder = "TEST/"
    #for path in paths:
    #    datasets.append(xr.open_dataset(path,  chunks={'time': 10}))

    dataset = DownloadData.era5_data_load()
    dataset = FormatData.era5_data_format(dataset)
    result, location = Calculation.save_results(dataset[2],f"{test_folder}Arctic_feb_results.nc")
    
    results = [result]
    Plotting.era5_monthly_globe_plot(results,figures_folder)
    pts_of_interest = Calculation.find_trend_extremum(results)
    for point in pts_of_interest:
        data = result.sel(latitude = point[1],longitude = point[2])
        Plotting.vertical_plot(data, figures_folder, description= point[0], month= point[3])
        Plotting.timeseries_plot(data, figures_folder, description= point[0], month=point[3])

    """




if __name__ == "__main__":
    process_era5_data()
    #one_time()


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

