import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager
from datetime import datetime, timedelta
import math
import time

# Define mappings for time periods and intervals
TIME_PERIODS = {'1M': '1mo', '3M': '3mo', '6M': '6mo', 'YTD': 'ytd', '1Y': '1y', '2Y': '2y', '5Y': '5y', 'MAX': 'max'}
INTERVALS = {'Daily': '1d', 'Weekly': '1wk', 'Monthly': '1mo'}

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
def fetch_stock_data(ticker, period='ytd', interval='1d'):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    if df.empty:
        st.warning(f"No data found for ticker {ticker}.")
    return df

def create_chart(chart_data, symbol, current_price, daily_change):
    if not chart_data.empty:
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        chart = StreamlitChart(height=300 if st.session_state.is_mobile else 525)
        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available for chart rendering.")

# Initial page config
st.set_page_config(layout="centered", page_title="ChartView 2.0", page_icon="📈")
st.session_state.is_mobile = st.session_state.get("is_mobile", False) if "is_mobile" in st.session_state else st.experimental_get_query_params().get("mobile", [""])[0] == "1"

if st.session_state.is_mobile:
    st.markdown("<style>body{font-size:90%;}</style>", unsafe_allow_html=True)

# Sidebar with collapsing layout
with st.sidebar:
    st.title("📊 ChartView 2.0")
    tables = get_tables()
    selected_table = st.selectbox("Select Table:", tables, key="selected_table")

# Load stocks data
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    if stocks_df.empty:
        st.warning("No stocks available in the selected table.")
    else:
        stock = stocks_df.iloc[0]  # Select the first stock for simplicity in a mobile-first view
        
        # Fetch and validate stock data
        chart_data = fetch_stock_data(stock['symbol'], period=TIME_PERIODS['YTD'], interval=INTERVALS['Daily'])
        if not chart_data.empty:
            # Extract necessary information for display
            current_price = chart_data['Close'].iloc[-1] if not chart_data['Close'].empty else None
            daily_change = 0  # Placeholder for a daily change value; implement logic as needed
            create_chart(chart_data.reset_index(), stock['symbol'], current_price, daily_change)
        else:
            st.warning(f"No data available for {stock['symbol']}.")

# Bottom navigation bar
st.markdown("""
    <style>
    .mobile-nav { display: flex; justify-content: space-around; padding: 8px 0; border-top: 1px solid #ccc; }
    .mobile-nav .nav-item { font-size: 1.2em; text-align: center; flex: 1; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="mobile-nav">
        <div class="nav-item">📅 Period</div>
        <div class="nav-item">⏰ Interval</div>
        <div class="nav-item">⬅️ Prev</div>
        <div class="nav-item">➡️ Next</div>
    </div>
""", unsafe_allow_html=True)
