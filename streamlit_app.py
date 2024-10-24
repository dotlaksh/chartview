import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from lightweight_charts.widgets import StreamlitChart

class UpstoxDataFetcher:
    def __init__(self):
        self.base_url = 'https://api.upstox.com/v2'
        self.headers = {'Accept': 'application/json'}

    def get_instrument_key(self, isin):
        return f"NSE_EQ|{isin}"  # Correct delimiter

    def get_historical_data(self, isin, interval='day', start_date=None):
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        instrument_key = self.get_instrument_key(isin)
        url = f"{self.base_url}/historical-candle/{instrument_key}/{interval}/{start_date}"

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'candles' in data['data']:
                    return self._process_candle_data(data['data']['candles'])
                else:
                    st.warning("No data available for the selected stock.")
            else:
                st.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
        return None

    def _process_candle_data(self, candles):
        processed_data = []
        for candle in candles:
            timestamp = datetime.fromisoformat(candle[0].replace('Z', '+00:00'))
            processed_data.append({
                'time': timestamp.strftime('%Y-%m-%d'),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })
        return processed_data

def main():
    st.title("Stock Market Data Visualization")

    isin_data = pd.read_csv('isin.csv')  # Ensure the file is available
    st.sidebar.header("Settings")

    # Stock selection logic
    search_term = st.sidebar.text_input("Search Company/Symbol").lower()
    filtered_data = isin_data[
        isin_data['Company Name'].str.lower().str.contains(search_term) |
        isin_data['Symbol'].str.lower().str.contains(search_term)
    ] if search_term else isin_data

    stock_options = [f"{row['Symbol']} - {row['Company Name']}" for _, row in filtered_data.iterrows()]
    if not stock_options:
        st.sidebar.warning("No matches found.")
        return

    selected_option = st.sidebar.selectbox("Select Stock", options=stock_options, index=0)
    selected_symbol = selected_option.split(' - ')[0]
    selected_stock_data = isin_data[isin_data['Symbol'] == selected_symbol].iloc[0]
    selected_isin = selected_stock_data['ISIN']

    # Display company information
    with st.expander("Company Information", expanded=True):
        col1, col2 = st.columns(2)
        col1.write(f"**Company Name:** {selected_stock_data['Company Name']}")
        col1.write(f"**Symbol:** {selected_stock_data['Symbol']}")
        col2.write(f"**Industry:** {selected_stock_data['Industry']}")
        col2.write(f"**ISIN:** {selected_stock_data['ISIN']}")

    start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=30))
    upstox_client = UpstoxDataFetcher()

    if st.sidebar.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            data = upstox_client.get_historical_data(selected_isin, start_date=start_date.strftime('%Y-%m-%d'))
            if data:
                # Separate data for the two series
                candlestick_data = [{
                    'time': d['time'],
                    'open': d['open'],
                    'high': d['high'],
                    'low': d['low'],
                    'close': d['close']
                } for d in data]

                volume_data = [{
                    'time': d['time'],
                    'value': d['volume'],
                    'color': '#26a69a' if d['close'] >= d['open'] else '#ef5350'
                } for d in data]

                # Define chart configuration
                chart_options = {
                    "width": 800,
                    "height": 600,
                    "layout": {
                        "textColor": "black",
                        "background": {"type": "solid", "color": "white"}
                    },
                    "priceScale": {"position": "right"},
                    "timeScale": {"timeVisible": True, "secondsVisible": False}
                }

                # Combine the two series for rendering
                series = [
                    {"type": "Candlestick", "data": candlestick_data, "name": f"{selected_symbol} Price"},
                    {"type": "Histogram", "data": volume_data, "name": "Volume", "color": "#26a69a"}
                ]

                # Render the chart
                render_lightweight_charts(series, chart_options)

if __name__ == "__main__":
    st.set_page_config(page_title="Stock Market Data Visualization", page_icon="📈", layout="wide")
    main()
