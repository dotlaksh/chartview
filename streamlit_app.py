import pandas as pd
import streamlit as st
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
import math
from datetime import datetime, timedelta

# Load stock data from CSV
@st.cache_data
def load_stock_data():
    try:
        df = pd.read_csv('nse.csv')
        print("Available columns:", df.columns.tolist())
        
        if len(df.columns) == 1:
            df.columns = ['symbol']
        
        if 'symbol' not in df.columns:
            df = df.rename(columns={df.columns[0]: 'symbol'})
        
        # Clean the symbols
        df['symbol'] = df['symbol'].str.strip()
        
        # Debug print
        print("First few symbols:", df['symbol'].head().tolist())
        
        return df
    except Exception as e:
        st.error(f"Error loading nse.csv: {e}")
        return pd.DataFrame(columns=['symbol'])

@st.cache_data
def load_chart_data(symbol):
    try:
        # Debug print
        print(f"Loading data for symbol: {symbol}")
        
        # Add .NS only if it's not already there
        ticker = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        df = yf.download(ticker,period='ytd', interval='1d')
        
        if df.empty:
            print(f"No data received for {ticker}")
            return None, None, None, None
            
        df.reset_index(inplace=True)
        
        # Debug print
        print(f"Data loaded for {ticker}, shape: {df.shape}")
        
        chart_data = pd.DataFrame({
            "time": df["Date"].dt.strftime("%Y-%m-%d"),
            "open": df["Open"].round(2),
            "high": df["High"].round(2),
            "low": df["Low"].round(2),
            "close": df["Close"].round(2),
            "volume": df["Volume"].round(2)
        })
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        daily_change = ((current_price - prev_price) / prev_price) * 100
        
        return chart_data, current_price, df['Volume'].iloc[-1], daily_change
    except Exception as e:
        print(f"Error loading data for {symbol}: {e}")
        return None, None, None, None

def create_chart(chart_data, symbol, current_price, volume, daily_change):
    try:
        if chart_data is None or chart_data.empty:
            print(f"No chart data for {symbol}")
            return None
            
        chart_height = 450
        chart = StreamlitChart(height=chart_height)

        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'      
        
        st.markdown(f"""
        <div class="stock-info">
            <span style='font-size: 16px; font-weight: bold;'>{symbol}</span>
            <span style='color: #00ff55;'>₹{current_price:.2f}</span> | 
            <span style='color: {change_color};'>{change_symbol} {abs(daily_change):.2f}%</span> | 
            Vol: {volume:,.0f}
        </div>
        """, unsafe_allow_html=True)

        # Print first few rows of chart data for debugging
        print(f"Chart data for {symbol}:")
        print(chart_data.head())

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
        
        chart.time_scale(right_offset=5, min_bar_spacing=10)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data.to_dict('records'))
        
        return chart
    except Exception as e:
        print(f"Error creating chart for {symbol}: {e}")
        return None

# Page setup
st.set_page_config(layout="wide", page_title="ChartView 2.0", page_icon="📈")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stSelectbox, .stTextInput {
        background-color: #262730;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stock-info {
        background-color: #1E222D;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session states
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Sidebar
with st.sidebar:
    st.title("📊 ChartView 2.0")
    st.markdown("---")
    search_term = st.text_input("🔍 Search for a stock symbol:", "")

# Get stocks data and display charts
stocks_df = load_stock_data()

# Show first few symbols in the sidebar for debugging
with st.sidebar:
    st.write("First few symbols in CSV:")
    st.write(stocks_df['symbol'].head().tolist())

# Filter stocks based on search term
if search_term:
    stocks_df = stocks_df[stocks_df['symbol'].str.contains(search_term, case=False)]

# Display the total number of stocks for debugging
st.sidebar.write(f"Total stocks: {len(stocks_df)}")

CHARTS_PER_PAGE = 12
total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

# Pagination controls
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if st.button("← Previous", key='prev', disabled=(st.session_state.current_page == 1)):
        st.session_state.current_page -= 1
        st.rerun()

with col2:
    st.write(f"Page {st.session_state.current_page} of {total_pages}")

with col3:
    if st.button("Next →", key='next', disabled=(st.session_state.current_page == total_pages)):
        st.session_state.current_page += 1
        st.rerun()

# Determine start and end indices for pagination
start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))

# Display charts in a loop
for i in range(start_idx, end_idx, 2):
    col1, col2 = st.columns([1, 1], gap='small')

    # First chart
    with col1:
        symbol = stocks_df['symbol'].iloc[i]
        st.write(f"Loading data for: {symbol}")  # Debug message
        with st.spinner(f"Loading {symbol}..."):
            chart_data, current_price, volume, daily_change = load_chart_data(symbol)
            if chart_data is not None:
                chart = create_chart(chart_data, symbol, current_price, volume, daily_change)
                if chart:
                    chart.load()
                else:
                    st.write(f"Failed to create chart for {symbol}")
            else:
                st.write(f"No data available for {symbol}")

    # Second chart (if available)
    with col2:
        if i + 1 < end_idx:
            symbol = stocks_df['symbol'].iloc[i + 1]
            st.write(f"Loading data for: {symbol}")  # Debug message
            with st.spinner(f"Loading {symbol}..."):
                chart_data, current_price, volume, daily_change = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, symbol, current_price, volume, daily_change)
                    if chart:
                        chart.load()
                    else:
                        st.write(f"Failed to create chart for {symbol}")
                else:
                    st.write(f"No data available for {symbol}")

# Add a footer
st.markdown("---")
st.markdown("Developed by Laksh | Data provided by Yahoo Finance")
