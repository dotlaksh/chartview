import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager
import math
from datetime import datetime, timedelta
import time
import requests
from requests.exceptions import RequestException

# Time period mappings
TIME_PERIODS = {
    '1Y': '1y',
    '5Y': '5y',
    'Max': 'max'
}

INTERVALS = {
    'D': '1d',
    'W': '1wk',
    'M': '1mo'
}

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks1.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def get_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [table[0] for table in cursor.fetchall()]

def get_stocks_from_table(table_name):
    with get_db_connection() as conn:
        query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='1y', interval='1d', retries=3, delay=1):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            if df.empty:
                raise ValueError("No data received")
            return df
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Failed to fetch data after {retries} attempts: {str(e)}")
                return None
            time.sleep(delay)
            delay *= 2

def format_volume(volume):
    if volume >= 1_000_000:
        return f'{volume/1_000_000:.2f}M'
    elif volume >= 1_000:
        return f'{volume/1_000:.1f}K'
    return str(volume)

def load_chart_data(symbol, period, interval):
    ticker = f"{symbol}.NS"
    try:
        df = fetch_stock_data(ticker, period=period, interval=interval)
        if df is None:
            return None, None, None, None
            
        df = df.reset_index()
        
        chart_data = pd.DataFrame({
            "time": df["Date"].dt.strftime("%Y-%m-%d"),
            "open": df["Open"],
            "high": df["High"],
            "low": df["Low"],
            "close": df["Close"],
            "volume": df["Volume"]
        })

        current_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
        daily_change = ((current_price - prev_close) / prev_close) * 100
        volume = df['Volume'].iloc[-1]

        return chart_data, current_price, daily_change, volume

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None, None, None

def create_chart(chart_data, name, symbol, current_price, daily_change, volume):
    if chart_data is not None:
        chart = StreamlitChart(height=500)
        
        # Style configuration matching the screenshot
        chart.layout(
            background_color='#1E222D',
            text_color='#FFFFFF',
            font_size=12,
            font_family='Inter'
        )
        
        # Candlestick style
        chart.candle_style(
            up_color='#26A69A',
            down_color='#EF5350',
            wick_up_color='#26A69A',
            wick_down_color='#EF5350'
        )
        
        # Volume style
        chart.volume_config(
            up_color='rgba(38, 166, 154, 0.5)',
            down_color='rgba(239, 83, 80, 0.5)'
        )
        
        # Other configurations
        chart.crosshair(mode='normal')
        chart.time_scale(
            right_offset=15,
            min_bar_spacing=6,
            visible=True
        )
        chart.grid(
            vert_enabled=False,
            horz_enabled=True,
            horz_color='rgba(255, 255, 255, 0.07)'
        )
        
        # Price formatting
        formatted_price = f"₹{current_price:,.2f}"
        change_color = '#26A69A' if daily_change >= 0 else '#EF5350'
        change_symbol = '+' if daily_change >= 0 else ''
        formatted_change = f"{change_symbol}{daily_change:.2f}%"
        formatted_volume = format_volume(volume)
        
        # Title and legend
        chart.topbar.textbox(
            'title',
            f"{name} ({symbol}) {formatted_price} {formatted_change}"
        )
        
        chart.legend(visible=True)
        chart.price_line(label_visible=True)
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available")

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Stock Chart",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #1E222D;
    }
    .stSelectbox {
        background-color: #2A2E39;
        color: white;
    }
    .stButton > button {
        background-color: #2A2E39;
        color: white;
        border: 1px solid #363A45;
    }
    </style>
    """, unsafe_allow_html=True)

# Main interface
col1, col2, col3 = st.columns([2, 8, 2])

with col1:
    selected_table = st.selectbox(
        "Select Index",
        get_tables(),
        key="selected_table",
        label_visibility="collapsed"
    )

if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = '1Y'
    if 'selected_interval' not in st.session_state:
        st.session_state.selected_interval = 'D'

    CHARTS_PER_PAGE = 1
    total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)
    start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
    stock = stocks_df.iloc[start_idx]

    # Chart area
    with st.container():
        chart_data, current_price, daily_change, volume = load_chart_data(
            stock['symbol'],
            TIME_PERIODS[st.session_state.selected_period],
            INTERVALS[st.session_state.selected_interval]
        )
        create_chart(
            chart_data,
            stock['stock_name'],
            stock['symbol'],
            current_price,
            daily_change,
            volume
        )

    # Bottom navigation
    cols = st.columns([1, 1, 1, 4, 1, 1, 1])
    
    with cols[0]:
        if st.button("← Previous", disabled=(st.session_state.current_page == 1)):
            st.session_state.current_page -= 1
            st.rerun()
    
    with cols[1]:
        st.write(f"{st.session_state.current_page} / {total_pages}")
    
    with cols[2]:
        if st.button("Next →", disabled=(st.session_state.current_page == total_pages)):
            st.session_state.current_page += 1
            st.rerun()
    
    with cols[4]:
        new_interval = st.selectbox(
            "Interval",
            list(INTERVALS.keys()),
            index=list(INTERVALS.keys()).index(st.session_state.selected_interval),
            key="interval_selector",
            label_visibility="collapsed"
        )
        if new_interval != st.session_state.selected_interval:
            st.session_state.selected_interval = new_interval
            st.rerun()
    
    with cols[5]:
        new_period = st.selectbox(
            "Period",
            list(TIME_PERIODS.keys()),
            index=list(TIME_PERIODS.keys()).index(st.session_state.selected_period),
            key="period_selector",
            label_visibility="collapsed"
        )
        if new_period != st.session_state.selected_period:
            st.session_state.selected_period = new_period
            st.rerun()
