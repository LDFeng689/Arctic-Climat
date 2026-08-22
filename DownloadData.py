import cdsapi
import xarray as xr
import os
import requests
import numpy as np
import time
import pandas as pd
from datetime import datetime
from urllib3.util.retry import Retry

def radiosonde_data_download(csvFolder, station_number, overwrite = False):

    station_path = os.path.join(csvFolder, station_number)
    
    if os.path.isdir(station_path) and overwrite == False:    #Skip if already exist and don't want to do changes to it
        print(f"{station_number} radiosonde data already downloaded")
        return station_path
    else:
        os.makedirs(station_path, exist_ok=True)
        print(f"Downloading radiosonde data for {station_number}")



    start_year = 1978 #normally from 1978 1977 only has DEC
    end_year =2025
    years = np.linspace(start_year,end_year, num = end_year-start_year+1 ).astype(int).astype(str)

    monthsInt = ["12","01","02"]
    monthsName = ['Dec','Jan','Feb']
    days = [f"{x:02d}" for x in range(1, 32) ]
    #0000 is 12 UTC, 2000 is 00 UTC
    hoursCode = ["2000","2012"]
    hours = ["00","12"]

    session = requests.Session()
    retries = Retry(
        total=5,                  # Retry 5 times
        connect=3,                # Retry up to 3 times on connection/handshake failure
        read=3,                   # Retry up to 3 times on read timeouts 
        backoff_factor=2,         # Wait 2s, 4s, 8s between retries
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
    

    #Create the error message file
    timeoutDates = f"Data&Model/Radiosonde/{station_number}timeoutDates.txt"
    try:
        with open(timeoutDates, "w", encoding="utf-8") as file:
            pass
        print("timeoutDates.txt file created successfully!")
    except FileExistsError:
        print("timeoutDates.txt already exists.")

    for year in years:
        year_path = os.path.join(station_path, year)
        os.makedirs(year_path, exist_ok=True)

        if int(year) >= 2018:
            source = "BUFR"
        else:
            source = "FM35"

        for monthI, monthN in zip(monthsInt, monthsName):
            month_path = os.path.join(year_path, monthN)
            os.makedirs(month_path, exist_ok=True)

            for day in days:
                for hour, hourc in zip(hours, hoursCode):
                    website = f"https://weather.uwyo.edu/wsgi/sounding?datetime={year}-{monthI}-{day}%{hourc}:00:00&id={station_number}&type=TEXT:CSV&src={source}"
                    csv_file = os.path.join(month_path, f"{day}_{hour}.csv")

                    if os.path.isfile(csv_file):
                        #so that i don't need to rerun the whole program for some missing ones
                        continue
                    
                    try:
                        # Send a GET request to the URL
                        response = session.get(website, timeout = (5,30))

                        # Check if the download link was successful (Status Code 200)
                        if response.status_code == 200:
                            # Open a local file in 'write binary' (wb) mode
                            with open(csv_file, "wb") as file:
                                file.write(response.content)
                            #print(f"Download complete: {station_number}/{monthN}/{year}/{day}_{hour}.csv")

                            time.sleep(1)
                        else:
                            if response.status_code != 404 and response.status_code != 500 and response.status_code != 400:   #only want to know the real errors not a this data does not exist
                                with open(timeoutDates, 'a', encoding = 'utf-8') as file:
                                    file.write(f"Failed to download file {station_number}/{monthN}/{year}/{day}_{hour}.csv. Status code: {response.status_code}\n")
                                #print(f"Failed to download file {station_number}/{monthN}/{year}/{day}_{hour}.csv. Status code: {response.status_code}")

                    except requests.RequestException as e:
                        # 4. Catch connection failures, timeouts, or bad status codes
                        with open(timeoutDates, 'a', encoding = 'utf-8') as file:
                                file.write(f"Skipping {website} due to error: {e}\n")
                        #print(f"Skipping {website} due to error: {e}")



            # --- CLEANUP STEP 1: Check and delete the month folder if all year subdirectories are missing ---
            if len(os.listdir(month_path)) == 0:
                os.rmdir(month_path)
                #print(f"Removed empty month directory: {month_path}")

        # --- CLEANUP STEP 2: Check and delete the year folder if it stayed empty ---
        if len(os.listdir(year_path)) == 0:
            os.rmdir(year_path)
            #print(f"Removed empty year directory: {year_path}")
    return station_path

def era5_hourly_level_data_load(coordinate= [90, -180, 66.5, 180], siteID = "arctic"):
    filename = f"Data&Model/ERA5/{siteID}/ERA5_hourly_level_{siteID}_raw.nc"
    
    #2 if statement to check if the data is already downloaded or converted to nc
    if os.path.isfile(filename):
        print(f"ERA5 {siteID} Dataset present")
        return filename
        #API download request
    else:
        print("Downloading hourly level data")
        dataset = "reanalysis-era5-pressure-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable": [
                "specific_humidity",
                "temperature"
            ],
            "year": [
                "1978",
                "1979", "1980", "1981",
                "1982", "1983", "1984",
                "1985", "1986", "1987",
                "1988", "1989", "1990",
                "1991", "1992", "1993",
                "1994", "1995", "1996",
                "1997", "1998", "1999",
                "2000", "2001", "2002",
                "2003", "2004", "2005",
                "2006", "2007", "2008",
                "2009", "2010", "2011",
                "2012", "2013", "2014",
                "2015", "2016", "2017",
                "2018", "2019", "2020",
                "2021", "2022", "2023",
                "2024", "2025"
            ],
        "month": ["01", "02", "12"],
        "day": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12",
            "13", "14", "15",
            "16", "17", "18",
            "19", "20", "21",
            "22", "23", "24",
            "25", "26", "27",
            "28", "29", "30",
            "31"
        ],
        "time": ["00:00", "12:00"],
        "pressure_level": [
            "1", "2", "3",
            "5", "7", "10",
            "20", "30", "50",
            "70", "100", "125",
            "150", "175", "200",
            "225", "250", "300",
            "350", "400", "450",
            "500", "550", "600",
            "650", "700", "750",
            "775", "800", "825",
            "850", "875", "900",
            "925", "950", "975",
            "1000"
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": coordinate
    }
        client = cdsapi.Client()
        client.retrieve(dataset, request).download(filename)

    return filename

