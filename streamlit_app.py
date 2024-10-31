import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
from contextlib import contextmanager
import time

# --- Page Config ---
st.set_page_config(
    page_title="ChartView Mobile",
    page_icon="📈",
    layout="centered",  # centers content on mobile screens
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Modern Look ---
st.markdown("""
    <style>
    /* General layout */
    .stApp { background-color: #181818; color: #e0e0e0; }
    .css-1kyxreq { padding-top: 0.5rem; }  /* reduces header space */
    
    /* Sidebar styling */
    .css-1d391kg { background-color: #202020; color: #e0e0e0; }  /* sidebar bg */
    
    /* Buttons */
    .stButton button { background-color: #292929; color: #00ff55; padding: 0.5rem 1rem; }
    .selected-btn { background-color: #00ff55 !important; color: #000000 !important; }
    
    /* Chart Top Bar Styling */
    .top-bar { text-align: center; color: #00ff55; font-size: 1.1rem; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- Time Periods and Intervals ---
TIME_PERIODS = {'6M': '6mo', '1Y': '1y', '5Y': '5y', 'MAX': 'max'}
INTERVALS = {'Daily': '1d', 'Weekly': '1wk', 'Monthly': '1mo'}

# --- Initialize Session State ---
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '6M'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'Daily'

# --- Database Context ---
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks1.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

# --- Helper Functions ---
def get_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [table[0] for table in cursor.fetchall()]

def get_stocks_from_table(table_name):
    with get_db_connection() as conn:
        query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
        return pd.read_sql_query(query, conn)

# --- Fetching Stock Data ---
@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='ytd', interval='1d'):
    stock = yf.Ticker(ticker)
    return stock.history(period=period, interval=interval)

# --- Load and Display Data ---
def load_chart_data(symbol, period, interval):
    df = fetch_stock_data(f"{symbol}.NS", period=period, interval=interval)
    if df is not None:
        df = df.reset_index()
        chart_data = pd.DataFrame({
            "time": df["Date"].dt.strftime("%Y-%m-%d"),
            "open": df["Open"], 
            "high": df["High"],
            "low": df["Low"], 
            "close": df["Close"],
            "volume": df["Volume"]
        })
        return chart_data, df["Close"].iloc[-1], df["Volume"].iloc[-1]
    return None, None, None

# --- Create Chart ---
def create_chart(chart_data, stock_name, price, volume):
    if chart_data is not None:
        chart = StreamlitChart(height=450)
        chart.layout(background_color='#1E222D', text_color='#e0e0e0', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.legend(visible=True, font_size=12)
        
        # Custom info bar
        st.markdown(f"<div class='top-bar'>{stock_name} | Price: ${price} | Volume: {volume}</div>", unsafe_allow_html=True)
        
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# --- Sidebar ---
with st.sidebar:
    st.title("📊 ChartView Mobile")
    tables = get_tables()
    selected_table = st.selectbox("Select a table:", tables, key="selected_table")

# --- Display Selected Stock ---
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    stock = stocks_df.iloc[0]  # Show only first stock for simplicity in mobile view

    # --- Time Period and Interval Buttons ---
    with st.container():
        st.markdown("<h3 style='text-align: center;'>Select Period & Interval</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            for period in TIME_PERIODS:
                if st.button(period, key=f"btn_{period}", use_container_width=True):
                    st.session_state.selected_period = period
        with col2:
            for interval in INTERVALS:
                if st.button(interval, key=f"btn_{interval}", use_container_width=True):
                    st.session_state.selected_interval = interval
    
    # --- Load and Render Chart ---
    with st.spinner(f"Loading {stock['stock_name']}..."):
        chart_data, current_price, volume = load_chart_data(
            stock['symbol'],
            TIME_PERIODS[st.session_state.selected_period],
            INTERVALS[st.session_state.selected_interval]
        )
        create_chart(chart_data, stock['stock_name'], current_price, volume)

# --- Navigation --- 
nav_col1, nav_col2 = st.columns([1, 1])
with nav_col1:
    st.button("Previous", use_container_width=True)
with nav_col2:
    st.button("Next", use_container_width=True)
