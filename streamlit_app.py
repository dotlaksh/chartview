import streamlit as st
import yfinance as yf
import pandas as pd
from lightweight_charts import Chart as StreamlitChart

# Load stock symbols from CSV file
nse_symbols = pd.read_csv('nse.csv')

# Sidebar selection for the stock symbol
st.sidebar.title("Select Stock Symbol")
selected_symbol = st.sidebar.selectbox("Choose a stock:", nse_symbols['Symbol'])

# Ensure the symbol is correctly formatted for NSE
formatted_symbol = f"{selected_symbol}.NS"

# Fetch data from yfinance
def get_stock_data(symbol):
    stock_data = yf.download(symbol, period='ytd', interval='1d')
    stock_data.reset_index(inplace=True)
    # Ensure the 'Date' column is in datetime format
    stock_data['Date'] = pd.to_datetime(stock_data['Date'])
    return stock_data

# Function to create and display the customized chart
def create_chart(chart_data, name, symbol, current_price, volume, daily_change):
    if chart_data is not None:
        chart_height = 450
        chart = StreamlitChart(height=chart_height)

        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'
        
        st.markdown(f"""
        <div class="stock-card">
            <div class="stock-header">
                <span class="stock-name">{symbol} | ₹{current_price:.2f} | {volume:,.0f} 
                <span style='color: {change_color};'>| {change_symbol} {abs(daily_change):.2f}% </span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        chart.layout(
            background_color='#1E222D',
            text_color='#FFFFFF',
            font_size=12,
            font_family='Helvetica'
        )
        
        chart.candle_style(
            up_color='#00ff55',
            down_color='#ed4807',
            wick_up_color='#00ff55',
            wick_down_color='#ed4807'
        )
        
        chart.volume_config(
            up_color='#00ff55',
            down_color='#ed4807'
        )
        
        chart.crosshair(
            mode='normal',
            vert_color='#FFFFFF',
            vert_style='dotted',
            horz_color='#FFFFFF',
            horz_style='dotted'
        )
        
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data)
        
        return chart
    return None

# Prepare data for the candlestick chart
def prepare_chart_data(stock_data):
    return [
        {
            "time": row["Date"].strftime("%Y-%m-%d"),
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume": row["Volume"]
        }
        for _, row in stock_data.iterrows()
    ]

# Main app
st.title("Stock Candlestick Chart Viewer")
if selected_symbol:
    st.write(f"Displaying candlestick chart for: {formatted_symbol}")
    
    # Get stock data
    data = get_stock_data(formatted_symbol)
    
    if not data.empty:
        # Calculate additional information
        current_price = data['Close'].iloc[-1]
        volume = data['Volume'].iloc[-1]
        daily_change = ((data['Close'].iloc[-1] - data['Open'].iloc[-1]) / data['Open'].iloc[-1]) * 100

        # Prepare chart data
        chart_data = prepare_chart_data(data)
        
        # Render the candlestick chart using the customized function
        create_chart(chart_data, selected_symbol, formatted_symbol, current_price, volume, daily_change)
    else:
        st.write("No data available for this symbol.")
