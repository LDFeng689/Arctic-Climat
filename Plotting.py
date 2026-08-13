import matplotlib
matplotlib.use('Agg')

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import scipy
import os
from datetime import datetime
import pandas as pd

def era5_monthly_globe_plot(datasets,foldername):
    #Initiate the values to plot and the time label
    months = [dataset.attrs["Month"] for dataset in datasets]
    features = ["avgIntensity", "avgDepth","intensityTrend","depthTrend"]
    descriptions = ["Temperature difference (°C)", "Depth (m)", " Temperature Difference Trend (°C/decade)", "Depth Trend (m/decade)"]
    titles = ["1979-2014 mean T(inversion top)- T(surface)", "1979-2014 mean inversion depth", "1979-2014 inversion intensity trends", "1979-2014 inversion depth trends"]
    colorMaps = ["hot_r", "YlGnBu","seismic","seismic"]
    type = ["value",'value','trend','trend']
    filenames = [f"{foldername}Arctic_{feature}_1979to2014.png" for feature in features]

    for i in range(len(features)):
        era5_plotting_3month_on_map(datasets, features[i] ,months, descriptions[i], titles[i],colorMaps[i],type[i],filenames[i])

#Initialize the arctic circle
def era5_format_arctic_axis(ax, title_text=""):
    """
    Applies the standardized Arctic Circle base map formatting 
    (66.5N-90N, circular boundary, and coastlines) to an existing axis slot.
    """
    # 1. Set strict geographic boundaries (66.5N to 90N)
    ax.set_extent([-180, 180, 66.5, 90], crs=ccrs.PlateCarree())
    
    # 2. Apply the circular boundary clip
    theta = np.linspace(0, 2 * np.pi, 100)
    center = [0.5, 0.5]
    radius = 0.5
    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
    circle = mpath.Path(verts * radius + center)
    ax.set_boundary(circle, transform=ax.transAxes)
    
    # 3. Add background geographic features
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='black', zorder=2)
    ax.add_feature(cfeature.LAND, facecolor='whitesmoke', zorder=1)
    ax.add_feature(cfeature.OCEAN, facecolor='aliceblue', zorder=0)
    
    # 4. Add standard gridlines
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=0.5, color='gray', linestyle='--')
    gl.ylocator = plt.FixedLocator([69, 75, 84])
    gl.xlocator = plt.FixedLocator([-180, -120, -60, 0, 60, 120, 180])
    
    if title_text:
        ax.set_title(title_text, fontsize=10, fontweight='bold', pad=10)

#Plots all 3 months with common color bar
def era5_plotting_3month_on_map(datasets, feature, months, description, title,colorMap,type,filename):
    # 1. Initialize a 1x3 horizontal layout
    # We specify the Cartopy projection inside the subplot keyword dictionary
    fig, axes = plt.subplots(
        1, 3, 
        figsize=(15, 6), 
        subplot_kw={'projection': ccrs.NorthPolarStereo(central_longitude=0)}
    )

    # 2. Establish uniform color limits for the shared colorbar
    # (Or hardcode them, e.g., vmin=-2, vmax=2 if you know your data range)
    all_values = np.concatenate([ds[feature].values.flatten() for ds in datasets])
    vmin = np.nanmin(all_values)
    vmax = np.nanmax(all_values)

    # Make symmetric if plotting diverging trends around 0
    if type == "trend":    
        vmax = max(abs(vmin), abs(vmax))
        vmin = -vmax

    # 3. Loop through and plot each of the 3 maps
    mesh_objects = []
    for i, ax in enumerate(axes):
        # Apply our reusable mold to this specific axis slot
        era5_format_arctic_axis(ax, title_text=months[i])
        

        # Overlay the gridded data onto the formatted axis slot
        mesh = ax.pcolormesh(
            datasets[i].longitude, 
            datasets[i].latitude, 
            datasets[i][feature], 
            transform=ccrs.PlateCarree(),
            cmap=colorMap,
            vmin=vmin, 
            vmax=vmax,
            shading='auto'
        )
        mesh_objects.append(mesh)

    # 4. Add the GLOBAL Colorbar
    # 'fig.colorbar' places it relative to the whole figure, not a single panel.
    # 'ax=axes.ravel().tolist()' tells it to steal even layout space from all three plots.
    cax = fig.add_axes([0.35, 0.05, 0.30, 0.03])
    cbar = fig.colorbar(
            mesh_objects[0], 
            cax=cax,                    # <-- CRITICAL: Use 'cax' instead of 'ax=axes...'
            orientation='horizontal'
        )
    cbar.set_label(f"{description}", fontsize=11, fontweight='bold',labelpad = 12)

    # 5. Global overarching title for the entire set of 3
    fig.suptitle(f"{title}", fontsize=14, fontweight='bold', y=0.97)

    # Save the multi-panel figure cleanly
    #plt.tight_layout(rect=[0, 0.12, 1, 0.90])
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except PermissionError:
            # If a background process or file viewer is holding it,
            # renaming it allows you to save the new one without crashing
            os.rename(filename, filename + ".old")
    plt.savefig(filename, dpi=300, bbox_inches='tight')
            
    plt.savefig(filename)
    #plt.show()
    plt.close()


