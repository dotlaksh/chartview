import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from lightweight_charts import Chart

# API URL Template and Headers
API_URL = "https://api.upstox.com/v2/historical-candle/NSE_EQ%7C{symbol}/{interval}/{end_date}/{start_date}"
HEADERS = {'Accept': 'application/json'}

@st.cache_data
def load_chart_data(symbol, time_period='1mo', interval='day'):
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Format the URL and fetch data
        url = API_URL.format(symbol=symbol, interval=interval, start_date=start_date, end_date=end_date)
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            st.error(f"Error {response.status_code}: {response.text}")
            return None, None

        data = response.json()
        df = pd.DataFrame(data['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

        # Prepare chart data for candlestick plotting
        chart_data = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        chart_data['time'] = chart_data['timestamp'].dt.strftime("%Y-%m-%d")
        chart_data.drop('timestamp', axis=1, inplace=True)

        return chart_data

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Streamlit Sidebar for user input
st.sidebar.header("Select Options")
symbol = st.sidebar.text_input("Enter Stock Symbol", value="INFY")
interval = st.sidebar.selectbox("Select Interval", ['day', 'week', 'month'])
time_period = st.sidebar.selectbox("Select Time Period", ['1mo', '1yr'])

# Load chart data
chart_data = load_chart_data(symbol, time_period, interval)

# Display the candlestick chart
if chart_data is not None:
    st.write(f"### {symbol} - Candlestick Chart")

    # Initialize TradingView lightweight chart
    chart = Chart()
    chart.setOptions({
        "width": 800,
        "height": 400,
        "layout": {"background": {"color": "#FFFFFF"}, "textColor": "#000"},
        "grid": {"vertLines": {"color": "#E0E0E0"}, "horzLines": {"color": "#E0E0E0"}},
    })

    # Add candlestick series to the chart
    candlestick_series = chart.addCandlestickSeries()
    candlestick_series.setData(chart_data.to_dict(orient='records'))

    # Render the chart
    st.write(chart)
else:
    st.warning("No data available. Please check your inputs.")
