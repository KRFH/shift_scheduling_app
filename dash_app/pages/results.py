import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc, callback, Input, Output
import plotly.graph_objects as go

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
        demand_df["Slot"] = pd.Categorical(
            demand_df["Slot"], categories=slot_order, ordered=True
        )

        avail_ok = avail_df[avail_df["Availability"].isin(["OK", "Wish"])]
        avail_wish = avail_df[avail_df["Availability"] == "Wish"]

            avail_ok.groupby(["Date", "Slot"]).size().reset_index(name="AvailableOK")
            avail_wish.groupby(["Date", "Slot"]).size().reset_index(name="AvailableWish")
        )

        summary["Gap"] = summary["RequiredCnt"] - summary["AvailableOK"]

        pivot = summary.pivot(index="Date", columns="Slot", values="Gap").sort_index()
        max_gap = pivot.abs().max().max()
        fig_heat = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=list(pivot.columns),
                y=list(pivot.index),
                colorscale="RdBu",
                zmin=-max_gap,
                zmax=max_gap,
            )
        )

        summary = summary.sort_values(["Date", "Slot"])

            go.Scatter(
                x=summary["Time"],
                y=summary["AvailableWish"],
                name="AvailableWish",
                stackgroup="one",
                mode="lines",
            )
            go.Scatter(
                x=summary["Time"],
                y=summary["AvailableOK"],
                name="AvailableOK",
                stackgroup="one",
                mode="lines",
            )
        heatmap_section = html.Div(
                html.H4("Staffing Gap Heatmap"),
                html.P(
                    "Red cells show a shortage of confirmed staff (OK) versus demand; blue cells show surplus."
                ),
                dcc.Graph(figure=fig_heat),
            ],
            className="mb-4",
        )

        area_section = html.Div(
            [
                html.H4("Required vs Available Over Time"),
                html.P(
                    "Compare required workers with confirmed (OK) and wish availability across slots."
                ),
                dcc.Graph(figure=fig_area),
            ],
            className="mb-4",
        )
        components.extend([heatmap_section, area_section])

            html.Div(
                [html.H4("Shift Schedule"), table_from_df(schedule_df)],
                className="mb-4",
            ),
            html.Div(
                [html.H4("Work Hours Summary"), table_from_df(hours_df)],
                className="mb-4",
            ),
            html.Div(
                [html.H4("Key Performance Indicators"), table_from_df(kpi_df)],
                className="mb-4",
            ),
        fig_area.add_trace(go.Scatter(x=summary["Time"], y=summary["RequiredCnt"], name="RequiredCnt", mode="lines"))
        fig_area.update_layout(xaxis=dict(type="category"))
        components.extend(
            [
                dcc.Graph(figure=fig_heat),
                dcc.Graph(figure=fig_area),
            ]
        )

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