def era5_vertical_plot(dataset,foldername, description="",month=""):
    tempTrend = dataset.temperatureTrend.values
    #print(tempTrend)
    pressure_levels = dataset.pressure_level
    #print(pressure_levels)

    plt.plot(tempTrend, pressure_levels)
    
    # Set the y-axis limits so 1000 is at the bottom and 1 is at the top
    plt.ylim(1050, -50)
    # Add labels and a grid for better readability
    plt.xlabel('Temperature Trend (K/decade)')
    plt.ylabel('Pressure Levels (hPa)')
    plt.title(f'Vertical Plot of Temperature Trend for the {description} in {month}',wrap = True)
    plt.grid(True)

    filename = f"{foldername}Arctic_vertical_{description}.png"
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except PermissionError:
            # If a background process or file viewer is holding it,
            # renaming it allows you to save the new one without crashing
            os.rename(filename, filename + ".old")
            
    plt.savefig(filename)

    #plt.show()
    plt.close()
    

def era5_timeseries_plot(dataset, foldername, description: str, month: str):
    sfc_temp = dataset.surface_temp.values
    inv_top = dataset.inversion_top.values
    depth = dataset.depth.values
    inv_top_plv = dataset.inversion_top_pressurelv.values
    times = dataset.time.values

    time_extend = np.linspace(1979, 2014, 1000)
    m_sfc, c_sfc, _, _, _ = scipy.stats.linregress(times, sfc_temp)
    m_top, c_top, _, _, _ = scipy.stats.linregress(times, inv_top)

    # ==========================================
    # GRAPH 1: Temperature Timeseries
    # ==========================================
    fig1, ax1 = plt.subplots(figsize=(6, 5))

    ax1.plot(time_extend, m_sfc * time_extend + c_sfc, color="black")
    ax1.plot(time_extend, m_top * time_extend + c_top, color="black")
    ax1.set_ylabel("Temperature (K)")
    ax1.plot(
        times,
        sfc_temp,
        color="blue",
        linewidth=2,
        label="Surface temperature",
    )
    ax1.plot(
        times,
        inv_top,
        color="red",
        linewidth=2,
        label="Inversion top temperature",
    )
    ax1.set_xlim(1977, 2016)
    ax1.margins(x = 0, y = 0.15)
    ax1.set_xlabel("Year")
    ax1.set_title(
        f"Temperature Timeseries ({description} - {month})", wrap=True
    )
    ax1.legend(loc="upper right")
    ax1.grid(True)

    #plt.tight_layout()
    filename = f"{foldername}Arctic_timeseries_Temp_{description}.png"

    if os.path.exists(filename):
        try:
            os.remove(filename)
        except PermissionError:
            # If a background process or file viewer is holding it,
            # renaming it allows you to save the new one without crashing
            os.rename(filename, filename + ".old")
            
    plt.savefig(filename)

    ax1.cla()
    plt.clf()
    plt.close(fig1)

    # ==========================================
    # GRAPH 2: Depth & Pressure Timeseries (Dual Y-Axes)
    # ==========================================
    fig2, ax2 = plt.subplots(figsize=(6, 5))

    # 1. Left Y-axis (ax2) -> Depth
    line1 = ax2.plot(times, depth, color="orange", linewidth=2, label="Depth")
    ax2.set_ylabel("Inversion Depth (m)")
    ax2.set_xlabel("Year")
    ax2.margins(x = 0, y = 0.15)
    ax2.grid(True, axis="y", linewidth=0.5)

    # 2. Right Y-axis (ax2_right) -> Pressure Level
    ax2_right = (
        ax2.twinx()
    )  # Instantiates a secondary axes that shares the x-axis
    line2 = ax2_right.plot(
        times,
        inv_top_plv,
        color="green",
        linewidth=2,
        label="Inversion top pressure",
    )
    ax2_right.set_ylabel("Inversion Top Pressure Level (hPa)")

    # Meteorology convention: higher pressure is lower altitude, so invert axis

    ax2_right.invert_yaxis()
    ax2_right.grid(False)
    ax2_right.margins(x=0, y=0.15)

    # 3. Combined Legend for Dual Axes
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc="upper right")

    ax2.set_title(
        f"Depth & Pressure Timeseries ({description} - {month})", wrap=True
    )

    filename = f"{foldername}Arctic_timeseries_Depth_Pres_{description}.png"
    #plt.tight_layout()
    # If the file exists, delete it from disk first to release Windows file locks
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except PermissionError:
            # If a background process or file viewer is holding it,
            # renaming it allows you to save the new one without crashing
            os.rename(filename, filename + ".old")

    plt.savefig(filename)

    ax2.cla()
    ax2_right.cla()
    plt.clf()
    plt.close(fig2)


