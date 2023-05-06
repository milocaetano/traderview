import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ccxt
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import logging

logging.basicConfig(level=logging.DEBUG)

def get_data_from_ccxt():
    exchange = ccxt.binance()
    timeframe = '5m'
    since = exchange.parse8601(str((datetime.now() - timedelta(days=90)).date()) + 'T00:00:00Z')
    ohlcv_data = exchange.fetch_ohlcv('BTC/USDT', timeframe, since)

    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.drop('timestamp', axis=1, inplace=True)
    return df

def load_data():
    # Carrega os dados e resample para períodos de 5 minutos
    df = get_data_from_ccxt()
    df.set_index('Date', inplace=True)
    df = df.resample('5T').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    df.reset_index(inplace=True)
    return df


def create_candlestick_chart(df):
    chart = go.Figure(data=[go.Candlestick(x=df['Date'],
                                           open=df['Open'],
                                           high=df['High'],
                                           low=df['Low'],
                                           close=df['Close'],
                                           name='BTC')])
    chart.update_layout(title='Gráfico de Candlestick BTC - 5 minutos',
                        xaxis=dict(type='date', rangeslider=dict(visible=False), tickformat='%Y-%m-%d %H:%M'),
                        yaxis=dict(title='Price (USD)'),
                        uirevision='no_zoom',
                        height=800,
                        margin=dict(l=50, r=50, b=100, t=100, pad=4),
                        plot_bgcolor='#FFFFFF',
                        paper_bgcolor='#FFFFFF')
    return chart
def create_dash_app(df):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    app.layout = html.Div([
        dcc.Graph(id='candlestick-graph',
                  figure=create_candlestick_chart(df),
                  config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['select2d']}),
        dcc.Dropdown(
            id="label-dropdown",
            options=[
                {"label": "Uptrend", "value": "Uptrend"},
                {"label": "Downtrend", "value": "Downtrend"},
                {"label": "Congestion", "value": "Congestion"},
            ],
            value="Uptrend",
            clearable=False,
        ),
        html.Button('Exportar CSV', id='export-button'),
        dcc.Download(id="download-csv"),
    ])

    @app.callback(
        Output("download-csv", "data"),
        Input("export-button", "n_clicks"),
        State('candlestick-graph', 'relayoutData'),
        State("label-dropdown", "value"),
        prevent_initial_call=True
    )
    def export_csv(n_clicks, relayout_data, label):
        logging.debug(f"Botão Exportar CSV clicado {n_clicks} vezes.")
        if n_clicks:
            if relayout_data:
                logging.debug(f"Dados de layout: {relayout_data}")
                xaxis_range = [relayout_data.get("xaxis.range[0]"), relayout_data.get("xaxis.range[1]")]
                if all(x is not None for x in xaxis_range):
                    start_date, end_date = map(datetime.fromisoformat, xaxis_range)
                    logging.debug(f"Intervalo selecionado: {start_date} - {end_date}")
                    selected_data = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
                    selected_data["Label"] = label
                    selected_data.to_csv("exported_data.csv", index=False)
                    return dcc.send_file("exported_data.csv")
                else:
                    logging.debug("Nenhum intervalo selecionado.")
            else:
                logging.debug("Nenhum intervalo selecionado.")
        return None

    return app


    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    app.layout = html.Div([
        dcc.Graph(id='candlestick-graph',
                  figure=create_candlestick_chart(df),
                  config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['select2d'], 'dragmode': 'pan'}),
        dcc.Dropdown(
            id="label-dropdown",
            options=[
                {"label": "Uptrend", "value": "Uptrend"},
                {"label": "Downtrend", "value": "Downtrend"},
                {"label": "Congestion", "value": "Congestion"},
            ],
            value="Uptrend",
            clearable=False,
        ),
        html.Button('Exportar CSV', id='export-button'),
        dcc.Download(id="download-csv"),
    ])

    @app.callback(
        Output("download-csv", "data"),
        Input("export-button", "n_clicks"),
        State('candlestick-graph', 'relayoutData'),
        State("label-dropdown", "value"),
        prevent_initial_call=True
    )
    def export_csv(n_clicks, relayout_data, label):
        logging.debug(f"Botão Exportar CSV clicado {n_clicks} vezes.")
        if n_clicks:
            if relayout_data:
                logging.debug(f"Dados de layout: {relayout_data}")
                xaxis_range = [relayout_data.get("xaxis.range[0]"), relayout_data.get("xaxis.range[1]")]
                if all(x is not None for x in xaxis_range):
                    start_date, end_date = map(datetime.fromisoformat, xaxis_range)
                    logging.debug(f"Intervalo selecionado: {start_date} - {end_date}")
                    selected_data = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
                   
                    selected_data["Label"] = label
                    selected_data.to_csv("exported_data.csv", index=False)
                    return dcc.send_file("exported_data.csv")
                else:
                    logging.debug("Nenhum intervalo selecionado.")
            else:
                logging.debug("Nenhum intervalo selecionado.")
        return None

    return app

if __name__ == "__main__":
    data = load_data()
    app = create_dash_app(data)
    app.run_server(debug=True)
