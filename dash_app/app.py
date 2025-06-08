import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html

from base_layout import base_layout

# Allow importing project modules when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server

app.layout = base_layout(dash.page_container)

if __name__ == "__main__":
    app.run_server(debug=True)