#ABOVE WERE FIRST ATTEMPS OF RECREATING RESULTS, BELOW IS THE ACTUALLY USED CODES 

def climatology_plots(dataset, resultsFolder):
    stationID = dataset.attrs["SiteName"]
    stationResFolder = os.path.join(resultsFolder,stationID)
    os.makedirs(stationResFolder, exist_ok=True)

    #1.Timeseries plots
    #Separating the data into each of the 6 timesteps
    grouped1 = dataset.groupby(dataset.time_monthly.dt.strftime("%m-%H"))
    timeKey = list(grouped1.groups.keys())
    sub_data = [sub_ds for _, sub_ds in grouped1]
    timeName = [datetime.strptime(key, "%m-%H").strftime("%B %H:00") for key in timeKey]  #Name of the time steps for each graphs
    years = [np.unique(sub_ds.time_monthly.dt.year.values) for sub_ds in sub_data]

    freq = [sub_ds["sbi_frequency"].values for sub_ds in sub_data]
    strength = [sub_ds["sbi_strength"].values for sub_ds in sub_data]
    depth = [sub_ds["sbi_depth"].values for sub_ds in sub_data]
    intensity = [sub_ds["sbi_intensity"].values for sub_ds in sub_data]
    topT = [sub_ds["inversion_top_t"].values for sub_ds in sub_data]
    topZ = [sub_ds["inversion_top_z"].values for sub_ds in sub_data]
    topP = [sub_ds["inversion_top_p"].values for sub_ds in sub_data]
    timeseries_plots(description = "SBI Frequency", xaxis = "Year", yaxis = "Frequency", xvar = years, yvar = freq, times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Intensity", xaxis = "Year", yaxis = "Lapse Rate (K m-1)", xvar = years, yvar = intensity, times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Strength", xaxis = "Year", yaxis = "Temperature (K)", xvar = years, yvar = strength,times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Depth", xaxis = "Year", yaxis = "Height (m)", xvar = years, yvar = depth, times = timeName,outputFolder = stationResFolder)
    timeseries_plots(description =  "Inversion Top Temperature", xaxis = "Year", yaxis = "Temperature (K)", xvar = years, yvar = topT,times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "Inversion Top Height", xaxis = "Year", yaxis = "Height (m)", xvar = years, yvar = topZ, times = timeName,outputFolder = stationResFolder)
    timeseries_plots(description = "Inversion Top Pressure", xaxis = "Year", yaxis = "Pressure (hpa)", xvar = years, yvar = topP, times = timeName,outputFolder = stationResFolder)
    


    grouped2 = dataset.groupby(dataset.time_diff.dt.strftime("%m-%H"))
    timeKey2 = list(grouped2.groups.keys())
    sub_data2 = [sub_ds for _, sub_ds in grouped2]
    timeName2 = [datetime.strptime(key, "%m-%H").strftime("%B %H:00") for key in timeKey2]  #Name of the time steps for each graphs
    years = [np.unique(sub_ds.time_diff.dt.year.values) for sub_ds in sub_data2]

    diT = [sub_ds["diurnal_contrast_T"].values for sub_ds in sub_data2]
    diF = [sub_ds["diurnal_contrast_F"].values for sub_ds in sub_data2]
    diZ = [sub_ds["diurnal_contrast_Z"].values for sub_ds in sub_data2]
    impact = [sub_ds["sbi_impact"].values for sub_ds in sub_data2]
    timeseries_plots(description = "Diurnal Strength Contrast", xaxis = "Year", yaxis = "Temperature(K)", xvar = years, yvar = diT, times = timeName2, outputFolder = stationResFolder, singleHour = True)
    timeseries_plots(description = "Diurnal Frequency Contrast", xaxis = "Year", yaxis = "Frequency", xvar = years, yvar = diF, times = timeName2, outputFolder = stationResFolder, singleHour = True)
    timeseries_plots(description = "Diurnal Depth Contrast", xaxis = "Year", yaxis = "Depth(m)", xvar = years, yvar = diZ, times = timeName2, outputFolder = stationResFolder, singleHour = True)
    timeseries_plots(description = "SBI Impact", xaxis = "Year", yaxis = "Impact temperature(K)", xvar = years, yvar = impact, times = ["January", "February", "December"], outputFolder = stationResFolder, singleHour = True, timeless = True)

    #2. Vertical plot
    #Also in time_monthly so take grouped1
    tempTrend = dataset["temperature_trend"].values 
    pressure = [sub_ds["pressure"].values for sub_ds in sub_data]
    timeseries_plots(description = "Temperature Trend", xaxis = "Temperature Trend (K decade^-1)", yaxis = "Pressure(hPa)", xvar = tempTrend, yvar = pressure, times = timeName, outputFolder = stationResFolder, vertical = True)

    #3. Table for trends
    trend_table(dataset, outputFolder = stationResFolder)


def timeseries_plots(description, xaxis, yaxis, xvar, yvar, times = None, outputFolder = "", yvar2 = None, singleHour = False, vertical = False, timeless = False):
    #For sbi: freq, strength, depth, intensity, impact, top height, top temp, 
    if singleHour:
        fig, axes = plt.subplots(1, 3, figsize=(15, 8))
    else:
        fig, axes = plt.subplots(2, 3, figsize=(15, 8)) #Each row is an hour

    axes = axes.flatten()
    if type(description) != str:
        title = description[0]
        dataName = description[1]
        doubleEntry = True
    else:
        title = description
        dataName = title
        doubleEntry = False

    for i, ax in enumerate(axes):

        ax.set_xlabel(xaxis)
        ax.set_ylabel(yaxis)
        if doubleEntry == True:
            ax.plot(xvar[i], yvar[i], label = dataName[0])
            ax.plot(xvar[i], yvar2[i], label = dataName[1])
        else:
            ax.plot(xvar[i], yvar[i]) 

        if timeless == True:
            ax.set_title(f"{title} for {times[i]}")
        else:
            ax.set_title(f"{title} for {times[i]} UTC")

        if vertical == True:   #Vertical plot so that go from higher pressure to lower
                    ax.invert_yaxis()

        ax.legend()
        ax.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(outputFolder,f"{title}.png"))


