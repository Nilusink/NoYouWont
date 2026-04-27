"""
gps_debug_analyzer.py
16.04.2026

csv analyzer

Author:
Nilusink
"""
from dash import Dash, dcc, html, Input, Output, Patch, State, ctx
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
import os
import re


# FILEPATH = "./gps_buff.csv"
FOLDER = "./logs"


def compute_center_and_zoom(lat, lon):
    lat_min, lat_max = min(lat), max(lat)
    lon_min, lon_max = min(lon), max(lon)

    center = {
        "lat": (lat_min + lat_max) / 2,
        "lon": (lon_min + lon_max) / 2,
    }

    # crude but effective zoom heuristic
    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min
    max_range = max(lat_range, lon_range)

    if max_range > 20:
        zoom = 3
    elif max_range > 10:
        zoom = 5
    elif max_range > 5:
        zoom = 7
    elif max_range > 1:
        zoom = 10
    else:
        zoom = 13

    return center, zoom


files = []
for file in os.listdir(FOLDER):
    try:
        file_time = float(file.lstrip("gps_debug_").rstrip(".csv"))

    except ValueError:
        continue

    files.append((file_time, file))

files = sorted(files, key=lambda x: x[0])

file_path = os.path.join(FOLDER, files[-1][1])
if not os.path.isfile(file_path):
    exit(1)

with open(file_path, "r") as f:
    raw_data = f.readlines()[:-1]

init_t = float(raw_data[0].split(",")[0])
df = pd.DataFrame([
    {
        "time": (float(t) - init_t) / 60,
        "mode": int(m),
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lat else None,
        "speed": round(float(speed), 2) if speed else None,
        "angle": float(a) if (a := angle.strip()) else None,
    }
    for i, line in enumerate(raw_data)
    for t, m, lat, lon, speed, angle in [line.split(",")]
])


# ----------------------------
# Figure builders
# ----------------------------
def make_map(selected_index=0):
    fig = go.Figure()

    # Full route
    center, zoom = compute_center_and_zoom(df["lat"], df["lon"])
    print(zoom)
    fig.add_trace(go.Scattermap(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines",
        line=dict(width=3),
        marker=dict(size=7),
        name="Route",
        hovertemplate="<extra></extra>"
    ))

    # Current synced point
    fig.add_trace(go.Scattermap(
        lat=[df.loc[selected_index, "lat"]],
        lon=[df.loc[selected_index, "lon"]],
        mode="markers",
        marker=dict(size=18, color="red"),
        name="Current Point",
        hovertemplate=(
            f"{round(df.loc[selected_index, "speed"], 2)}km/h<br>"
            f"{str(df.loc[selected_index, "time"]).split(".")[0]}min "
            f"{round(float("0."+str(df.loc[selected_index, "time"]).split(".")[1])*60, 1)}s "
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Route Map",
        height=700,
        uirevision="stay",

        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),

        template="plotly_dark",
        showlegend=False,

        map=dict(
            center=center,
            zoom=zoom,
            style="carto-darkmatter"
        ),
    )
    return fig


def make_graph(selected_index=0):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["speed"],
        mode="lines",
        name="Speed",
        hovertemplate="<extra></extra>"
    ))

    # Current synced point
    fig.add_trace(go.Scatter(
        x=[df.loc[selected_index, "time"]],
        y=[df.loc[selected_index, "speed"]],
        mode="markers",
        marker=dict(size=16, color="red"),
        name="Current Point",
        showlegend=False,
        hovertemplate=(
            f"{round(df.loc[selected_index, "speed"], 2)}km/h<br>"
            f"{str(df.loc[selected_index, "time"]).split(".")[0]}min "
            f"{round(float("0."+str(df.loc[selected_index, "time"]).split(".")[1])*60, 1)}s "
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        uirevision="stay",
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_dark",
        legend=dict(
            orientation="h",
            y=1.08,
            x=.5,
            xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0
        ),
    )
    return fig


def get_recording_files():
    files = []
    pattern = re.compile(r"gps_debug_(\d+(?:\.\d+)?)\.csv")

    for file in os.listdir(FOLDER):
        match = pattern.match(file)
        if match:
            ts = float(match.group(1))
            dt = datetime.fromtimestamp(ts)

            files.append({
                "label": dt.strftime("%Y-%m-%d %H:%M"),
                "value": os.path.join(FOLDER, file),
                "sort_ts": ts
            })

    # newest first
    files.sort(key=lambda x: x["sort_ts"], reverse=True)

    # remove helper key
    for f in files:
        del f["sort_ts"]

    return files


# ----------------------------
# Dash app
# ----------------------------
app = Dash(__name__)

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

app.layout = html.Div(
    [
        html.H1("GPS Debugger", title="GPS Debugger", className="title"),
        html.Label("Select recording:"),
        dcc.Dropdown(
            id="recording-dropdown",
            options=get_recording_files(),
            value=get_recording_files()[0]["value"] if get_recording_files() else None,
            clearable=False
        ),
        dcc.Graph(
            id="map", className="graph-top", clear_on_unhover=False,
            figure=make_map(0), config={"responsive": True}
        ),
        dcc.Graph(
            id="graph", className="graph-bottom", clear_on_unhover=False,
            figure=make_graph(0), config={"responsive": True}
        ),
    ],
    id="main-container",
)


# refresh dropdown options
# @app.callback(
#     Output("recording-dropdown", "options"),
#     Input("refresh-files", "n_intervals")
# )
# def refresh_dropdown(_):
#     return get_recording_files()


# Hover line graph -> sync map + graph marker
@app.callback(
    Output("map", "figure"),
    Output("graph", "figure"),
    Input("graph", "hoverData"),
    Input("map", "hoverData"),
    State("map", "figure"),
    State("graph", "figure")
)
def sync(graph_hover, map_hover, map_fig, graph_fig):

    trigger = ctx.triggered_id

    idx = 0
    if trigger == "graph":
        # sync graph -> map
        if graph_hover and "points" in graph_hover:
            t = graph_hover["points"][0]["x"]
            idx = (df["time"] - t).abs().idxmin()

    elif trigger == "map":
        # sync map -> graph
        if map_hover and "points" in map_hover:
            t = map_hover["points"][0]["lat"]
            idx = (df["lat"] - t).abs().idxmin()

    # --- PATCH ONLY MARKER ON MAP ---
    map_patch = Patch()
    map_patch["data"][1]["lat"] = [df.loc[idx, "lat"]]
    map_patch["data"][1]["lon"] = [df.loc[idx, "lon"]]
    map_patch["data"][1]["hovertemplate"] = (
        f"{round(df.loc[idx, "speed"], 2)}km/h<br>"
        f"{str(df.loc[idx, "time"]).split(".")[0]}min "
        f"{round(float("0."+str(df.loc[idx, "time"]).split(".")[1])*60, 1)}s "
        "<extra></extra>"
    )

    # --- PATCH ONLY GRAPH MARKER ---
    graph_patch = Patch()
    graph_patch["data"][1]["x"] = [df.loc[idx, "time"]]
    graph_patch["data"][1]["y"] = [df.loc[idx, "speed"]]
    graph_patch["data"][1]["hovertemplate"] = (
        f"{round(df.loc[idx, "speed"], 2)}km/h<br>"
        f"{str(df.loc[idx, "time"]).split(".")[0]}min "
        f"{round(float("0."+str(df.loc[idx, "time"]).split(".")[1])*60, 1)}s "
        "<extra></extra>"
    )

    return map_patch, graph_patch


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
    print("run")
    # app.run(debug=True)
