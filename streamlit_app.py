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
    layout="wide",  # Use wide layout for better mobile responsiveness
    initial_sidebar_state="collapsed"
)
# CSS to hide unwanted elements and adjust padding
hide_streamlit_style = """
    <style>
    /* Hide Streamlit header, GitHub and Fork buttons */
    #MainMenu {visibility: hidden;}
    /* Hide Streamlit footer */
    footer {visibility: hidden;}
    /* Remove extra padding at the top */
    .block-container {padding-top: 0rem;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# --- Custom CSS for Modern Mobile-First Design ---
st.markdown("""
    <style>
    /* General layout */
    .stApp { 
        background-color: #181818; 
        color: #e0e0e0; 
        max-width: 800px;  /* Constrain width for mobile feel */
        margin: 0 auto;
    }
    
    /* Compact header and spacing */
    .css-1kyxreq { padding-top: 0.25rem; }
    .stMarkdown { margin-bottom: 0.5rem; }
    
    /* Button styling - smaller and more compact */
    .stButton>button { 
        background-color: #292929; 
        color: #00ff55; 
        padding: 0.3rem 0.5rem;  /* Smaller padding */
        font-size: 0.8rem;  /* Smaller font */
        height: 2rem;  /* Fixed height for uniformity */
        width: 100%;  /* Full width in column */
    }
    .stButton>button:hover {
        background-color: #333;
        color: #00ff55;
    }
    
    /* Chart Top Bar Styling */
    .top-bar { 
        text-align: center; 
        color: #00ff55; 
        font-size: 0.9rem; 
        font-weight: 600; 
        margin-bottom: 0.5rem;
    }
    
    /* Compact form elements */
    .stSelectbox, .stNumberInput { 
        margin-bottom: 0.5rem; 
    }
    
    /* Navigation buttons */
    .nav-buttons { 
        display: flex; 
        justify-content: space-between; 
        margin-top: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Time Periods and Intervals ---
TIME_PERIODS = {'1Y': '1y', '5Y': '5y', 'MAX': 'max'}
INTERVALS = {'Daily': '1d', 'Weekly': '1wk', 'Monthly': '1mo'}

# --- Initialize Session State ---
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '1Y'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'Daily'
if 'current_stock_index' not in st.session_state:
    st.session_state.current_stock_index = 0

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
        chart = StreamlitChart(height=350)  # Reduced height for mobile
        chart.layout(background_color='#1E222D', text_color='#e0e0e0', font_size=10, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.legend(visible=True, font_size=10)
        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.grid(vert_enabled=False, horz_enabled=False)  
        chart.price_line(label_visible=True,line_visible=True)
        chart.fit()
        # Custom info bar
        st.markdown(f"<div class='top-bar'>{stock_name} </div>", unsafe_allow_html=True)
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# --- Main App ---
st.title("📊 ChartView Mobile")

# --- Table and Stock Selection ---
tables = get_tables()
selected_table = st.selectbox("Select a Table:", tables)

if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    # Pagination Logic
    total_stocks = len(stocks_df)
    st.session_state.current_stock_index = max(0, min(st.session_state.current_stock_index, total_stocks - 1))
    
    # Current Stock
    current_stock = stocks_df.iloc[st.session_state.current_stock_index]

    # --- Time Period and Interval Buttons ---
    st.markdown("<h4 style='text-align: center;'>Select Period & Interval</h4>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Period**")
        for period in TIME_PERIODS:
            if st.button(period, key=f"period_{period}", use_container_width=True):
                st.session_state.selected_period = period
    
    with col2:
        st.markdown("**Interval**")
        for interval in INTERVALS:
            if st.button(interval, key=f"interval_{interval}", use_container_width=True):
                st.session_state.selected_interval = interval
    
    # --- Load and Render Chart ---
    with st.spinner(f"Loading {current_stock['stock_name']}..."):
        chart_data, current_price, volume = load_chart_data(
            current_stock['symbol'],
            TIME_PERIODS[st.session_state.selected_period],
            INTERVALS[st.session_state.selected_interval]
        )
        create_chart(chart_data, current_stock['stock_name'], current_price, volume)

    # --- Navigation ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous", use_container_width=True, key="prev_btn"):
            st.session_state.current_stock_index = (st.session_state.current_stock_index - 1) % total_stocks
            st.rerun()
    
    with col2:
        if st.button("Next", use_container_width=True, key="next_btn"):
            st.session_state.current_stock_index = (st.session_state.current_stock_index + 1) % total_stocks
            st.rerun()
