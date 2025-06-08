import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc, callback, Input, Output
import plotly.express as px

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
    demand_df = None
    avail_df = None
    if "demand" in data and "availability" in data:
        demand_df = pd.read_json(data["demand"], orient="split")
        avail_df = pd.read_json(data["availability"], orient="split")

    def table_from_df(df: pd.DataFrame) -> dash_table.DataTable:
        return dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": c, "id": c} for c in df.columns],
        )

    components = []
    if demand_df is not None and avail_df is not None:
        slot_order = ["10-14", "14-18", "18-22", "22-26"]
        demand_df["Slot"] = pd.Categorical(demand_df["Slot"], slot_order, ordered=True)
        avail_ok = avail_df[avail_df["Availability"].isin(["OK", "Wish"])]
        avail_wish = avail_df[avail_df["Availability"] == "Wish"]
        ok_counts = (
            avail_ok.groupby(["Date", "Slot"]).size().rename("AvailableOK")
        )
        wish_counts = (
            avail_wish.groupby(["Date", "Slot"]).size().rename("AvailableWish")
        )
        summary = (
            demand_df.merge(ok_counts, on=["Date", "Slot"], how="left")
            .merge(wish_counts, on=["Date", "Slot"], how="left")
            .fillna(0)
        )
        summary["Gap"] = summary["RequiredCnt"] - summary["AvailableOK"]
        pivot = summary.pivot(index="Date", columns="Slot", values="Gap").sort_index()
        max_gap = pivot.abs().max().max()
        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="RdBu",
            zmin=-max_gap,
            zmax=max_gap,
        )
        summary = summary.sort_values(["Date", "Slot"])
        summary["Time"] = summary["Date"] + " " + summary["Slot"].astype(str)
        fig_area = px.area(
            summary,
            x="Time",
            y=["RequiredCnt", "AvailableOK", "AvailableWish"],
        )
        components.extend([
            dcc.Graph(figure=fig_heat),
            dcc.Graph(figure=fig_area),
        ])

    components.extend(
        [
            html.H3("Schedule"),
            table_from_df(schedule_df),
            html.H3("Hours"),
            table_from_df(hours_df),
            html.H3("KPI"),
            table_from_df(kpi_df),
        ]
    )

    return html.Div(components)
