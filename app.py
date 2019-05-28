# import time
# import plotly
# first you have to load the geojson file

import json
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import geopandas as gpd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from requests.models import PreparedRequest

# external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
GEOSERVER_LOCATION = os.getenv(
    "GEOSERVER_LOCATION", '"http://localhost:8080/geoserver14-geonode/wfs"'
)
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "<Your_Access_Token>")
_CACHE = dict()


def build_get_features_url(base_url, layername):
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": layername,
        "outputFormat": "application/json",
    }
    req = PreparedRequest()
    req.prepare_url(base_url, params)
    return req.url


def get_filtered_data_frame(layername="geonode:cpi_layer", col=None, value=None):
    cache_value = _CACHE.get(layername, None)
    if cache_value:
        df = cache_value
    else:
        df = gpd.read_file(build_get_features_url(GEOSERVER_LOCATION, layername))
    if value and col:
        return df.loc[df[col] == value]
    # df["text"] = "code:" + df["iso3"] + "<br>" + "value:" + df["data_value"].astype(str)
    return df


def get_map_graph_layout(title="CPI Choropleth Map"):
    return go.Layout(
        title=go.layout.Title(text=title),
        geo=go.layout.Geo(
            scope="world",
            projection=go.layout.geo.Projection(type="mercator", scale=3.5),
            showlakes=True,
            showland=True,
            landcolor="darkblue",
            center={"lon": 23.992767, "lat": 5.088892},
            lakecolor="rgb(255, 255, 255)",
        ),
    )


def get_map_choropleth(locations, z, locationmode="ISO-3", **kwargs):
    return go.Choropleth(
        autocolorscale=True,
        locations=locations,
        z=z,
        locationmode=locationmode,
        marker=go.choropleth.Marker(
            line=go.choropleth.marker.Line(color="rgb(255,255,255)", width=2)
        ),
        colorbar=go.choropleth.ColorBar(title="CPI"),
        **kwargs
    )


def get_bar_trace(df, x_col, y_col, name="CPI"):
    trace = go.Bar(
        x=df[x_col], y=df[y_col], name=name, marker=dict(color="rgb(49,130,189)")
    )
    return trace


def get_bar_trace_layout(x_col, y_col, title="CPI Line Chart"):
    layout = dict(title=title, xaxis=dict(title=x_col), yaxis=dict(title=y_col))
    return layout


df = get_filtered_data_frame(col="year")
YEARS = list(set(df["data_year"]))
app = dash.Dash()

app = dash.Dash(__name__)
app.layout = html.Div(
    className="full-height",
    children=[
        html.H1(children="Arab Spatial Dashboard", className="text-center"),
        html.H6(children="""Arab Spatial CPI""", className="text-center"),
        html.Br(),
        html.Div(
            className="slider-container",
            children=[
                dcc.Slider(
                    id="year_slider",
                    min=min(YEARS),
                    max=max(YEARS),
                    value=min(YEARS),
                    marks={str(year): str(year) for year in YEARS},
                )
            ],
        ),
        html.Br(),
        html.Br(),
        html.Div(
            className="charts-container",
            children=[dcc.Graph(id="mapDiv"), dcc.Graph(id="bar-chart")],
        ),
        dcc.Graph(id="mapbox-map"),
    ],
)


@app.callback(Output("mapDiv", "figure"), [Input("year_slider", "value")])
def time_series_figure(selected_year):

    dff = get_filtered_data_frame(col="data_year", value=selected_year)
    figure_data = [get_map_choropleth(dff["iso3"], dff["data_value"].astype(float))]
    return go.Figure(data=figure_data, layout=get_map_graph_layout())


@app.callback(Output("bar-chart", "figure"), [Input("year_slider", "value")])
def time_series_bar_chart(selected_year):

    dff = get_filtered_data_frame(col="data_year", value=selected_year)
    figure_data = dict(
        data=[get_bar_trace(dff, "iso3", "data_value")],
        layout=get_bar_trace_layout("Year", "CPI"),
    )
    return go.Figure(figure_data)


@app.callback(Output("mapbox-map", "figure"), [Input("year_slider", "value")])
def mapbox_map_time_series(selected_year):

    dff = get_filtered_data_frame(col="data_year", value=selected_year)
    dff_json = dff.to_json()
    dff_geojson = json.loads(dff_json)
    map_data = [go.Scattermapbox(lat=["24.667298"], lon=["25.664063"], mode="markers")]
    map_layout = go.Layout(
        height=600,
        autosize=True,
        hovermode="closest",
        mapbox=dict(
            layers=[
                dict(
                    sourcetype="geojson",
                    source=dff_geojson,
                    type="fill",
                    color="rgb(49,130,189)",
                )
            ],
            accesstoken=MAPBOX_ACCESS_TOKEN,
            bearing=0,
            center=go.layout.mapbox.Center(lat=24.667298, lon=25.664063),
            pitch=0,
            zoom=3,
            style="light",
        ),
    )
    return go.Figure(dict(data=map_data, layout=map_layout))


if __name__ == "__main__":
    app.run_server(debug=True)