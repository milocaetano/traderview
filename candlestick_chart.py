import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import ccxt
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import logging

##Version working okay ( but need to be improved: vertical resize)
##loading chart next and previous day
logging.basicConfig(level=logging.DEBUG)

current_date = datetime.now() - timedelta(days=3)

def get_data_from_ccxt(target_date=None):
    exchange = ccxt.binance()
    timeframe = '5m'
    
    if target_date is None:
        since = exchange.parse8601(str(current_date.date()) + 'T00:00:00Z')      
    else:
        since = exchange.parse8601(str((target_date - timedelta(days=2.5)).date()) + 'T00:00:00Z')
        
    ohlcv_data = exchange.fetch_ohlcv('BTC/USDT', timeframe, since)

    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.drop('timestamp', axis=1, inplace=True)
    return df

def load_data(target_date=None):
    df = get_data_from_ccxt(target_date)
    df.set_index('Date', inplace=True)
    df = df.resample('5T').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    df.reset_index(inplace=True)
    return df
def create_candlestick_chart(df):
    trace = go.Candlestick(x=df['Date'],
                           open=df['Open'],
                           high=df['High'],
                           low=df['Low'],
                           close=df['Close'])
    layout = go.Layout(xaxis={'type': 'category'}, yaxis={'title': 'Price'})
    return {'data': [trace], 'layout': layout}


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
                        paper_bgcolor='#FFFFFF',
                        dragmode='pan')
    return chart

def create_dash_app(df):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

        
    app.layout = html.Div([
        dcc.Graph(id='candlestick-graph',
                figure=create_candlestick_chart(df),
                config={'displayModeBar': True, 'scrollZoom': True, 'modeBarButtonsToAdd': ['select2d']}),
        # restante do código        
        
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
        html.Button('1 dia atrás', id='back-button'),
        html.Button('1 dia à frente', id='forward-button'),
        dcc.Store(id='date-storage', data=df['Date'].min())
    ])
    
    @app.callback(
        Output('candlestick-graph', 'figure'),
        Input('back-button', 'n_clicks'),
        Input('forward-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_button_clicks(back_clicks, forward_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            logging.info("Nenhum botão foi clicado ainda.")
            raise dash.exceptions.PreventUpdate
        else:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        global current_date
        if back_clicks:
            current_date -= timedelta(days=1)
            new_df = get_data_from_ccxt(current_date)
            return create_candlestick_chart(new_df)
        elif forward_clicks:
            current_date += timedelta(days=1)
            new_df = get_data_from_ccxt(current_date)
            return create_candlestick_chart(new_df)
        else:
            raise dash.exceptions.PreventUpdate

    # def handle_button_clicks(back_clicks, forward_clicks, stored_date):
    #     ctx = dash.callback_context
    #     if not ctx.triggered:
    #         raise dash.exceptions.PreventUpdate
    #     else:
    #         button_id = ctx.triggered[0]['prop_id'].split('.')[0']

    #     # Convertendo a data armazenada para um objeto datetime
    #     stored_date = datetime.strptime(stored_date, "%Y-%m-%d %H:%M:%S.%f")

    #     if button_id == 'back-button':
    #         logging.debug("Você clicou no botão esquerdo.")
    #         return (stored_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    #     elif button_id == 'forward-button':
    #         logging.debug("Você clicou no botão direito.")
    #         return (stored_date + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S.%f")


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
