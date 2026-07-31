import cdsapi
import xarray as xr
import os
import requests
import numpy as np
import time
import pandas as pd
from datetime import datetime
from siphon.simplewebservice.wyoming import WyomingUpperAir



def era5_data_load():
    filename = "Data&Model/ERA5/ERA5_data_arctic.nc"

    #2 if statement to check if the data is already downloaded or converted to nc
    if os.path.isfile(filename):
        print("ERA5 Arctic Dataset present")
        #API download request
    else:
        print("Downloading data")
        dataset = "reanalysis-era5-pressure-levels-monthly-means"
        request = {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": [
                "specific_humidity",
                "temperature"
            ],
            "pressure_level": [
                "1", "2", "3",
                "5", "7", "10",
                "20", "30", "50",
                "70",
                "100", "125", "150",
                "175", "200", "225",
                "250", "300", "350",
                "400", "450", "500",
                "550", "600", "650",
                "700", "750", "775",
                "800", "825", "850",
                "875", "900", "925",
                "950", "975", "1000"
            ],
            "year": [
                "1940", "1941", "1942",
                "1943", "1944", "1945",
                "1946", "1947", "1948",
                "1949", "1950", "1951",
                "1952", "1953", "1954",
                "1955", "1956", "1957",
                "1958", "1959", "1960",
                "1961", "1962", "1963",
                "1964", "1965", "1966",
                "1967", "1968", "1969",
                "1970", "1971", "1972",
                "1973", "1974", "1975",
                "1976", "1977", "1978",
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
                "2024", "2025", "2026"
            ],
            "month": ["01", "02", "12"],
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [90, -180, 66.5, 180] #definition of the arctic circle
        }

        client = cdsapi.Client()
        client.retrieve(dataset, request).download(filename)



    return filename

def era5_sp_data_load():
    filename = "Data&Model/ERA5/ERA5_sp_arctic.nc"

    #2 if statement to check if the data is already downloaded or converted to nc
    if os.path.isfile(filename):
        print("ERA5 Arctic Surface Pressure Data present")
        #API download request
    else:
        print("Downloading surface pressure data")
        dataset = "reanalysis-era5-single-levels-monthly-means"
        request = {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": ["surface_pressure", "2m_temperature"],
            "year": [
                "1940", "1941", "1942",
                "1943", "1944", "1945",
                "1946", "1947", "1948",
                "1949", "1950", "1951",
                "1952", "1953", "1954",
                "1955", "1956", "1957",
                "1958", "1959", "1960",
                "1961", "1962", "1963",
                "1964", "1965", "1966",
                "1967", "1968", "1969",
                "1970", "1971", "1972",
                "1973", "1974", "1975",
                "1976", "1977", "1978",
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
                "2024", "2025", "2026"
            ],
            "month": ["01", "02", "12"],
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [90, -180, 66.5, 180]
        }

        client = cdsapi.Client()
        client.retrieve(dataset, request).download(filename)
    return filename

def radiosonde_data_download(csvFolder, station_number, overwrite = False):

    station_path = os.path.join(csvFolder, station_number)
    
    if os.path.isdir(station_path) and overwrite == False:    #Skip if already exist and don't want to do changes to it
        print(f"{station_number} radiosonde data already downloaded")
        return station_path
    else:
        os.makedirs(station_path, exist_ok=True)
        print(f"Downloading radiosonde data for {station_number}")



    start_year = 2021 #1977 #normally from 73
    end_year =2021
    years = np.linspace(start_year,end_year, num = end_year-start_year+1 ).astype(int).astype(str)

    monthsInt = ["12","01","02"]
    monthsName = ['Dec','Jan','Feb']
    days = [f"{x:02d}" for x in range(1, 32) ]
    #0000 is 12 UTC, 2000 is 00 UTC
    hoursCode = ["2000","2012"]
    hours = ["00","12"]


    

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
                    
                    try:
                        # Send a GET request to the URL
                        response = requests.get(website, timeout = (1,40))

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



if __name__ == "__main__":
    #era5_data_load()
    #era5_sp_data_load()
    radiosonde_data_download("Data&Model/Radiosonde/CSV/", "71082")
