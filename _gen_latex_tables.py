import xarray as xr
import numpy as np
from datetime import datetime

era5_path = "Data&Model/ERA5/71082/era5_71082_monthly.nc"
radio_path = "Data&Model/Radiosonde/NC/71082_monthly.nc"

def extract_trend_data(path):
    ds = xr.open_dataset(path)
    groupTrend = ds.groupby(ds.month_hour)
    timeKey3 = list(groupTrend.groups.keys())
    sub_data3 = [sub_ds for _, sub_ds in groupTrend]
    timeName3 = [f"{datetime.strptime(key, '%m-%H').strftime('%B %H')} UTC" for key in timeKey3]
    
    freqTrend = [np.squeeze(sub_ds["frequency_trend"].values) for sub_ds in sub_data3]
    strengthTrend = [np.squeeze(sub_ds["strength_trend"].values) for sub_ds in sub_data3]
    depthTrend = [np.squeeze(sub_ds["depth_trend"].values) for sub_ds in sub_data3]
    intensityTrend = [np.squeeze(sub_ds["intensity_trend"].values) for sub_ds in sub_data3]
    
    ds.close()
    return timeName3, freqTrend, strengthTrend, depthTrend, intensityTrend

def fmt(val, decimals=4):
    if isinstance(val, (float, np.floating, np.float32, np.float64)):
        if np.isnan(val):
            return "N/A"
        return f"{float(val):.{decimals}f}"
    return str(val)

def generate_latex_table(label, caption, timeName3, freq, strength, depth, intensity):
    row_labels = [
        "Frequency Trend (decade$^{-1}$)",
        "Strength Trend (K decade$^{-1}$)",
        "Depth Trend (m decade$^{-1}$)",
        "Intensity Trend (K m$^{-1}$ decade$^{-1}$)",
    ]
    
    rows_data = [freq, strength, depth, intensity]
    
    latex = []
    latex.append(r"\begin{table}[H]")
    latex.append(r"  \centering")
    latex.append(r"  \small")
    latex.append(r"  \caption{" + caption + "}")
    latex.append(r"  \label{" + label + "}")
    latex.append(r"  \begin{tabular}{l" + "c" * len(timeName3) + "}")
    latex.append(r"    \toprule")
    
    # Header row
    header = r"    \textbf{Trend Index} & " + " & ".join([r"\textbf{" + c + "}" for c in timeName3]) + r" \\"
    latex.append(header)
    latex.append(r"    \midrule")
    
    # Data rows
    for i, row_label in enumerate(row_labels):
        vals = rows_data[i]
        cells = " & ".join([fmt(v) for v in vals])
        latex.append(f"    {row_label} & {cells} \\\\")
    
    latex.append(r"    \bottomrule")
    latex.append(r"  \end{tabular}")
    latex.append(r"\end{table}")
    
    return "\n".join(latex)

# Extract data
era5_cols, era5_freq, era5_str, era5_dep, era5_int = extract_trend_data(era5_path)
rad_cols, rad_freq, rad_str, rad_dep, rad_int = extract_trend_data(radio_path)

# Generate LaTeX
era5_latex = generate_latex_table(
    "tab:era5_trends",
    "ERA5 Reanalysis: Wintertime SBI Long-Term Trends (1978--2025) at Alert, NU (71082)",
    era5_cols, era5_freq, era5_str, era5_dep, era5_int
)

rad_latex = generate_latex_table(
    "tab:radiosonde_trends",
    "Radiosonde Observations: Wintertime SBI Long-Term Trends (1978--2025) at Alert, NU (71082)",
    rad_cols, rad_freq, rad_str, rad_dep, rad_int
)

