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
        plotting_3month_on_map(datasets, features[i] ,months, descriptions[i], titles[i],colorMaps[i],type[i],filenames[i])

#Initialize the arctic circle
def format_arctic_axis(ax, title_text=""):
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
def plotting_3month_on_map(datasets, feature, months, description, title,colorMap,type,filename):
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
        format_arctic_axis(ax, title_text=months[i])
        

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
    plt.savefig(filename, dpi=300, bbox_inches='tight')
            
    plt.savefig(filename)
    #plt.show()
    plt.close()


def vertical_plot(dataset,foldername, description="",month=""):
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
            
    plt.savefig(filename)

    #plt.show()
    plt.close()
    

def timeseries_plot(dataset, foldername, description: str, month: str):
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

    #ax2_right.invert_yaxis()
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

    plt.savefig(filename)

    ax2.cla()
    ax2_right.cla()
    plt.clf()
    plt.close(fig2)




if __name__ == "__main__":
    pass