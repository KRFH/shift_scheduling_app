import dash_bootstrap_components as dbc
from dash import html


def base_layout(content):
    return dbc.Container(
        [
            dbc.NavbarSimple(
                children=[
                    dbc.NavItem(dbc.NavLink("Upload", href="/")),
                    dbc.NavItem(dbc.NavLink("Results", href="/results")),
                ],
                brand="Shift Scheduling App",
                color="primary",
                dark=True,
                className="mb-4",
            ),
            content,
        ],
        fluid=True,
    )
