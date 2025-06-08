import base64
from io import BytesIO

import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State

from shift_optimizer import InputData, ShiftSchedulingModel


def read_data_from_bytes(data: bytes) -> InputData:
    xls = pd.ExcelFile(BytesIO(data))
    staff = pd.read_excel(xls, "Staff")
    avail = pd.read_excel(xls, "Availability")
    demand = pd.read_excel(xls, "Demand")
    wages = pd.read_excel(xls, "Wages").iloc[0]
    return InputData(staff, avail, demand, wages)


dash.register_page(__name__, path="/")

layout = html.Div(
    [
        html.H2("Upload Input"),
        dcc.Upload(id="upload-data", children=dbc.Button("Select Excel File")),
        dbc.Button("Run Optimization", id="run-button", className="mt-2"),
        html.Div(id="run-status", className="mt-2"),
        dcc.Store(id="result-store", storage_type="session"),
    ]
)


@callback(
    Output("run-status", "children"),
    Output("result-store", "data"),
    Input("run-button", "n_clicks"),
    State("upload-data", "contents"),
    prevent_initial_call=True,
)
def run_optimizer(n_clicks, contents):
    if contents is None:
        return "Please upload a file first.", dash.no_update
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    data = read_data_from_bytes(decoded)
    model = ShiftSchedulingModel(data)
    model.build()
    model.solve()
    schedule_df, hours_df, kpi_df = model.results()
    result = {
        "schedule": schedule_df.to_json(orient="split"),
        "hours": hours_df.to_json(orient="split"),
        "kpi": kpi_df.to_json(orient="split"),
        "availability": data.availability.to_json(orient="split"),
        "demand": data.demand.to_json(orient="split"),
    }
    return "Optimization complete.", result
