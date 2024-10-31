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

# Time period mappings (matching chartz)
TIME_PERIODS = {
    '1M': '1mo',
    '3M': '3mo',
    '6M': '6mo',
    'YTD': 'ytd',
    '1Y': '1y',
    '2Y': '2y',
    '5Y': '5y',
    'MAX': 'max'
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
        
        # Style configuration matching chartz
        chart.layout(
            background_color='#1E222D',
            text_color='#D1D4DC',
            font_size=12,
            font_family='Inter'
        )
        
        # Candlestick style matching chartz
        chart.candle_style(
            up_color='#089981',
            down_color='#F23645',
            wick_up_color='#089981',
            wick_down_color='#F23645'
        )
        
        # Volume style
        chart.volume_config(
            up_color='rgba(8, 153, 129, 0.5)',
            down_color='rgba(242, 54, 69, 0.5)'
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
            horz_enabled=True
        )
        
        # Format price and change
        formatted_price = f"₹{current_price:,.2f}"
        change_symbol = '+' if daily_change >= 0 else ''
        formatted_change = f"{change_symbol}{daily_change:.2f}%"
        formatted_volume = format_volume(volume)
        
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

# Custom CSS to match chartz styling
st.markdown("""
    <style>
    .stApp {
        background-color: #1E222D;
    }
    
    /* Header styling */
    div[data-testid="stToolbar"] {
        display: none;
    }
    
    .header-container {
        background-color: #2A2E39;
        padding: 10px 20px;
        margin: -1rem -1rem 1rem -1rem;
        border-bottom: 1px solid #363A45;
    }
    
    .stock-info {
        color: #D1D4DC;
        font-size: 16px;
        font-weight: 500;
    }
    
    /* Control elements styling */
    .stSelectbox > div > div {
        background-color: #2A2E39;
        border: 1px solid #363A45;
        color: #D1D4DC;
    }
    
    div[data-baseweb="select"] > div {
        background-color: #2A2E39 !important;
        border-color: #363A45 !important;
        color: #D1D4DC !important;
    }
    
    .stButton > button {
        background-color: #2A2E39;
        color: #D1D4DC;
        border: 1px solid #363A45;
        border-radius: 4px;
        padding: 4px 12px;
    }
    
    .stButton > button:hover {
        background-color: #363A45;
        border-color: #4A4E58;
    }
    
    /* Period/interval buttons */
    .time-controls {
        display: flex;
        gap: 8px;
    }
    
    .time-controls button {
        background-color: #2A2E39;
        color: #D1D4DC;
        border: 1px solid #363A45;
        padding: 4px 12px;
        border-radius: 4px;
        cursor: pointer;
    }
    
    .time-controls button.active {
        background-color: #363A45;
        border-color: #4A4E58;
    }
    
    /* Navigation styling */
    .navigation {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-top: 16px;
        padding: 8px;
        background-color: #2A2E39;
        border-radius: 4px;
    }
    
    /* Price display */
    .price-display {
        color: #D1D4DC;
        font-size: 18px;
        font-weight: bold;
    }
    
    .price-change {
        font-size: 14px;
        margin-left: 8px;
    }
    
    .price-change.positive {
        color: #089981;
    }
    
    .price-change.negative {
        color: #F23645;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="header-container">
        <div class="stock-info">
            <select id="index-selector" style="background-color: #2A2E39; color: #D1D4DC; border: 1px solid #363A45; padding: 4px 8px; border-radius: 4px;">
                <option value="NIFTY50">NIFTY 50</option>
            </select>
        </div>
    </div>
""", unsafe_allow_html=True)

# Main content area
selected_table = st.selectbox("Select Index", get_tables(), label_visibility="collapsed")

if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = 'YTD'
    if 'selected_interval' not in st.session_state:
        st.session_state.selected_interval = 'D'

    CHARTS_PER_PAGE = 1
    total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)
    start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
    stock = stocks_df.iloc[start_idx]

    # Chart container
    chart_container = st.container()
    with chart_container:
        chart_data, current_price, daily_change, volume = load_chart_data(
            stock['symbol'],
            TIME_PERIODS[st.session_state.selected_period],
            INTERVALS[st.session_state.selected_interval]
        )
        
        # Price and change display
        col1, col2 = st.columns([6, 4])
        with col1:
            change_class = "positive" if daily_change >= 0 else "negative"
            st.markdown(f"""
                <div class="price-display">
                    ₹{current_price:,.2f}
                    <span class="price-change {change_class}">
                        {'+' if daily_change >= 0 else ''}{daily_change:.2f}%
                    </span>
                </div>
            """, unsafe_allow_html=True)
        
        create_chart(
            chart_data,
            stock['stock_name'],
            stock['symbol'],
            current_price,
            daily_change,
            volume
        )

    # Time period and interval controls
    col1, col2, col3 = st.columns([6, 2, 2])
    
    with col1:
        st.markdown('<div class="time-controls">', unsafe_allow_html=True)
        for period in TIME_PERIODS.keys():
            active_class = "active" if period == st.session_state.selected_period else ""
            if st.button(period, key=f"period_{period}", help=f"Show {period} data"):
                st.session_state.selected_period = period
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Navigation
    nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
    with nav_col1:
        if st.button("← Previous", disabled=(st.session_state.current_page == 1)):
            st.session_state.current_page -= 1
            st.rerun()
    
    with nav_col2:
        st.markdown(f"""
            <div style="text-align: center; color: #D1D4DC;">
                {st.session_state.current_page} / {total_pages}
            </div>
        """, unsafe_allow_html=True)
    
    with nav_col3:
        if st.button("Next →", disabled=(st.session_state.current_page == total_pages)):
            st.session_state.current_page += 1
            st.rerun()
