import cdsapi
import xarray as xr
import os

def era5_data_load():
    filename = "Data&Model/ERA5data_arctic.nc"

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
            "area": [90, -180, 66.5, 180]
        }

        client = cdsapi.Client()
        client.retrieve(dataset, request).download(filename)



    return filename






def main():
    era5_data_load()

if __name__ == "__main__":
    main()
