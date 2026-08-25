import matplotlib
matplotlib.use('Agg')

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator, MultipleLocator
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import scipy
import os
from datetime import datetime
import pandas as pd
import calendar
from pathlib import Path

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

def climatology_plots(datasetE,datasetR, resultsFolder):
    stationID = datasetE.attrs["SiteName"]

    print(f"Plotting Data for {stationID}")

    #1.Timeseries plots
    #Getting the variables
    (timeNameE, yearsE, freqE, strengthE, depthE, intensityE, topTE, topPE, surfTE, surfPE, pressureE, timeName2E, years2E, diTE, diFE, diZE, impactE) = time_grouping(datasetE)
    (timeNameR, yearsR, freqR, strengthR, depthR, intensityR, topTR, topPR, surfTR, surfPR, pressureR, timeName2R, years2R, diTR, diFR, diZR, impactR) = time_grouping(datasetR)

    # Separating the data into each of the 6 timesteps
    timeseries_plots(description=["SBI Frequency", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Frequency", xvar=yearsE, yvar=freqE, yvar2=freqR, times=timeNameE, outputFolder=resultsFolder)
    timeseries_plots(description=["SBI Lapse Rate", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Lapse Rate (K m-1)", xvar=yearsE, yvar=intensityE, yvar2=intensityR, times=timeNameE, outputFolder=resultsFolder)
    timeseries_plots(description=["SBI Strength", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Temperature (K)", xvar=yearsE, yvar=strengthE, yvar2=strengthR, times=timeNameE, outputFolder=resultsFolder)
    timeseries_plots(description=["SBI Depth", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Height (m)", xvar=yearsE, yvar=depthE, yvar2=depthR, times=timeNameE, outputFolder=resultsFolder)

    timeseries_plots(description=["Inversion Top Temperature", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Temperature (K)", xvar=yearsE, yvar=topTE, yvar2=topTR, times=timeNameE, outputFolder=resultsFolder)
    timeseries_plots(description=["Inversion Top Pressure", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Pressure (hpa)", xvar=yearsE, yvar=topPE, yvar2=topPR, times=timeNameE, outputFolder=resultsFolder, vertical=True)
    timeseries_plots(description=["Surface Pressure", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Pressure (hpa)", xvar=yearsE, yvar=surfPE, yvar2=surfPR, times=timeNameE, outputFolder=resultsFolder, vertical=True)
    timeseries_plots(description=["Surface Temperature", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Temperature (K)", xvar=yearsE, yvar=surfTE, yvar2=surfTR, times=timeNameE, outputFolder=resultsFolder)

    # 3 timesteps
    timeseries_plots(description=["Diurnal Strength Contrast", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Temperature(K)", xvar=yearsE, yvar=diTE, yvar2=diTR, times=timeName2E, outputFolder=resultsFolder, singleHour=True,timeless=True)
    timeseries_plots(description=["Diurnal Frequency Contrast", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Frequency", xvar=yearsE, yvar=diFE, yvar2=diFR, times=timeName2E, outputFolder=resultsFolder, singleHour=True,timeless=True)
    timeseries_plots(description=["Diurnal Depth Contrast", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Depth(m)", xvar=yearsE, yvar=diZE, yvar2=diZR, times=timeName2E, outputFolder=resultsFolder, singleHour=True,timeless=True)
    timeseries_plots(description=["SBI Impact", ("ERA5", "Radiosonde")], xaxis="Year", yaxis="Impact temperature(°C month^-1)", xvar=yearsE, yvar=impactE, yvar2=impactR, times=["January", "February", "December"], outputFolder=resultsFolder, singleHour=True, timeless=True)

    #2. Vertical plot
    #Also in time_monthly so take grouped1
    tempTrendE = datasetE["temperature_trend"].values
    tempTrendR = datasetR["temperature_trend"].values 
    timeseries_plots(description = "Temperature Trend ERA5", xaxis = "Temperature Trend (K decade^-1)", yaxis = "Pressure(hPa)", xvar = tempTrendE, yvar = pressureE, times = timeNameE, outputFolder = resultsFolder, vertical = True)
    timeseries_plots(description = "Temperature Trend Radiosonde", xaxis = "Temperature Trend (K decade^-1)", yaxis = "Pressure(hPa)", xvar = tempTrendR, yvar = pressureR, times = timeNameE, outputFolder = resultsFolder, vertical = True)
    #3. Table for trends
    trend_table(datasetE, outputFolder = resultsFolder, dataName= "ERA5")
    trend_table(datasetR, outputFolder = resultsFolder, dataName= "Radiosonde")


def timeseries_plots(
    description,
    xaxis,
    yaxis,
    xvar,
    yvar,
    times=None,
    outputFolder="",
    yvar2=None,
    singleHour=False,
    vertical=False,
    timeless=False,
):
    # Set global aesthetic style
    plt.style.use(
        "seaborn-v0_8-whitegrid"
        if "seaborn-v0_8-whitegrid" in plt.style.available
        else "default"
    )

    # Modern Blue & Coral Color Palette
    primary_color = "#005b96"  # Deep Ocean Blue
    secondary_color = "#e65c00"  # Warm Accent Coral

    # Parse title and dataset naming
    if isinstance(description, (list, tuple)):
        title = description[0]
        dataName = description[1]
        doubleEntry = True
    else:
        title = description
        dataName = [title, ""]
        doubleEntry = False

    # Define Grid Dimensions
    ncols = 3
    nrows = 1 if singleHour else 2
    n_subplots = len(xvar)

    # Figure dimensions
    fig = plt.figure(
        figsize=(24, 8.5 if singleHour else 16.0), constrained_layout=False
    )
    outer_grid = gridspec.GridSpec(nrows, ncols, figure=fig, wspace=0.35, hspace=0.35)

    for i in range(nrows * ncols):
        if i >= n_subplots:
            break

        ax_main = fig.add_subplot(outer_grid[i])

        # Clean/Align Input Vectors
        x = np.asarray(xvar[i])
        y1 = np.asarray(yvar[i])

        # Plot Main Line Data
        if doubleEntry and yvar2 is not None:
            y2 = np.asarray(yvar2[i])
            ax_main.plot(
                x,
                y1,
                label=dataName[0][0] if isinstance(dataName[0], (list, tuple)) else dataName[0],
                color=primary_color,
                linewidth=2.5,
            )
            ax_main.plot(
                x,
                y2,
                label=dataName[1][0] if isinstance(dataName[1], (list, tuple)) else dataName[1],
                color=secondary_color,
                linewidth=2.5,
            )
            
            # Position Legend on Top-Left
            ax_main.legend(
                frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=16, loc="upper left"
            )

            # Compute Statistical Metrics
            mask = ~np.isnan(y1) & ~np.isnan(y2)
            if np.sum(mask) > 1:
                o, m = y2[mask], y1[mask]  # y2: Benchmark, y1: Model
                bias = np.mean(m - o)
                rmse = np.sqrt(np.mean((m - o) ** 2))
                r = np.corrcoef(o, m)[0, 1] if np.std(o) > 0 and np.std(m) > 0 else np.nan

                stats_text = f"Bias: {bias:+.2f} | RMSE: {rmse:.2f} | Corr: {r:.2f}"
            else:
                stats_text = "N/A"

            # Overlay Statistics Text Box directly BELOW the Title
            ax_main.text(
                0.5,
                1.02,
                stats_text,
                transform=ax_main.transAxes,
                fontsize=16,
                family="monospace",
                verticalalignment="bottom",
                horizontalalignment="center",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="#f8f9fa",
                    edgecolor="#cccccc",
                    alpha=0.95,
                ),
            )

        else:
            ax_main.plot(
                x,
                y1,
                color=primary_color,
                linewidth=2.5,
                label=dataName[0] if doubleEntry else None,
            )
            if doubleEntry:
                ax_main.legend(
                    frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=16, loc="best"
                )

        # Axis Labels & Titles
        ax_main.set_xlabel(xaxis, fontsize=18, fontweight="bold", labelpad=8)
        ax_main.set_ylabel(yaxis, fontsize=18, fontweight="bold", labelpad=8)

        if times is not None and i < len(times):
            time_str = f"{times[i]}" if timeless else f"{times[i]} UTC"
            ax_main.set_title(
                f"{title}\n[{time_str}]", fontsize=20, fontweight="semibold", pad=35 if (doubleEntry and yvar2 is not None) else 20
            )
        else:
            ax_main.set_title(f"{title}", fontsize=20, fontweight="semibold", pad=35 if (doubleEntry and yvar2 is not None) else 20)

        if vertical:
            ax_main.invert_yaxis()

        # Grid and Spines styling
        ax_main.grid(True, linestyle="--", alpha=0.3, color="#888888")
        ax_main.tick_params(axis="both", which="major", labelsize=16)
        for spine in ax_main.spines.values():
            spine.set_color("#cccccc")

    # Save figure
    os.makedirs(outputFolder, exist_ok=True)
    output_path = os.path.join(outputFolder, f"{title.replace(' ', '_')}.png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def trend_table(dataset, outputFolder,dataName):
    groupTrend = dataset.groupby(dataset.month_hour)
    timeKey3 = list(groupTrend.groups.keys())
    sub_data3 = [sub_ds for _, sub_ds in groupTrend]
    timeName3 = [f"{datetime.strptime(key, '%m-%H').strftime('%B %H')} UTC" for key in timeKey3]

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
    plt.savefig(os.path.join(outputFolder,f"{dataName}_sbi_trends_table.png"), dpi=300, bbox_inches="tight")


def time_grouping(dataset):
    grouped1 = dataset.groupby(dataset.time.dt.strftime("%m-%H"))
    timeKey = list(grouped1.groups.keys())
    sub_data = [sub_ds for _, sub_ds in grouped1]
    timeName = [datetime.strptime(key, "%m-%H").strftime("%B %H") for key in timeKey]  #Name of the time steps for each graphs
    years = [np.unique(sub_ds.time.dt.year.values) for sub_ds in sub_data]

    freq = [sub_ds["sbi_frequency"].values for sub_ds in sub_data]
    strength = [sub_ds["sbi_strength"].values for sub_ds in sub_data]
    depth = [sub_ds["sbi_depth"].values for sub_ds in sub_data]
    intensity = [sub_ds["sbi_intensity"].values for sub_ds in sub_data]
    topT = [sub_ds["inversion_top_temp"].values for sub_ds in sub_data]
    topP = [sub_ds["inversion_top_pressure"].values for sub_ds in sub_data]
    surfT = [sub_ds["surface_temp"].values for sub_ds in sub_data]
    surfP = [sub_ds["surface_pressure"].values for sub_ds in sub_data]
    pressure = [sub_ds["pressure"].values for sub_ds in sub_data]

    grouped2 = dataset.groupby(dataset.year_month.dt.strftime("%m"))
    timeKey2 = list(grouped2.groups.keys())
    sub_data2 = [sub_ds for _, sub_ds in grouped2]
    timeName2 = [datetime.strptime(key, "%m").strftime("%B") for key in timeKey2]  #Name of the time steps for each graphs
    years2 = [np.unique(sub_ds.year_month.dt.year.values) for sub_ds in sub_data2]

    diT = [sub_ds["diurnal_contrast_T"].values for sub_ds in sub_data2]
    diF = [sub_ds["diurnal_contrast_F"].values for sub_ds in sub_data2]
    diZ = [sub_ds["diurnal_contrast_Z"].values for sub_ds in sub_data2]
    impact = [sub_ds["sbi_impact"].values for sub_ds in sub_data2]

    return (
        timeName,
        years,
        freq,
        strength,
        depth,
        intensity,
        topT,
        topP,
        surfT,
        surfP,
        pressure,

        timeName2,
        years2,
        diT,
        diF,
        diZ,
        impact,
    )




def radiosonde_data_count(csvFolder, figFolder, siteID):
    CSVpath = os.path.join(csvFolder, siteID)
    output_location = os.path.join(figFolder, siteID, "Data_Count.png")
    
    # Map month string names to integer month numbers
    month_str_to_num = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, 
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, 
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    # Color map indexed by month number
    winter_colors = {
        12: ["#8B0000", "#E55353"],  # December: [00 UTC (Dark Crimson), 12 UTC (Light Red)]
        1:  ["#002366", "#4169E1"],  # January:  [00 UTC (Midnight Navy), 12 UTC (Royal Blue)]
        2:  ["#005F73", "#0A9396"],  # February: [00 UTC (Deep Teal),      12 UTC (Frost Cyan)]
    }

    # Safely sort folder listings
    years = sorted([y for y in os.listdir(CSVpath) if os.path.isdir(os.path.join(CSVpath, y))])
    
    # Get month folder names (e.g., ['Dec', 'Jan', 'Feb'])
    sample_year_path = os.path.join(CSVpath, years[0])
    raw_months = [m for m in os.listdir(sample_year_path) if os.path.isdir(os.path.join(sample_year_path, m))]
    
    # Sort months based on month_str_to_num mapping
    months = sorted(raw_months, key=lambda m: month_str_to_num.get(m, 0))
    
    hour_labels = ["00 UTC", "12 UTC"]
    hours_map = [0, 12]
    hour_patterns = [r"_00", r"_12"]
    
    counts = np.full((len(years), len(months), len(hour_labels)), np.nan)  # 3D array: (years, months, hours)
    dataLack = []

    for y_idx, year_str in enumerate(years):
        year = int(year_str)
        year_path = os.path.join(CSVpath, year_str)
        
        for m_idx, month_str in enumerate(months):
            # Convert folder name string ("Dec") to integer (12)
            month = month_str_to_num[month_str]
            month_path = os.path.join(year_path, month_str)
            
            if not os.path.exists(month_path):
                continue
                
            all_files = pd.Series(os.listdir(month_path))
            _, total_days_in_month = calendar.monthrange(year, month)
            
            # Allow at most 5 missing days per month (WMO Guideline)
            min_required_days = total_days_in_month - 5 
            
            for h_idx, h_pattern in enumerate(hour_patterns):
                matching_files = all_files[all_files.str.contains(h_pattern, na=False)]
                total_count = len(matching_files)
                counts[y_idx, m_idx, h_idx] = total_count
                
                # --- Condition 1: Monthly Total Count Threshold ---
                has_enough_count = total_count >= min_required_days
                
                # --- Condition 2: No 5 Consecutive Days Missing ---
                day_numbers = matching_files.str.extract(r"(\d{2})_" + h_pattern[1:])[0].dropna().astype(int).unique()
                days_present = np.isin(np.arange(1, total_days_in_month + 1), day_numbers)
                
                missing_consecutive = 0
                max_missing_consecutive = 0
                for present in days_present:
                    if not present:
                        missing_consecutive += 1
                        max_missing_consecutive = max(max_missing_consecutive, missing_consecutive)
                    else:
                        missing_consecutive = 0
                        
                has_no_5_consecutive_gaps = max_missing_consecutive < 5
                
                # Flag timestamp if either condition fails
                if not (has_enough_count and has_no_5_consecutive_gaps):
                    dt = datetime(year, month, 1, hours_map[h_idx])
                    dataLack.append(np.datetime64(f"{dt.isoformat()}.000000000"))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_location), exist_ok=True)

    # region Plotting the data counts
    linestyles = ["-", ":"]

    plt.figure(figsize=(11, 6))

    for m_idx, month_str in enumerate(months):
        month_num = month_str_to_num[month_str]
        color_pair = winter_colors.get(month_num, ["#1f77b4", "#aec7e8"])

        for h_idx in range(2):
            y = counts[:, m_idx, h_idx]
            label = f"Month: {month_str} ({hour_labels[h_idx]})"

            plt.plot(
                years, 
                y, 
                label=label, 
                color=color_pair[h_idx],
                marker="o",
                linestyle=linestyles[h_idx],
                linewidth=1.8,
                markersize=7,
                alpha=0.85
            )

    buffer = 1
    y_min = int(np.nanmin(counts)) - buffer
    y_max = int(np.nanmax(counts)) + buffer
    plt.ylim(y_min, y_max)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.gca().xaxis.set_major_locator(MultipleLocator(base=5))

    plt.xlabel("Year", fontsize=16, fontweight="bold")
    plt.ylabel("Data count", fontsize=16, fontweight="bold")
    plt.title(f"Number of Radiosonde Data for each Time Period for {siteID}", fontsize=18, fontweight="bold")
    plt.xticks(rotation=45)
    plt.legend(fontsize=16, loc="best", frameon=True)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    plt.savefig(output_location, dpi=300, bbox_inches="tight")
    plt.close()
    # endregion

    return dataLack


#Run alone plots for indivicual checks

def vertical_anotated_plot(dataset, figFolder, time=[0,0,0,0], dataName =""):
    site_name = dataset.attrs["SiteName"]
    if len(time) == 3:
        dt = datetime(time[0], time[1], 1, time[2])
        date = dt.strftime("%Y-%m-%dT%H:%M:%S.000000000")  
        titleDate = f"{time[0]}-{time[1]:02d} {time[2]:02d} UTC"     
        output_location = os.path.join(figFolder,f"{dataName}{time[0]}-{time[1]}_{time[2]}_vertical.png")
    else :
        dt = datetime.strptime(str(datetime(time[0],time[1],time[2],time[3])), "%Y-%m-%d %H:%M:%S")
        date = f"{dt.isoformat()}.000000000"
        titleDate = f"{time[0]}-{time[1]:02d}-{time[2]:02d} {time[3]:02d} UTC"  
        output_location = os.path.join(figFolder,f"{dataName}{time[0]}-{time[1]}-{time[2]}_{time[3]}_vertical.png")


    time = dataset.time.values

    try:
         t_idx = np.where(time == np.datetime64(date))[0].item()
    except ValueError:
        print("No data at this date")
        return None

# Extract profiles and force scalar extraction for 1D single-value outputs
    pressure = np.asarray(dataset.pressure.values)
    temp = np.asarray(dataset.temperature.values[t_idx])
    

    #Set surface
    sfc_P = dataset.sp.values[t_idx]
    sfc_T = dataset.st.values[t_idx]
    temp[np.where(pressure > sfc_P -10)] = np.nan
    valid_start_idx = np.where(~np.isnan(temp))[0]

    if len(valid_start_idx) > 0:
        first_valid = valid_start_idx[0]
        pressure = pressure[first_valid:]
        temp = temp[first_valid:]

    pressure = np.insert(pressure, 0, sfc_P)
    temp = np.insert(temp, 0, sfc_T)    


    # Convert 1-element arrays to scalar floats to avoid string format errors
    sbi_depth = float(dataset.sbi_depth.values[t_idx])
    sbi_strength = float(dataset.sbi_strength.values[t_idx])
    inv_top_T = float(dataset.inversion_top_temp.values[t_idx])
    inv_top_P = float(dataset.inversion_top_pressure.values[t_idx])

# Ensure output directory exists
    os.makedirs(os.path.dirname(output_location), exist_ok=True)

    # Create Figure
    fig, ax = plt.subplots(figsize=(6, 8))
    
    primary_color = "#005b96"       # Deep Ocean Blue
    annotation_color = "#e65c00"    # Warm Coral Accent

    # 1. Plot vertical temperature profile
    ax.plot(temp, pressure, color=primary_color, linewidth=2.5, label="Temperature Profile")

    # 2. Vertical line: Surface pressure to Inversion Top Pressure
    ax.vlines(
        x=sfc_T, 
        ymin=min(sfc_P, inv_top_P), 
        ymax=max(sfc_P, inv_top_P), 
        colors=annotation_color, 
        linestyles="--", 
        linewidth=1.8, 
        label=f"Inversion Depth = {sbi_depth:.2} m"
    )

    # 3. Horizontal line: Surface temp to Inversion Top Temp
    ax.hlines(
        y=inv_top_P, 
        xmin=min(sfc_T, inv_top_T), 
        xmax=max(sfc_T, inv_top_T), 
        colors="#d9534f", 
        linestyles="-", 
        linewidth=1.8, 
        label=f"Inversion Strength = {sbi_strength:.2} K"
    )

    # Highlight Inversion Top Point and surface point
    if inv_top_T is not np.nan and inv_top_P is not np.nan:
        ax.scatter([inv_top_T], [inv_top_P], color="#d9534f", zorder=5, s=40)
        ax.scatter([sfc_T], [sfc_P], color="#ef9c9a", zorder=5, s=40)

    # Formatting & Axes
    ax.set_xlabel("Temperature (K)", fontsize=10, fontweight="bold", labelpad=6)
    ax.set_ylabel("Pressure (hPa)", fontsize=10, fontweight="bold", labelpad=6)

    ax.set_title(f"{dataName} Vertical Profile\n[{titleDate}]", fontsize=11, fontweight="semibold", pad=10)

    # Ensure pressure coordinates auto-scale before inverting axis
    ax.relim()
    ax.autoscale_view()
    ax.invert_yaxis()

    # Styling
    ax.grid(True, linestyle="--", alpha=0.3, color="#888888")
    ax.tick_params(axis='both', which='major', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#cccccc')

    ax.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=9, loc="best")
    plt.tight_layout()

    plt.savefig(output_location, dpi=300, bbox_inches="tight")
    plt.close(fig)

def month_timeseries(
    datasetD1,
    datasetM1,
    datasetD2,
    datasetM2,
    figFolder,
    time=[0, 0, 0],
    dataName=["Dataset 1", "Dataset 2"],
):
    site_name = datasetD1.attrs.get("SiteName", "Site")
    target_year, target_month, target_hour = time[0], time[1], time[2]

    # Set global aesthetic style
    plt.style.use(
        "seaborn-v0_8-whitegrid"
        if "seaborn-v0_8-whitegrid" in plt.style.available
        else "default"
    )

    primary_color = "#005b96"    # Deep Ocean Blue
    secondary_color = "#e65c00"  # Warm Accent Coral

    # --- Dataset Sub-selection ---
    sub_D1 = datasetD1.sel(
        time=(datasetD1.time.dt.year == target_year)
        & (datasetD1.time.dt.month == target_month)
        & (datasetD1.time.dt.hour == target_hour)
    )
    sub_D2 = datasetD2.sel(
        time=(datasetD2.time.dt.year == target_year)
        & (datasetD2.time.dt.month == target_month)
        & (datasetD2.time.dt.hour == target_hour)
    )

    # --- Align Daily Datasets by Day-of-Month using Pandas ---
    s1_str = pd.Series(sub_D1.sbi_strength.values, index=sub_D1.time.dt.day.values)
    s2_str = pd.Series(sub_D2.sbi_strength.values, index=sub_D2.time.dt.day.values)

    s1_dep = pd.Series(sub_D1.sbi_depth.values, index=sub_D1.time.dt.day.values)
    s2_dep = pd.Series(sub_D2.sbi_depth.values, index=sub_D2.time.dt.day.values)

    # Combine into aligned DataFrames to handle mismatched day counts automatically
    df_str = pd.DataFrame({"d1": s1_str, "d2": s2_str})
    df_dep = pd.DataFrame({"d1": s1_dep, "d2": s2_dep})

    days = df_str.index.values
    d1_strength, d2_strength = df_str["d1"].values, df_str["d2"].values
    d1_depth, d2_depth = df_dep["d1"].values, df_dep["d2"].values

    # --- Monthly Averages ---
    sub_M1 = datasetM1.sel(
        time=(datasetM1.time.dt.year == target_year)
        & (datasetM1.time.dt.month == target_month)
        & (datasetM1.time.dt.hour == target_hour)
    )
    sub_M2 = datasetM2.sel(
        time=(datasetM2.time.dt.year == target_year)
        & (datasetM2.time.dt.month == target_month)
        & (datasetM2.time.dt.hour == target_hour)
    )

    avg_strength1 = sub_M1.sbi_strength.values.item()
    avg_depth1 = sub_M1.sbi_depth.values.item()
    avg_strength2 = sub_M2.sbi_strength.values.item()
    avg_depth2 = sub_M2.sbi_depth.values.item()

    # --- Helper Function for Statistics Calculation ---
    def calc_stats(y1, y2):
        mask = ~np.isnan(y1) & ~np.isnan(y2)
        if np.sum(mask) > 1:
            m, o = y1[mask], y2[mask]  # y1: Dataset 1, y2: Dataset 2
            bias = np.mean(m - o)
            rmse = np.sqrt(np.mean((m - o) ** 2))
            r = np.corrcoef(o, m)[0, 1] if np.std(o) > 0 and np.std(m) > 0 else np.nan
            return f"Bias: {bias:+.2f} | RMSE: {rmse:.2f} | Corr: {r:.2f}"
        return "N/A"

    stats_strength = calc_stats(d1_strength, d2_strength)
    stats_depth = calc_stats(d1_depth, d2_depth)

    # --- Setup Figure and Subplots ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    name1 = dataName[0] if isinstance(dataName, (list, tuple)) else "Dataset 1"
    name2 = dataName[1] if isinstance(dataName, (list, tuple)) and len(dataName) > 1 else "Dataset 2"

    # ==========================================
    # --- Top Subplot: SBI Strength ---
    # ==========================================
    ax1.plot(days, d1_strength, marker="o", color=primary_color, linewidth=2, label=f"{name1} Daily")
    ax1.axhline(
        y=avg_strength1, color=primary_color, linestyle="--", linewidth=1.8, label=f"{name1} Avg ({avg_strength1:.2f} K)"
    )

    ax1.plot(days, d2_strength, marker="s", color=secondary_color, linewidth=2, label=f"{name2} Daily")
    ax1.axhline(
        y=avg_strength2, color=secondary_color, linestyle="--", linewidth=1.8, label=f"{name2} Avg ({avg_strength2:.2f} K)"
    )

    ax1.set_ylabel("SBI Strength (K)", fontsize=18, fontweight="bold")
    ax1.set_title(
        f"{site_name} - SBI Strength - {target_year}-{target_month:02d} ({target_hour:02d} UTC)",
        fontsize=20,
        fontweight="bold",
        pad=35,
    )
    ax1.grid(True, linestyle="--", alpha=0.4, color="#888888")
    ax1.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        fontsize=16,
    )

    # Statistics Box Above Ax1
    ax1.text(
        0.5, 1.02, stats_strength, transform=ax1.transAxes, fontsize=16, family="monospace",
        verticalalignment="bottom", horizontalalignment="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8f9fa", edgecolor="#cccccc", alpha=0.95)
    )

    # ==========================================
    # --- Bottom Subplot: SBI Depth ---
    # ==========================================
    ax2.plot(days, d1_depth, marker="o", color=primary_color, linewidth=2, label=f"{name1} Daily")
    ax2.axhline(
        y=avg_depth1, color=primary_color, linestyle="--", linewidth=1.8, label=f"{name1} Avg ({avg_depth1:.2f} m)"
    )

    ax2.plot(days, d2_depth, marker="s", color=secondary_color, linewidth=2, label=f"{name2} Daily")
    ax2.axhline(
        y=avg_depth2, color=secondary_color, linestyle="--", linewidth=1.8, label=f"{name2} Avg ({avg_depth2:.2f} m)"
    )

    ax2.set_xlabel("Day of Month", fontsize=18, fontweight="bold")
    ax2.set_ylabel("SBI Depth (m)", fontsize=18, fontweight="bold")
    ax2.set_title(
        f"{site_name} - SBI Depth - {target_year}-{target_month:02d} ({target_hour:02d} UTC)",
        fontsize=20,
        fontweight="bold",
        pad=35,
    )
    ax2.grid(True, linestyle="--", alpha=0.4, color="#888888")
    ax2.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        fontsize=16,
        )

    # Statistics Box Above Ax2
    ax2.text(
        0.5, 1.02, stats_depth, transform=ax2.transAxes, fontsize=16, family="monospace",
        verticalalignment="bottom", horizontalalignment="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f8f9fa", edgecolor="#cccccc", alpha=0.95)
    )

    plt.tight_layout()

    # Save figure
    os.makedirs(figFolder, exist_ok=True)
    out_name = f"{site_name}_{target_year}_{target_month:02d}_{target_hour:02d}UTC_StrDepth.png"
    outPath = os.path.join(figFolder, out_name)
    plt.savefig(outPath, dpi=300, bbox_inches="tight")
    plt.close()

def vapor_presence_plot(dataset, figFolder):
    site_name = dataset.attrs["SiteName"]
    hour = [0, 12]
    month = [12, 1, 2]  # Dec -> Jan -> Feb
    month_str = ["Dec", "Jan", "Feb"]

    month_colors = {
        12: "#8B0000",  # December (Crimson)
        1: "#002366",  # January (Navy)
        2: "#005F73",  # February (Teal)
    }

    month_offsets = {
        12: -0.25,
        1: 0.00,
        2: 0.25,
    }
    bar_half_width = 0.10

    # Grid changed to 2 rows x 2 columns
    fig, axes = plt.subplots(
        2, 2, figsize=(18, 12), sharey=True, sharex="col"
    )

    all_years = np.unique(dataset.time.dt.year.values)
    min_year, max_year = all_years.min(), all_years.max()
    tick_years = np.arange(min_year, max_year + 1, 5)

    # Defines row-level logic
    # Row 0: At least one profile valid (Any valid)
    # Row 1: ALL profiles valid (No NaNs allowed)
    row_titles = [
        "Partial Coverage (At least 1 valid profile)",
        "Complete Coverage (All profiles valid, 0 NaNs)",
    ]

    for col_idx, h in enumerate(hour):
        sub_dataset = dataset.sel(time=dataset.time.dt.hour == h)
        years = np.unique(sub_dataset.time.dt.year.values)

        for m, mstr in zip(month, month_str):
            offset = month_offsets[m]

            for y in years:
                data_slice = sub_dataset.sel(
                    time=(sub_dataset.time.dt.month == m)
                    & (sub_dataset.time.dt.year == y)
                )

                if data_slice.time.size == 0:
                    continue

                pressure = data_slice.pressure.values
                mixR = data_slice.mixRatio.values

                # Handle 2D vs 1D arrays
                if mixR.ndim > 1:
                    # Top row: True if ANY profile is non-NaN
                    mask_any = ~np.isnan(mixR).all(axis=0)
                    # Bottom row: True ONLY IF ALL profiles are non-NaN (NO NaNs)
                    mask_all = ~np.isnan(mixR).any(axis=0)

                    if pressure.ndim > 1:
                        pressure = np.nanmean(pressure, axis=0)
                else:
                    mask_any = ~np.isnan(mixR)
                    mask_all = ~np.isnan(mixR)

                x_center = y + offset
                x1 = x_center - bar_half_width
                x2 = x_center + bar_half_width

                # Plot Row 0 (Partial / Any valid)
                axes[0, col_idx].fill_betweenx(
                    y=pressure,
                    x1=x1,
                    x2=x2,
                    where=mask_any,
                    color=month_colors[m],
                    alpha=0.85,
                    linewidth=0,
                )

                # Plot Row 1 (Complete / Strictly no NaNs)
                axes[1, col_idx].fill_betweenx(
                    y=pressure,
                    x1=x1,
                    x2=x2,
                    where=mask_all,
                    color=month_colors[m],
                    alpha=0.85,
                    linewidth=0,
                )

    # Formatting axes and titles
    for col_idx, h in enumerate(hour):
        # Column headers
        axes[0, col_idx].set_title(
            f"{h:02d}:00 UTC – Any Valid Profile", fontsize=16, fontweight="bold"
        )
        axes[1, col_idx].set_title(
            f"{h:02d}:00 UTC – Strictly All Valid Profiles",
            fontsize=16,
            fontweight="bold",
        )

        for row_idx in range(2):
            ax = axes[row_idx, col_idx]
            ax.set_xticks(tick_years)
            ax.set_xticklabels([str(y) for y in tick_years], fontsize=10)
            ax.set_xlim(min_year - 1, max_year + 1)
            ax.grid(True, linestyle="--", alpha=0.3, axis="y")

            if not ax.yaxis_inverted():
                ax.invert_yaxis()

        axes[1, col_idx].set_xlabel("Year", fontsize=16,fontweight="bold")

    axes[0, 0].set_ylabel("Pressure (hPa)", fontsize=16,fontweight="bold")
    axes[1, 0].set_ylabel("Pressure (hPa)", fontsize=16,fontweight="bold")

    # Title & Legend
    fig.suptitle(
        f"Mixing Ratio Data Availability – {site_name}",
        fontsize=20,
        fontweight="bold",
        y=0.98,
    )

    handles = [
        plt.Rectangle(
            (0, 0), 1, 1, color=month_colors[m], alpha=0.85, label=mstr
        )
        for m, mstr in zip(month, month_str)
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=3,
        frameon=False,
        fontsize=16,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.91])

    outDir = os.path.join(figFolder, site_name)
    os.makedirs(outDir, exist_ok=True)
    outPath = os.path.join(outDir, "water_vapor_presence.png")

    plt.savefig(outPath, dpi=300)
    plt.close()

if __name__ == "__main__":
    #dataset = xr.open_dataset(r"D:\McGill\Atoc396\ArcticClimat\Data&Model\Radiosonde\NC\71917_results.nc", chunks={'time': 10})
    #radiosonde_plots(dataset, "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde", "71917")
    #climatology_plots(dataset, "D:/McGill/Atoc396/ArcticClimat/Figures/Radiosonde")
    #days = radiosonde_data_count(r"Data&Model\Radiosonde\CSV",r"Figures\Radiosonde","71082")
    source = "Radiosonde"

    #from main import one_time
    #one_time(dataset = source)

    da = xr.open_dataset(r"Data&Model\Radiosonde\NC\71082_monthly.nc")
    db = xr.open_dataset(r"Data&Model\ERA5\71082\era5_71082_monthly.nc")

    d1 = xr.open_dataset(r"Data&Model\Radiosonde\NC\71082_daily.nc")
    d2 = xr.open_dataset(r"Data&Model\ERA5\71082\era5_71082_daily.nc")
    year = 2000
    month = 2
    day =16
    figFolder = r"Figures\71082\Profiles"
    vertical_anotated_plot(d1,figFolder,[year,month,day,00],"Radiosonde")
    vertical_anotated_plot(d2,figFolder,[year,month,day,00],"ERA5")
    vertical_anotated_plot(d1,figFolder,[year,month,day,12],"Radiosonde")
    vertical_anotated_plot(d2,figFolder,[year,month,day,12],"ERA5")

    vertical_anotated_plot(da,figFolder,[year,month,00],"Radiosonde")
    vertical_anotated_plot(db,figFolder,[year,month,00],"ERA5")
    vertical_anotated_plot(da,figFolder,[year,month,12],"Radiosonde")
    vertical_anotated_plot(db,figFolder,[year,month,12],"ERA5")

    month_timeseries(d2,db,d1,da, figFolder,[year,month,00],["ERA5","Radiosonde"])
    month_timeseries(d2,db,d1,da, figFolder,[year,month,12],["ERA5","Radiosonde"])




    






