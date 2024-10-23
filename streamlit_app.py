import streamlit as st
import yfinance as yf
import pandas as pd
from lightweight_charts import Chart

# Load stock symbols from CSV file
nse_symbols = pd.read_csv('nse.csv')

# Sidebar selection for the stock symbol
st.sidebar.title("Select Stock Symbol")
selected_symbol = st.sidebar.selectbox("Symbol", nse_symbols['Symbol'])

# Ensure the symbol is correctly formatted for NSE
formatted_symbol = f"{selected_symbol}.NS"

# Fetch data from yfinance
def get_stock_data(symbol):
    stock_data = yf.download(symbol, period='ytd', interval='1d')
    stock_data.reset_index(inplace=True)
    return stock_data

# Display the stock chart as a candlestick chart
def show_candlestick_chart(stock_data):
    chart = Chart()

    # Prepare data for the candlestick chart
    chart_data = [
        {
            "time": row["Date"].strftime("%Y-%m-%d"),
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume":row["volume"]
        }
        for _, row in stock_data.iterrows()
    ]

    # Add candlestick series using correct method to create a candle-like effect
    candlestick_series = chart.add_series('Candlestick', chart_data)
    
    # Set the data and render the chart
    candlestick_series.set_data(chart_data)
    chart.show("chart-container", display=True)

# Main app
st.title("Stock Candlestick Chart Viewer")
if selected_symbol:
    st.write(f"Displaying candlestick chart for: {formatted_symbol}")
    
    # Get stock data
    data = get_stock_data(formatted_symbol)
    
    if not data.empty:
        st.write(data)
        
        # Render the candlestick chart using lightweight charts
        show_candlestick_chart(data)
    else:
        st.write("No data available for this symbol.")
