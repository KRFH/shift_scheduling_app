import sys
from pathlib import Path

import dash
from dash import html, dcc

# Allow importing project modules when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = dash.Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1("Shift Scheduling App"),
    html.Div([
        dcc.Link("Upload Input", href="/"),
        " | ",
        dcc.Link("Results", href="/results"),
    ]),
    dash.page_container,
])

if __name__ == "__main__":
    app.run_server(debug=True)
