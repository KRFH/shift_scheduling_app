import dash
from dash import html, dcc

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