def era5_hourly_surface_data_load(coordinate= [90, -180, 66.5, 180], siteID = "arctic", overwrite = False):
    filename = f"Data&Model/ERA5/{siteID}/ERA5_hourly_surface_{siteID}_raw.nc"

    #2 if statement to check if the data is already downloaded or converted to nc
    if os.path.isfile(filename) and overwrite == False:
        print(f"ERA5 {siteID} Hourly Surface Data present")
        return filename
        #API download request
    else:
        print("Downloading hourly surface data")
        dataset = "reanalysis-era5-single-levels"
        request = {
            "product_type": ["reanalysis"],
            "variable": [
                "2m_temperature",
                "surface_pressure",
            ],
            "year": [
                "1978",
                "1979", "1980", "1981",
                "1982", "1983", "1984",
                "1985", "1986", "1987",
                "1988", "1989", "1990",
                "1991", "1992", "1993",
                "1994", "1995", "1996",
                "1997", "1998", "1999",
                "2000", "2001", "2002",
                "2003", "2004", "2005",
                "2006", "2007", "2008",
                "2009", "2010", "2011",
                "2012", "2013", "2014",
                "2015", "2016", "2017",
                "2018", "2019", "2020",
                "2021", "2022", "2023",
                "2024", "2025"
            ],
            "month": ["01", "02", "12"],
            "day": [
                "01", "02", "03",
                "04", "05", "06",
                "07", "08", "09",
                "10", "11", "12",
                "13", "14", "15",
                "16", "17", "18",
                "19", "20", "21",
                "22", "23", "24",
                "25", "26", "27",
                "28", "29", "30",
                "31"
            ],
            "time": ["00:00", "12:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": coordinate
        }
        client = cdsapi.Client()
        client.retrieve(dataset, request).download(filename)
    return filename


def era5_download(dataset, product_type, variables, filename, coordinate=[90, -180, 66.5, 180], siteID="arctic", overwrite = False):
    if os.path.isfile(filename) and overwrite == False:
        print(f"{dataset} Data present")
        return filename
    client = cdsapi.Client()
    os.makedirs("Data&Model/temp", exist_ok=True)
    
    start_year = 1977
    end_year = 2025
    months_to_download = ["01", "02", "12"]
    
    all_years = [str(y) for y in range(start_year, end_year + 1)]
    temp_files = []

    #Create the error message file
    timeoutDates = f"Data&Model/ERA5/{siteID}_{product_type}_timeoutDates.txt"
    try:
        with open(timeoutDates, "w", encoding="utf-8") as file:
            pass
        print("timeoutDates.txt file created successfully!")
    except FileExistsError:
        print("timeoutDates.txt already exists.")
    
    print(f"=== Step 1: Downloading ERA5 Data {dataset} (Year & Month Granularity) ===")
    
    # Iterate through years
    for yr in all_years:
        # Iterate through months individually
        for mth in months_to_download:
            chunk_str = f"{yr}_{mth}"
            chunk_filename = f"Data&Model/temp/temp_era5_{siteID}_{chunk_str}.nc"
            temp_files.append(chunk_filename)
            
            # Skip download if chunk file already exists locally
            if os.path.exists(chunk_filename):
                print(f"File {chunk_filename} already exists. Skipping download.")
                continue
                
            print(f"Downloading: Year {yr}, Month {mth}...")



            request = {
                        "product_type": product_type,
                        "variable": variables,
                        "year": [yr],
                        "month": [mth],  # Single month request
                        "day": [
                            "01", "02", "03",
                            "04", "05", "06",
                            "07", "08", "09",
                            "10", "11", "12",
                            "13", "14", "15",
                            "16", "17", "18",
                            "19", "20", "21",
                            "22", "23", "24",
                            "25", "26", "27",
                            "28", "29", "30",
                            "31"
                        ],                            
                        "time": ["00:00", "12:00"],
                        "pressure_level": [
                        "1", "2", "3",
                        "5", "7", "10",
                        "20", "30", "50",
                        "70", "100", "125",
                        "150", "175", "200",
                        "225", "250", "300",
                        "350", "400", "450",
                        "500", "550", "600",
                        "650", "700", "750",
                        "775", "800", "825",
                        "850", "875", "900",
                        "925", "950", "975",
                        "1000"
                    ],
                        "data_format": "netcdf",
                        "download_format": "unarchived",
                        "area": coordinate
                    }

            
            try:
                client.retrieve(dataset, request).download(chunk_filename)
                print(f"Successfully downloaded {chunk_filename}")
            except Exception as e:
                with open(timeoutDates, 'a', encoding = 'utf-8') as file:
                        file.write(f"Skipping {yr}-{mth} due to error: {e}\n")
                temp_files.pop()

    # 2. Merge all monthly NetCDF files into one complete dataset
    print("\n=== Step 2: Merging NetCDF Chunks into Single File ===")
    
    try:
        # combine='by_coords' handles both year and month dimensions seamlessly
        ds_merged = xr.open_mfdataset(temp_files, combine='by_coords')
        ds_merged.load()
        print("Merged and converting to NC")
        # Save to single combined NetCDF file
        ds_merged.to_netcdf(filename)
        print(f"Successfully merged all chunks into: {filename}")
        
        # Close dataset handle so the files can be safely deleted
        ds_merged.close()

    except Exception as e:
        print(f"Error while concatenating files: {e}")
        return None

    # 3. Clean up individual chunk files
    print("\n=== Step 3: Cleaning up temporary chunk files ===")
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
            print(f"Removed temporary file: {f}")
            
    print("\nProcess Complete!")
    return filename






if __name__ == "__main__":
    #era5_data_load()
    #era5_sp_data_load()
    #radiosonde_data_download("Data&Model/Radiosonde/CSV/", "71082")
    era5_hourly_level_data_load(coordinate = [84.7769, -81.5466, 78.6372, -47.5212], siteID = 71082)