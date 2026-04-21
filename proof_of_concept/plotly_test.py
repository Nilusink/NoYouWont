import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ----------------------------
# Example telemetry data
# ----------------------------
df = pd.DataFrame({
    "time":  [0, 1, 2, 3, 4, 5],
    "speed": [0, 12, 28, 35, 30, 18],
    "lat":   [48.2082, 48.2090, 48.2105, 48.2120, 48.2130, 48.2140],
    "lon":   [16.3738, 16.3750, 16.3770, 16.3800, 16.3840, 16.3880],
})

# ----------------------------
# Figure builders
# ----------------------------
def make_map(selected_index=0):
    fig = go.Figure()

    # Full route
    fig.add_trace(go.Scattermap(
        lat=df["lat"],
        lon=df["lon"],
        mode="lines+markers",
        line=dict(width=3),
        marker=dict(size=7),
        name="Route",
        hoverinfo="skip"
    ))

    # Current synced point
    fig.add_trace(go.Scattermap(
        lat=[df.loc[selected_index, "lat"]],
        lon=[df.loc[selected_index, "lon"]],
        mode="markers",
        marker=dict(size=18, color="red"),
        name="Current Point",
        hovertemplate=(
            f"t={df.loc[selected_index,'time']}s"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Route Map",
        height=700,
        uirevision="stay",

        map=dict(
            style="open-street-map",
            center=dict(
                lat=df["lat"].mean(),
                lon=df["lon"].mean()
            ),
            zoom=13
        )
    )
    return fig


def make_graph(selected_index=0):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["speed"],
        mode="lines+markers",
        name="Speed"
    ))

    # Current synced point
    fig.add_trace(go.Scatter(
        x=[df.loc[selected_index, "time"]],
        y=[df.loc[selected_index, "speed"]],
        mode="markers",
        marker=dict(size=16, color="red"),
        name="Current Point"
    ))

    fig.update_layout(
        title="Route Map",
        height=700,
        uirevision="stay",

        map=dict(
            style="open-street-map",
            center=dict(
                lat=df["lat"].mean(),
                lon=df["lon"].mean()
            ),
            zoom=13
        )
    )
    return fig


# ----------------------------
# Dash app
# ----------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(
            id="map",
            figure=make_map(0),
            clear_on_unhover=False,
            style={"width": "50%"}
        ),

        dcc.Graph(
            id="graph",
            figure=make_graph(0),
            clear_on_unhover=False,
            style={"width": "50%"}
        )
    ], style={"display": "flex"})
])


# Hover line graph -> sync map + graph marker
@app.callback(
    Output("map", "figure"),
    Output("graph", "figure"),
    Input("graph", "hoverData")
)
def sync_from_graph(hover):
    if hover and "points" in hover:
        hovered_time = hover["points"][0]["x"]
        idx = (df["time"] - hovered_time).abs().idxmin()
    else:
        idx = 0

    return make_map(idx), make_graph(idx)


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)