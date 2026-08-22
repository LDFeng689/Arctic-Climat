import matplotlib
matplotlib.use('Agg')

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mpath
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

def climatology_plots(dataset, resultsFolder):
    stationID = dataset.attrs["SiteName"]
    stationResFolder = os.path.join(resultsFolder,stationID)
    os.makedirs(stationResFolder, exist_ok=True)
    print(f"Plotting Data for {stationID}")

    #1.Timeseries plots
    #Separating the data into each of the 6 timesteps
    grouped1 = dataset.groupby(dataset.time.dt.strftime("%m-%H"))
    timeKey = list(grouped1.groups.keys())
    sub_data = [sub_ds for _, sub_ds in grouped1]
    timeName = [datetime.strptime(key, "%m-%H").strftime("%B %H:00") for key in timeKey]  #Name of the time steps for each graphs
    years = [np.unique(sub_ds.time.dt.year.values) for sub_ds in sub_data]

    freq = [sub_ds["sbi_frequency"].values for sub_ds in sub_data]
    strength = [sub_ds["sbi_strength"].values for sub_ds in sub_data]
    depth = [sub_ds["sbi_depth"].values for sub_ds in sub_data]
    intensity = [sub_ds["sbi_intensity"].values for sub_ds in sub_data]
    topT = [sub_ds["inversion_top_temp"].values for sub_ds in sub_data]
    topP = [sub_ds["inversion_top_pressure"].values for sub_ds in sub_data]
    timeseries_plots(description = "SBI Frequency", xaxis = "Year", yaxis = "Frequency", xvar = years, yvar = freq, times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Intensity", xaxis = "Year", yaxis = "Lapse Rate (K m-1)", xvar = years, yvar = intensity, times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Strength", xaxis = "Year", yaxis = "Temperature (K)", xvar = years, yvar = strength,times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "SBI Depth", xaxis = "Year", yaxis = "Height (m)", xvar = years, yvar = depth, times = timeName,outputFolder = stationResFolder)
    timeseries_plots(description =  "Inversion Top Temperature", xaxis = "Year", yaxis = "Temperature (K)", xvar = years, yvar = topT,times = timeName, outputFolder = stationResFolder)
    timeseries_plots(description = "Inversion Top Pressure", xaxis = "Year", yaxis = "Pressure (hpa)", xvar = years, yvar = topP, times = timeName,outputFolder = stationResFolder, vertical=True)
    


    grouped2 = dataset.groupby(dataset.year_month.dt.strftime("%m"))
    timeKey2 = list(grouped2.groups.keys())
    sub_data2 = [sub_ds for _, sub_ds in grouped2]
    timeName2 = [datetime.strptime(key, "%m").strftime("%B") for key in timeKey2]  #Name of the time steps for each graphs
    years = [np.unique(sub_ds.year_month.dt.year.values) for sub_ds in sub_data2]

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
    dataOrigin = Path(outputFolder).name

    # Set global aesthetic style
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Modern Blue Color Palette
    primary_color = "#005b96"    # Deep Ocean Blue
    secondary_color = "#e65c00"  # Warm Accent Coral (for yvar2)
    
    # Layout dimensions
    if singleHour:
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    else:
        fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), sharey=False)

    axes = np.atleast_1d(axes).flatten()

    # Parse title and dataset naming
    if isinstance(description, (list, tuple)):
        title = description[0]
        dataName = description[1]
        doubleEntry = True
    else:
        title = description
        dataName = [title, ""]
        doubleEntry = False

    for i, ax in enumerate(axes):
        if i >= len(xvar):
            ax.set_visible(False)
            continue

        # Plot primary variable
        if doubleEntry and yvar2 is not None:
            ax.plot(xvar[i], yvar[i], label=dataName[0], color=primary_color, linewidth=2)
            ax.plot(xvar[i], yvar2[i], label=dataName[1], color=secondary_color, linewidth=2, linestyle="--")
            ax.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=9)
        else:
            ax.plot(xvar[i], yvar[i], color=primary_color, linewidth=2, label=dataName[0] if doubleEntry else None)
            if doubleEntry:
                ax.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=9)

        # Labels & Titles
        ax.set_xlabel(xaxis, fontsize=10, fontweight="bold", labelpad=6)
        ax.set_ylabel(yaxis, fontsize=10, fontweight="bold", labelpad=6)

        if times is not None and i < len(times):
            time_str = f"{times[i]}" if timeless else f"{times[i]} UTC"
            ax.set_title(f"{dataOrigin}-{title}\n[{time_str}]", fontsize=11, fontweight="semibold", pad=8)
        else:
            ax.set_title(f"{dataOrigin}-{title}", fontsize=11, fontweight="semibold", pad=8)

        # Invert vertical axis for pressure levels (high pressure at bottom -> surface)
        if vertical:
            ax.invert_yaxis()

        # Grid and Spines styling
        ax.grid(True, linestyle="--", alpha=0.3, color="#888888")
        ax.tick_params(axis='both', which='major', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#cccccc')

    plt.tight_layout()
    
    # Save figure with high DPI and tight borders
    output_path = os.path.join(outputFolder, f"{title.replace(' ', '_')}.png")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


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

    plt.xlabel("Year", fontsize=11, fontweight="bold")
    plt.ylabel("Data count", fontsize=11, fontweight="bold")
    plt.title(f"Number of Radiosonde Data for each Time Period for {siteID}", fontsize=12, fontweight="bold")
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    plt.savefig(output_location, dpi=300, bbox_inches="tight")
    plt.close()
    # endregion

    return dataLack


#Run alone plots for indivicual checks

def vertical_anotated_plot(dataset, figFolder, time=[0,0,0,0]):
    site_name = dataset.attrs["SiteName"]
    if len(time) == 3:
        dt = datetime.strptime(str(datetime(time[0],time[1],time[2])), "%Y-%m-%H")
        dt = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
        date = f"{dt.isoformat()}.000000000"
        output_location = os.path.join(figFolder,site_name,f"{time[0]}-{time[1]}_{time[2]}_vertical.png")
    else :
        dt = datetime.strptime(str(datetime(time[0],time[1],time[2],time[3])), "%Y-%m-%d %H:%M:%S")
        date = f"{dt.isoformat()}.000000000"
        output_location = os.path.join(figFolder,site_name,f"{time[0]}-{time[1]}-{time[2]}_{time[3]}_vertical.png")


    time = dataset.time.values

    try:
         t_idx = np.where(time == np.datetime64(date))[0].item()
    except ValueError:
        print("No data at this date")
        return None

# Extract profiles and force scalar extraction for 1D single-value outputs
    pressure = np.asarray(dataset.pressure.values)
    temp = np.asarray(dataset.temperature.values[t_idx])
    mixR = np.asarray(dataset.mixRatio.values[t_idx])

    #Set surface
    sfc_P = dataset.sp.values[t_idx]
    sfc_idx = np.where(pressure == sfc_P)[0]
    if len(sfc_idx) == 0:  #no index found
        p_below_idx = np.where(pressure > sfc_P)[0][-1]  # Higher pressure (closer to surface)
        p_above_idx = np.where(pressure < sfc_P)[0][0]  # Lower pressure (higher up)
        sfc_T = np.interp(sfc_P, (pressure[p_above_idx], pressure[p_below_idx]), (temp[p_above_idx], temp[p_below_idx]))

    else: 
        sfc_T = temp[sfc_idx[0]]


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
    ax.scatter([inv_top_T], [inv_top_P], color="#d9534f", zorder=5, s=40)
    ax.scatter([sfc_T], [sfc_P], color="#cf514d", zorder=5, s=40)

    # Formatting & Axes
    ax.set_xlabel("Temperature (K)", fontsize=10, fontweight="bold", labelpad=6)
    ax.set_ylabel("Pressure (hPa)", fontsize=10, fontweight="bold", labelpad=6)
    ax.set_title(f"{site_name} Vertical Profile\n[{date[:19]}]", fontsize=11, fontweight="semibold", pad=10)

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

def month_timeseries(datasetD,datasetM, figFolder, time = [0,0,0]):
    site_name = datasetD.attrs["SiteName"]
    dataOrigin = Path(figFolder).name

    target_year, target_month, target_hour = time[0], time[1], time[2]

    sub_datasetD = datasetD.sel(
            time=(datasetD.time.dt.year == target_year)
            & (datasetD.time.dt.month == target_month)
            & (datasetD.time.dt.hour == target_hour)
        )
    daily_strength = sub_datasetD.sbi_strength.values
    daily_depth = sub_datasetD.sbi_depth.values

    days = sub_datasetD.time.dt.day.values
    
    sub_datasetM = datasetM.sel(
            time=(datasetM.time.dt.year == target_year)
            & (datasetM.time.dt.month == target_month)
            & (datasetM.time.dt.hour == target_hour)
        )
    avg_strength = sub_datasetM.sbi_strength.values.item()
    avg_depth = sub_datasetM.sbi_depth.values.item()


    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    primary_color = "#005b96" 
    secondary_color = "#e65c00"

    # --- Top Subplot: SBI Strength ---
    ax1.plot(
        days, daily_strength, marker="o", color=primary_color, label="Daily SBI Strength"
    )
    ax1.axhline(
        y=avg_strength,
        color=secondary_color,
        linestyle="--",
        linewidth=2,
        label=f"Monthly Avg ({avg_strength:.2f})",
    )
    ax1.set_ylabel("SBI Strength (K)")
    ax1.set_title(
        f"{dataOrigin}_{site_name} - {target_year}-{target_month:02d} (Hour {target_hour:02d}:00)"
    )
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right")

    # --- Bottom Subplot: SBI Depth ---
    ax2.plot(days, daily_depth, marker="o", color= primary_color, label="Daily SBI Depth")
    ax2.axhline(
        y=avg_depth,
        color=secondary_color,
        linestyle="-",
        linewidth=2,
        label=f"Monthly Avg ({avg_depth:.2f})",
    )
    ax2.set_xlabel("Day of Month")
    ax2.set_ylabel("SBI Depth (m)")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right")

    plt.tight_layout()
    outFolder = os.path.join(figFolder,site_name,f"{target_year}_{target_month:02d}_{target_hour:02d}UTC_StrDepth.png")
    plt.savefig(outFolder, dpi=300)
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
            f"{h:02d}:00 UTC – Any Valid Profile", fontsize=13, fontweight="bold"
        )
        axes[1, col_idx].set_title(
            f"{h:02d}:00 UTC – Strictly All Valid Profiles",
            fontsize=13,
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

        axes[1, col_idx].set_xlabel("Year", fontsize=12)

    axes[0, 0].set_ylabel("Pressure (hPa)", fontsize=12)
    axes[1, 0].set_ylabel("Pressure (hPa)", fontsize=12)

    # Title & Legend
    fig.suptitle(
        f"Mixing Ratio Data Availability – {site_name}",
        fontsize=16,
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
        fontsize=12,
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

    ds = xr.open_dataset(r"Data&Model\ERA5\71082\era5_71082_daily.nc")
    dm = xr.open_dataset(r"Data&Model\ERA5\71082\era5_71082_monthly.nc")
    vertical_anotated_plot(ds,r"Figures\ERA5",[2019,12,6,0])

    for i in range(0,48): #0,48
        try:
            vertical_anotated_plot(ds,f"Figures/{source}",[1978+i,12,6,0])
            month_timeseries(ds,dm, f"Figures/{source}", [1978+i,12,0])
        except Exception:
            pass

    






