import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc, callback, Input, Output, State

dash.register_page(__name__, path="/results")

layout = html.Div(
    [
        html.H2("Results"),
        dcc.Store(id="result-store", storage_type="session"),
        html.Div(id="results-content"),
    ]
)


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

    def table_from_df(df: pd.DataFrame) -> dash_table.DataTable:
        return dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
        )

    return html.Div(
        [
            html.H3("Schedule"),
            table_from_df(schedule_df),
            html.H3("Hours"),
            table_from_df(hours_df),
            html.H3("KPI"),
            table_from_df(kpi_df),
        ]
    )
