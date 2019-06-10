import json
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
    "GEOSERVER_LOCATION", "http://localhost:8080/geoserver/"
)
WFS_URL = urljoin(GEOSERVER_LOCATION, "wfs")
WMS_URL = urljoin(GEOSERVER_LOCATION, "wms")
MAPBOX_ACCESS_TOKEN = os.getenv(
    "MAPBOX_ACCESS_TOKEN",
    "pk.eyJ1IjoiY2FydG9sb2dpYyIsImEiOiJjanc0a292ejUwdDg0NGFvNjMxNXU4ZTlsIn0.Bes3yfK13D6aOAhoKniOpg",
)


def build_wms_layer_url(base_url, layername):
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


def get_map_graph_layout(title="CPI Choropleth Map"):
    return go.Layout(
        title=go.layout.Title(text=title),
        geo=go.layout.Geo(
            scope="world",
            projection=go.layout.geo.Projection(type="mercator", scale=3.5),
            showlakes=True,
            showland=True,
            center={"lon": 23.992767, "lat": 5.088892},
        ),
    )


def get_map_choropleth(locations, z, locationmode="ISO-3", title="CPI"):
    return go.Choropleth(
        autocolorscale=True,
        locations=locations,
        z=z,
        locationmode=locationmode,
        marker=go.choropleth.Marker(
            line=go.choropleth.marker.Line(color="rgb(255,255,255)", width=2)
        ),
        colorbar=go.choropleth.ColorBar(title=title),
    )


def get_bar_trace(df, x_col, y_col, name="CPI"):
    trace = go.Bar(
        x=df[x_col], y=df[y_col], name=name, marker=dict(color="rgb(49,130,189)")
    )
    return trace


def get_bar_trace_layout(x_col, y_col, title="CPI Line Chart"):
    layout = dict(title=title, xaxis=dict(title=x_col), yaxis=dict(title=y_col))
    return layout


def get_years(layername, col="data_year"):
    df = get_filtered_data_frame(layername=layername)
    years = getattr(df, col).unique()
    return years


INDICATORS = {
    "geonode:cpi_layer": {"title": "CPI indicator"},
    "geonode:fiscal_balance_layer": {"title": "Fiscal Balance indicator"},
}

YEARS = get_years("geonode:cpi_layer")
app = dash.Dash(__name__)
app.layout = html.Div(
    className="full-height",
    children=[
        html.H1(children="Arab Spatial Dashboard", className="text-center"),
        html.Br(),
        dcc.Dropdown(
            id="layer-selector",
            options=[
                {"label": "CPI", "value": "geonode:cpi_layer"},
                {"label": "Fiscal Balance", "value": "geonode:fiscal_balance_layer"},
            ],
            value="geonode:cpi_layer",
            placeholder="Select a indicator",
            clearable=False,
        ),
        html.Div(
            className="slider-container",
            children=[dcc.Slider(id="year_slider", value=1990)],
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


@app.callback(Output("year_slider", "min"), [Input("layer-selector", "value")])
def layer_inidicator_min(indicator):
    if indicator:
        return min(get_years(indicator))
    else:
        return 0


@app.callback(Output("year_slider", "max"), [Input("layer-selector", "value")])
def layer_inidicator_max(indicator):
    if indicator:
        return max(get_years(indicator))
    else:
        return 0


@app.callback(Output("year_slider", "marks"), [Input("layer-selector", "value")])
def layer_inidicator_marks(indicator):
    years = get_years(indicator)
    return {str(year): str(year) for year in years}


@app.callback(
    Output("mapDiv", "figure"),
    [Input("year_slider", "value"), Input("layer-selector", "value")],
)
def time_series_figure(selected_year, selected_layer):
    title = INDICATORS[selected_layer]["title"]
    dff = get_filtered_data_frame(selected_layer, col="data_year", value=selected_year)
    figure_data = [
        get_map_choropleth(dff["iso3"], dff["data_value"].astype(float), title=title)
    ]
    return go.Figure(data=figure_data, layout=get_map_graph_layout(title=title))


@app.callback(
    Output("bar-chart", "figure"),
    [Input("year_slider", "value"), Input("layer-selector", "value")],
)
def time_series_bar_chart(selected_year, selected_layer):
    title = INDICATORS[selected_layer]["title"]
    dff = get_filtered_data_frame(selected_layer, col="data_year", value=selected_year)
    figure_data = dict(
        data=[get_bar_trace(dff, "iso3", "data_value", name=title)],
        layout=get_bar_trace_layout("Year", "CPI", title=title),
    )
    return go.Figure(figure_data)


@app.callback(
    Output("mapbox-map", "figure"),
    [Input("year_slider", "value"), Input("layer-selector", "value")],
)
def mapbox_map_time_series(selected_year, selected_layer):

    dff = get_filtered_data_frame(selected_layer, col="data_year", value=selected_year)
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