def trend_table(dataset, outputFolder):
    groupTrend = dataset.groupby(dataset.month_hour)
    timeKey3 = list(groupTrend.groups.keys())
    sub_data3 = [sub_ds for _, sub_ds in groupTrend]
    timeName3 = [datetime.strptime(key, "%m-%H").strftime("%B %H:00") for key in timeKey3]

    freqTrend = [sub_ds["frequency_trend"].values for sub_ds in sub_data3]
    strengthTrend = [sub_ds["strength_trend"].values for sub_ds in sub_data3]
    depthTrend = [sub_ds["depth_trend"].values for sub_ds in sub_data3]
    intensityTrend = [sub_ds["intensity_trend"].values for sub_ds in sub_data3]

    row_labels = [
        "Frequency Trend (decade^-1)",
        "Strength Trend (k decade^-1)",
        "Depth Trend (m decade^-1)",
        "Intensity Trend (k m^-1 decade^-1)",
    ]
    col_labels = timeName3  # 6 column names (e.g., 'December 00:00', ...)

    # 2. Extract and flatten values into a 2D matrix (4 rows x 6 columns)
    # Note: np.squeeze handles 1D arrays or single-element sub-arrays cleanly
    data_matrix = np.array(
        [
            [np.squeeze(val) for val in freqTrend],
            [np.squeeze(val) for val in strengthTrend],
            [np.squeeze(val) for val in depthTrend],
            [np.squeeze(val) for val in intensityTrend],
        ]
    )

    # Optional: Format floating point numbers to 4 decimal places for clean reading
    formatted_data = np.vectorize(
        lambda x: f"{float(x):.4f}" if np.issubdtype(type(x), np.number) else str(x)
    )(data_matrix)

    # 3. Create DataFrame
    df = pd.DataFrame(formatted_data, index=row_labels, columns=col_labels)

    # 4. Render Table using Matplotlib
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")  # Hide surrounding plot axes

    # Build table layout
    table = ax.table(
        cellText=df.values,
        rowLabels=df.index,
        colLabels=df.columns,
        cellLoc="center",
        loc="center",
    )

    # 5. Apply styling for publication/printing
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 2.0)  # Adjust cell width and height

    # Style headers (bold text + light grey background)
    for (r, c), cell in table.get_celld().items():
        if r == 0 or c == -1:  # Column header or Row label
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#f0f4f8")

    plt.tight_layout()

    # 6. Save as high-resolution PNG ready for printing
    plt.savefig(os.path.join(outputFolder,"sbi_trends_table.png"), dpi=300, bbox_inches="tight")
    

if __name__ == "__main__":
    #dataset = xr.open_dataset(r"D:\McGill\Atoc396\ArcticClimat\Data&Model\Radiosonde\NC\71917_results.nc", chunks={'time': 10})
    #radiosonde_plots(dataset, "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde", "71917")

    dataset = xr.open_dataset(r"D:\McGill\Atoc396\ArcticClimat\Data&Model\Radiosonde\NC\71082_results.nc", chunks={'time': 10})
    #climatology_plots(dataset, "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde")