import pandas as pd
import dash
from dash import html, dash_table, dcc, callback, Input, Output, State

dash.register_page(__name__, path="/results")

layout = html.Div([
    html.H2("Results"),
    dcc.Store(id="result-store", storage_type="session"),
    html.Div(id="results-content"),
    html.Br(),
    dcc.Link("Back to Upload", href="/"),
])


@callback(
    Output("results-content", "children"),
    Input("result-store", "data"),
)
def display_results(data):
    if not data:
        return "No results available."
    schedule_df = pd.read_json(data["schedule"], orient="split")
    hours_df = pd.read_json(data["hours"], orient="split")
    kpi_df = pd.read_json(data["kpi"], orient="split")
    return html.Div([
        html.H3("Schedule"),
        dash_table.DataTable(schedule_df.to_dict("records"), list(schedule_df.columns)),
        html.H3("Hours"),
        dash_table.DataTable(hours_df.to_dict("records"), list(hours_df.columns)),
        html.H3("KPI"),
        dash_table.DataTable(kpi_df.to_dict("records"), list(kpi_df.columns)),
    ])
