import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager
import math
from datetime import datetime, timedelta
import time

# Constants
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

# Database functions remain the same
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

# Updated styling to match chartz
st.set_page_config(
    layout="wide",
    page_title="Stock Chart",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# Custom CSS matching chartz exactly
st.markdown("""
    <style>
    /* Hide default Streamlit button styling */
    .stButton > button {
        display: none;
    }
    
    /* Navigation container */
    .nav-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1C1F26;
        padding: 16px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid #2A2E39;
    }
    
    /* Custom navigation buttons */
    .nav-btn-container {
        display: flex;
        align-items: center;
        gap: 24px;
    }
    
    .custom-nav-btn {
        background-color: #2A2E39;
        color: #D1D4DC;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: background-color 0.2s;
    }
    
    .custom-nav-btn:hover {
        background-color: #363A45;
    }
    
    .custom-nav-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    
    .page-indicator {
        color: #D1D4DC;
        font-size: 14px;
        padding: 0 16px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '1Y'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'D'

# Top navigation
st.markdown("""
    <div class="top-nav">
        <select class="index-selector">
            <option value="NIFTY50">NIFTY 50</option>
        </select>
    </div>
""", unsafe_allow_html=True)

# Main content
selected_table = "NIFTY50"  # Hardcoded for demo
stocks_df = get_stocks_from_table(selected_table)

# Get current stock
start_idx = (st.session_state.current_page - 1)
stock = stocks_df.iloc[start_idx]

# Load chart data
@st.cache_data(ttl=300)
def load_chart_data(symbol, period='1y', interval='1d'):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None, None, None
        
        current_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
        daily_change = ((current_price - prev_close) / prev_close) * 100
        
        chart_data = pd.DataFrame({
            "time": df.index.strftime("%Y-%m-%d"),
            "open": df["Open"],
            "high": df["High"],
            "low": df["Low"],
            "close": df["Close"],
            "volume": df["Volume"]
        })
        
        return chart_data, current_price, daily_change
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None, None

# Load and display chart
chart_data, current_price, daily_change = load_chart_data(
    stock['symbol'],
    TIME_PERIODS[st.session_state.selected_period],
    INTERVALS[st.session_state.selected_interval]
)

# Stock info and chart
st.markdown(f"""
    <div class="stock-info">
        <div class="stock-name">{stock['stock_name']}</div>
        <div class="stock-price">₹{current_price:,.2f}</div>
        <div class="price-change {'positive' if daily_change >= 0 else 'negative'}">
            {'+' if daily_change >= 0 else ''}{daily_change:.2f}%
        </div>
    </div>
""", unsafe_allow_html=True)

# Chart
if chart_data is not None:
    chart = StreamlitChart(height=500)
    
    # Chart styling
    chart.layout(
        background_color='#1C1F26',
        text_color='#D1D4DC',
        font_size=12,
        font_family='Inter'
    )
    
    chart.candle_style(
        up_color='#089981',
        down_color='#F23645',
        wick_up_color='#089981',
        wick_down_color='#F23645'
    )
    
    chart.volume_config(
        up_color='rgba(8, 153, 129, 0.5)',
        down_color='rgba(242, 54, 69, 0.5)'
    )
    
    chart.crosshair(mode='normal')
    chart.time_scale(
        right_offset=15,
        min_bar_spacing=6,
        visible=True
    )
    
    chart.grid(
        vert_enabled=False,
        horz_enabled=True
    )
    
    chart.set(chart_data)
    chart.load()

# Time period controls
st.markdown('<div class="time-controls">', unsafe_allow_html=True)
for period in TIME_PERIODS:
    active_class = "active" if period == st.session_state.selected_period else ""
    if st.button(period, key=f"period_{period}", 
                 help=f"Show {period} data",
                 use_container_width=False):
        st.session_state.selected_period = period
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Navigation
total_pages = len(stocks_df)
# Container for navigation
st.markdown(
    f"""
    <div class="nav-container">
        <div class="nav-btn-container">
            <div class='stButton'>
                {'<button class="custom-nav-btn" disabled>← Previous</button>' 
                if st.session_state.current_page == 1 
                else '<button class="custom-nav-btn">← Previous</button>'}
            </div>
            <span class="page-indicator">{st.session_state.current_page} / {total_pages}</span>
            <div class='stButton'>
                {'<button class="custom-nav-btn" disabled>Next →</button>' 
                if st.session_state.current_page == total_pages 
                else '<button class="custom-nav-btn">Next →</button>'}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Navigation buttons functionality
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("Previous", key="prev_btn", disabled=(st.session_state.current_page == 1)):
        st.session_state.current_page -= 1
        st.rerun()

with col3:
    if st.button("Next", key="next_btn", disabled=(st.session_state.current_page == total_pages)):
        st.session_state.current_page += 1
        st.rerun()
st.markdown("<div style='height: 80px'></div>", unsafe_allow_html=True)
