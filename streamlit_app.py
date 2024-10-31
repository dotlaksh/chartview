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
    initial_sidebar_state="collapsed"  # collapses sidebar on start for mobile
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
    .stButton button { background-color: #292929; color: #00ff55; padding: 0.6rem 1.5rem; }
    
    /* Chart Top Bar Styling */
    .top-bar { text-align: center; color: #00ff55; font-size: 1.1rem; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

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
    
    with st.spinner(f"Loading {stock['stock_name']}..."):
        chart_data, current_price, volume = load_chart_data(stock['symbol'], 'ytd', '1d')
        create_chart(chart_data, stock['stock_name'], current_price, volume)

# --- Navigation --- 
nav_col1, nav_col2 = st.columns([1, 1])
with nav_col1:
    st.button("Previous", use_container_width=True)
with nav_col2:
    st.button("Next", use_container_width=True)
