import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager

# Page config
st.set_page_config(layout="wide", page_title="Stock Chart")

# Hide Streamlit elements
st.markdown("""
    <style>
        #MainMenu, header, footer {display: none;}
        .stApp {
            background-color: #14171C;
        }
        section[data-testid="stSidebar"] {display: none;}
        button[data-testid="baseButton-secondary"] {
            background-color: #2A2E39;
            border: none;
            color: #D1D4DC;
            padding: 4px 12px;
            font-size: 13px;
        }
        div[data-testid="stVerticalBlock"] > div {
            padding-top: 0;
            padding-bottom: 0;
        }
    </style>
""", unsafe_allow_html=True)

# Database functions
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks1.db')
    try:
        yield conn
    finally:
        conn.close()

def get_stocks_from_table(table_name):
    with get_db_connection() as conn:
        query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
        return pd.read_sql_query(query, conn)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'period' not in st.session_state:
    st.session_state.period = '1y'

# Load data
@st.cache_data(ttl=300)
def load_stock_data(symbol, period='1y'):
    try:
        stock = yf.Ticker(f"{symbol}.NS")
        df = stock.history(period=period)
        if not df.empty:
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
            change = ((current_price - prev_close) / prev_close) * 100
            
            df = df.reset_index()
            chart_data = {
                "time": df["Date"].dt.strftime("%Y-%m-%d"),
                "open": df["Open"],
                "high": df["High"],
                "low": df["Low"],
                "close": df["Close"],
                "volume": df["Volume"]
            }
            return pd.DataFrame(chart_data), current_price, change
        return None, None, None
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None

# Get stock data
stocks = get_stocks_from_table("NIFTY50")
current_stock = stocks.iloc[st.session_state.page - 1]
chart_data, price, change = load_stock_data(current_stock['symbol'], st.session_state.period)

# Header with stock info
st.markdown(f"""
    <div style="background-color: #1C1F26; padding: 15px; margin: -1rem -1rem 1rem -1rem;">
        <div style="color: #D1D4DC; font-size: 20px; font-weight: 500;">
            {current_stock['stock_name']}
            <span style="margin-left: 15px;">₹{price:.2f}</span>
            <span style="margin-left: 10px; padding: 2px 8px; border-radius: 4px; 
                  background-color: {'rgba(8, 153, 129, 0.1)' if change >= 0 else 'rgba(242, 54, 69, 0.1)'};
                  color: {'#089981' if change >= 0 else '#F23645'}">
                {'+' if change >= 0 else ''}{change:.2f}%
            </span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Chart
if chart_data is not None:
    chart = StreamlitChart(height=500)
    chart.layout(background_color='#1C1F26', text_color='#D1D4DC')
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
    chart.grid(vert_enabled=False, horz_enabled=True)
    chart.set(chart_data)
    chart.load()

# Time period buttons
cols = st.columns(8)
periods = ['1Y', '5Y', 'Max']
for i, period in enumerate(periods):
    with cols[i]:import pandas as pd
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

        if st.button(period):
            st.session_state.period = period.lower()
            st.rerun()

# Navigation
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("← Previous", disabled=st.session_state.page == 1):
        st.session_state.page -= 1
        st.rerun()
with col2:
    st.markdown(f"""
        <div style="text-align: center; color: #D1D4DC;">
            {st.session_state.page} / {len(stocks)}
        </div>
    """, unsafe_allow_html=True)
with col3:
    if st.button("Next →", disabled=st.session_state.page == len(stocks)):
        st.session_state.page += 1
        st.rerun()
