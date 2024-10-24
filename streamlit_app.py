import pandas as pd
import streamlit as st
import requests
import json
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math

# Define a function to load chart data from Upstox API
@st.cache_data
def load_chart_data(symbol):
    instrument_key = f"NSE_EQ|{isin}"  # Modify as per your API's requirements
    interval = "1d"  # Adjust the interval as needed
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    
    url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"
    headers = {
        'Accept': 'application/json'
        # You may need to include authentication headers, depending on the API requirements
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        
        # Assuming data contains a list of candle data
        df = pd.DataFrame(data['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # Convert timestamp to datetime
        
        chart_data = pd.DataFrame({
            "time": df["timestamp"].dt.strftime("%Y-%m-%d"),
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "volume": df["volume"]
        })

        # Calculate daily percentage change
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        daily_change = ((current_price - prev_price) / prev_price) * 100

        return chart_data, current_price, df['volume'].iloc[-1], daily_change
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading data for {symbol}: {e}")
        return None, None, None, None

def create_chart(chart_data, name, symbol, current_price, volume, daily_change):
    if chart_data is not None:
        chart_height = 450
        chart = StreamlitChart(height=chart_height)

        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'      
        
        st.markdown(f"""
        <div class="stock-info">
            <span style='font-size: 16px; font-weight: bold;'>{name}</span>
            <span style='color: #00ff55;'>₹{current_price:.2f}</span> | 
            <span style='color: {change_color};'>{change_symbol} {abs(daily_change):.2f}%</span> | 
            Vol: {volume:,.0f}
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
        
        chart.time_scale(right_offset=5, min_bar_spacing=10)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data)
        return chart
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
            with st.spinner(f"Loading {stocks_df['stock_name'].iloc[i]}..."):
                symbol = stocks_df['symbol'].iloc[i]
                name = stocks_df['stock_name'].iloc[i]
                chart_data, current_price, volume, daily_change = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, name, symbol, current_price, volume, daily_change)
                    if chart:
                        chart.load()

        # Second chart (if available)
        with col2:
            if i + 1 < end_idx:
                with st.spinner(f"Loading {stocks_df['stock_name'].iloc[i + 1]}..."):
                    symbol = stocks_df['symbol'].iloc[i + 1]
                    name = stocks_df['stock_name'].iloc[i + 1]
                    chart_data, current_price, volume, daily_change = load_chart_data(symbol)
                    if chart_data is not None:
                        chart = create_chart(chart_data, name, symbol, current_price, volume, daily_change)
                        if chart:
                            chart.load()

    # Add a footer
    st.markdown("---")
    st.markdown("Developed by Laksh | Data provided by Upstox")
