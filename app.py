# import json
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import geopandas as gpd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from requests.models import PreparedRequest
from urllib.parse import urljoin
from requests.utils import unquote

current_dir = os.path.dirname(__file__)
GEOSERVER_LOCATION = os.getenv(
    "GEOSERVER_LOCATION", "http://plotly.cartoview.net/geoserver/"
)
WFS_URL = urljoin(GEOSERVER_LOCATION, "wfs")
WMS_URL = urljoin(GEOSERVER_LOCATION, "wms")
MAPBOX_ACCESS_TOKEN = os.getenv(
    "MAPBOX_ACCESS_TOKEN",
    "pk.eyJ1IjoiY2FydG9sb2dpYyIsImEiOiJjanc0a292ejUwdDg0NGFvNjMxNXU4ZTlsIn0.Bes3yfK13D6aOAhoKniOpg",
)


def build_wms_layer_url(base_url, layername, CQL_FILTER=None):
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
        "SRS": "EPSG:3857",
        "bbox": "{bbox-epsg-3857}",
        "LAYERS": layername,
        "WIDTH": 256,
        "HEIGHT": 256,
    }
    if CQL_FILTER:
        params.update({"cql_Filter": CQL_FILTER})
    req = PreparedRequest()
    req.prepare_url(base_url, params)
    return req.url


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
    return unquote(req.url)


def get_filtered_data_frame(layername="geonode:cpi_layer", col=None, value=None):
    url = build_get_features_url(WFS_URL, layername)
    df = gpd.read_file(url)
    if value and col:
        return df.loc[df[col] == value]
    # df["text"] = "code:" + df["iso3"] + "<br>" + "value:" + df["data_value"].astype(str)
    return df


def get_bar_trace(df, x_col, y_col, name="CPI", orientation="v"):
    trace = go.Bar(
        x=df[x_col],
        y=df[y_col],
        name=name,
        marker=dict(color="rgb(49,130,189)"),
        orientation=orientation,
    )
    return trace


def get_bar_trace_layout(x_col, y_col, title="Fiscal Balance indicator Chart"):
    layout = dict(title=title, xaxis=dict(title=x_col), yaxis=dict(title=y_col))
    return layout


def get_years(layername, col="data_year"):
    df = get_filtered_data_frame(layername=layername)
    years = getattr(df, col).unique()
    return years


INDICATORS = {"geonode:fiscal_balance_layer": {"title": "Fiscal Balance indicator"}}

YEARS = [i for i in range(1990, 2015, 1)]
app = dash.Dash(__name__)
app.layout = html.Div(
    className="full-height",
    children=[
        html.H1(children="Arab Spatial Dashboard", className="text-center"),
        html.Br(),
        html.Div(
            className="selectors-container",
            children=[
                dcc.Dropdown(
                    id="layer-selector",
                    options=[
                        {
                            "label": "Fiscal Balance",
                            "value": "geonode:fiscal_balance_{}",
                        }
                    ],
                    value="geonode:fiscal_balance_{}",
                    placeholder="Select a indicator",
                    clearable=False,
                ),
                dcc.Dropdown(
                    id="year_slider",
                    options=[
                        {"label": str(year), "value": str(year)} for year in YEARS
                    ],
                    value=str(min(YEARS)),
                    placeholder="Select a Year",
                    clearable=False,
                ),
            ],
        ),
        html.Br(),
        html.Br(),
        html.Div(
            className="charts-container",
            children=[dcc.Graph(id="bar-chart"), dcc.Graph(id="bar-chart2")],
        ),
        dcc.Graph(id="mapbox-map"),
    ],
)


@app.callback(
    Output("bar-chart2", "figure"),
    [
        Input("bar-chart", "clickData"),
        Input("layer-selector", "value"),
        Input("year_slider", "value"),
    ],
)
def country_years_chart(selected_data, selected_layer, selected_year):
    selected_layer = selected_layer.format(selected_year)
    title = "Fiscal Balance indicator"
    if selected_data:
        country = selected_data["points"][0]["y"]
        df = get_filtered_data_frame("geonode:fiscal_balance_layer", "iso3", country)
        data = get_bar_trace(df, "data_year", "data_value", title)
        layout = get_bar_trace_layout("Year", "Value", title=country)
        figure_data = dict(data=[data], layout=layout)
        return go.Figure(figure_data)
    layout = get_bar_trace_layout("Year", "Value", title="No Country Selected")
    return go.Figure(dict(data=[], layout=layout))


@app.callback(
    Output("bar-chart", "figure"),
    [Input("year_slider", "value"), Input("layer-selector", "value")],
)
def time_series_bar_chart(selected_year, selected_layer):
    title = "Fiscal Balance indicator"
    selected_layer = selected_layer.format(selected_year)
    dff = get_filtered_data_frame(selected_layer)
    figure_data = dict(
        data=[get_bar_trace(dff, "data_value", "iso3", name=title, orientation="h")],
        layout=get_bar_trace_layout("Value", "Country", title=title),
    )
    return go.Figure(figure_data)


@app.callback(
    Output("mapbox-map", "figure"),
    [
        Input("year_slider", "value"),
        Input("layer-selector", "value"),
        Input("bar-chart", "clickData"),
    ],
)
def mapbox_map_time_series(selected_year, selected_layer, selected_data):
    selected_layer = selected_layer.format(selected_year)
    country = None
    # if selected_data:
    #     country = selected_data["points"][0]["y"]

    # dff = get_filtered_data_frame(selected_layer, col="data_year", value=selected_year)
    # dff_json = dff.to_json()
    # dff_geojson = json.loads(dff_json)
    map_data = [go.Scattermapbox(lat=["24.667298"], lon=["25.664063"], mode="markers")]
    # if country:
    #     wms_filter = "data_year = '{}' and iso3 = '{}'".format(selected_year, country)
    # else:
    #     wms_filter = "data_year = '{}'".format(selected_year)
    map_layout = go.Layout(
        height=600,
        autosize=True,
        hovermode="closest",
        mapbox=dict(
            layers=[
                dict(
                    sourcetype="raster",
                    source=[build_wms_layer_url(WMS_URL, selected_layer)],
                    type="raster",
                    visible=True,
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
    app.run_server(debug=True, host="0.0.0.0")