# Combined side-by-side table
combined = []
combined.append(r"\begin{table}[H]")
combined.append(r"  \centering")
combined.append(r"  \small")
combined.append(r"  \caption{Wintertime SBI Long-Term Trends (1978--2025) at Alert, NU (71082): Radiosonde vs.\ ERA5}")
combined.append(r"  \label{tab:sbi_trends_comparison}")
combined.append(r"  \begin{subtable}[t]{0.48\textwidth}")
combined.append(r"    \centering")
combined.append(r"    \caption{Radiosonde Observations}")
combined.append(r"    \label{tab:radiosonde_trends}")
combined.append(r"    \begin{tabular}{l" + "c" * len(rad_cols) + "}")
combined.append(r"      \toprule")
combined.append(r"      \textbf{Trend} & " + " & ".join([r"\textbf{\shortstack{" + c.replace(" UTC","") + "}}" for c in rad_cols]) + r" \\")
combined.append(r"      \midrule")
rad_labels = ["Freq. (dec$^{-1}$)", "Str. (K dec$^{-1}$)", "Depth (m dec$^{-1}$)", "Int. (K m$^{-1}$ dec$^{-1}$)"]
rad_data = [rad_freq, rad_str, rad_dep, rad_int]
for i, rl in enumerate(rad_labels):
    cells = " & ".join([fmt(v) for v in rad_data[i]])
    combined.append(f"      {rl} & {cells} \\\\")
combined.append(r"      \bottomrule")
combined.append(r"    \end{tabular}")
combined.append(r"  \end{subtable}")
combined.append(r"  \hfill")
combined.append(r"  \begin{subtable}[t]{0.48\textwidth}")
combined.append(r"    \centering")
combined.append(r"    \caption{ERA5 Reanalysis}")
combined.append(r"    \label{tab:era5_trends}")
combined.append(r"    \begin{tabular}{l" + "c" * len(era5_cols) + "}")
combined.append(r"      \toprule")
combined.append(r"      \textbf{Trend} & " + " & ".join([r"\textbf{\shortstack{" + c.replace(" UTC","") + "}}" for c in era5_cols]) + r" \\")
combined.append(r"      \midrule")
era5_labels = ["Freq. (dec$^{-1}$)", "Str. (K dec$^{-1}$)", "Depth (m dec$^{-1}$)", "Int. (K m$^{-1}$ dec$^{-1}$)"]
era5_data = [era5_freq, era5_str, era5_dep, era5_int]
for i, el in enumerate(era5_labels):
    cells = " & ".join([fmt(v) for v in era5_data[i]])
    combined.append(f"      {el} & {cells} \\\\")
combined.append(r"      \bottomrule")
combined.append(r"    \end{tabular}")
combined.append(r"  \end{subtable}")
combined.append(r"\end{table}")

# Write output
output = "=" * 70 + "\n"
output += "LATEX TABLE CODE - RADIOSONDE SBI TRENDS TABLE\n"
output += "(Values extracted from Data&Model/Radiosonde/NC/71082_monthly.nc)\n"
output += "=" * 70 + "\n\n"
output += rad_latex
output += "\n\n" + "=" * 70 + "\n"
output += "LATEX TABLE CODE - ERA5 SBI TRENDS TABLE\n"
output += "(Values extracted from Data&Model/ERA5/71082/era5_71082_monthly.nc)\n"
output += "=" * 70 + "\n\n"
output += era5_latex
output += "\n\n" + "=" * 70 + "\n"
output += "BONUS: COMBINED SIDE-BY-SIDE COMPARISON TABLE\n"
output += "=" * 70 + "\n\n"
output += "\n".join(combined)

print(output)

with open("ArcticSBI_LaTeXReport/trend_tables_latex.tex", "w") as f:
    f.write("% ============================================================\n")
    f.write("% SBI Trend Tables - Generated from NetCDF climatology data\n")
    f.write("% Radiosonde: Data&Model/Radiosonde/NC/71082_monthly.nc\n")
    f.write("% ERA5:      Data&Model/ERA5/71082/era5_71082_monthly.nc\n")
    f.write("% ============================================================\n\n")
    f.write(rad_latex)
    f.write("\n\n")
    f.write(era5_latex)
    f.write("\n\n")
    f.write("\n".join(combined))
    f.write("\n")

print("\n\nSaved to: ArcticSBI_LaTeXReport/trend_tables_latex.tex")
