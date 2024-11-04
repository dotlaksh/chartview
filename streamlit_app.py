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
from streamlit_extras.row import row

# Time period and interval mappings
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
    'Daily': '1d',
    'Weekly': '1wk',
    'Monthly': '1mo'
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

def calculate_pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    return {'P': round(pivot, 2)}

def format_volume(volume):
    if volume >= 1_000_000:
        return f'{volume/1_000_000:.1f}M'
    elif volume >= 1_000:
        return f'{volume/1_000:.0f}K'
    else:
        return str(volume)

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='1y', interval='1d', retries=3, delay=1):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                raise ValueError("No data received from Yahoo Finance")
            
            return df
            
        except (RequestException, ValueError, Exception) as e:
            if attempt == retries - 1:
                st.error(f"Failed to fetch data for {ticker} after {retries} attempts. Error: {str(e)}")
                return None
            time.sleep(delay)
            delay *= 2

def load_chart_data(symbol, period, interval):
    ticker = f"{symbol}.NS"
    try:
        df = fetch_stock_data(ticker, period=period, interval=interval)
        
        if df is None:
            return None, None, None, None, None
            
        df = df.reset_index()

        if not df.empty:
            prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev_month_data = df[df['Date'].dt.strftime('%Y-%m') == prev_month]

            if not prev_month_data.empty:
                high, low, close = prev_month_data['High'].max(), prev_month_data['Low'].min(), prev_month_data['Close'].iloc[-1]
                pivot_points = calculate_pivot_points(high, low, close)
            else:
                pivot_points = None

            chart_data = pd.DataFrame({
                "time": df["Date"].dt.strftime("%Y-%m-%d"),
                "open": df["Open"], 
                "high": df["High"],
                "low": df["Low"], 
                "close": df["Close"],
                "volume": df["Volume"]
            })

            try:
                today = pd.Timestamp.now().strftime('%Y-%m-%d')
                today_data = df[df['Date'].dt.strftime('%Y-%m-%d') == today]
                
                if today_data.empty:
                    current_price = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
                else:
                    today_idx = df[df['Date'].dt.strftime('%Y-%m-%d') == today].index[0]
                    current_price = df['Close'].iloc[today_idx]
                    prev_close = df['Close'].iloc[today_idx - 1] if today_idx > 0 else current_price

                daily_change = ((current_price - prev_close) / prev_close) * 100
                volume = df['Volume'].iloc[-1]

            except (IndexError, ZeroDivisionError) as e:
                st.warning(f"Unable to calculate metrics for {symbol}. Error: {str(e)}")
                current_price = df['Close'].iloc[-1] if not df['Close'].empty else 0
                daily_change = 0
                volume = 0

            return chart_data, current_price, volume, daily_change, pivot_points
            
    except Exception as e:
        st.error(f"""
            Error loading data for {symbol}. This could be due to:
            - Temporary connection issues with Yahoo Finance
            - Rate limiting
            - Invalid symbol
            
            Please try again in a few moments. Error: {str(e)}
        """)
    return None, None, None, None, None

def create_chart(chart_data, name, symbol, current_price, volume, daily_change, pivot_points):
    if chart_data is not None:
        chart = StreamlitChart(height=500)  # Reduced height
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '+' if daily_change >= 0 else '-'
        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        formatted_volume = format_volume(volume)
        
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)

        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.grid(vert_enabled=False, horz_enabled=False)  
        chart.legend(visible=True, font_size=12)
        chart.topbar.textbox(
            'info',
            f'{name} |{change_symbol}{abs(daily_change):.2f}%'
        )
        chart.price_line(label_visible=True, line_visible=True)
        chart.fit()
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

st.set_page_config(layout="wide", page_title="ChartView 2.0", page_icon="📈")

st.markdown("""
    <style>
        /* Global theme */
        .stApp {
            background-color: #1a202c;
        }
        
        /* Container modifications */
        .block-container {
            padding-top: 1rem !important;
            max-width: 95% !important;
        }
        
        /* Header styling */
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        /* Selectbox styling */
        .stSelectbox > div > div {
            background-color: transparent;
            border: 1px solid #4a5568;
            color: white !important;
        }
        
        /* Search box styling */
        .stTextInput > div > div > input {
            background-color: transparent;
            border: 1px solid #4a5568;
            color: white;
            padding-left: 2.5rem;
        }
        
        /* Time period buttons */
        .stButton > button {
            background-color: transparent;
            color: #a0aec0;
            border: none;
            padding: 0.5rem 1rem;
            min-width: 3rem;
        }
        
        .stButton > button:hover {
            color: white;
            background-color: #2d3748;
        }
        
        .selected-button {
            background-color: #3182ce !important;
            color: white !important;
        }
        
        /* Stock info styling */
        .stock-info {
            margin: 1rem 0;
            padding: 0.5rem 0;
        }
        
        .stock-name {
            font-size: 1.5rem;
            font-weight: bold;
            color: white;
        }
        
        .stock-price {
            font-size: 1.2rem;
            color: white;
            margin-left: 1rem;
        }
        
        .stock-change-positive {
            color: #34d399;
        }
        
        .stock-change-negative {
            color: #ef4444;
        }
        
        /* Navigation styling */
        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
        }
        
        .nav-button {
            background-color: #2d3748;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
        }
        
        .page-info {
            background-color: #2d3748;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
        }
        
        /* Hide Streamlit defaults */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Header section
col1, col2 = st.columns([2, 2])
with col1:
    tables = get_tables()
    selected_table = st.selectbox(
        "",
        tables,
        key="selected_table"
    )

with col2:
    search = st.text_input("", placeholder="🔍 Search stocks...", key="search")

# Stock info section
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    stock = stocks_df.iloc[(st.session_state.current_page - 1) * CHARTS_PER_PAGE]
    
    chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(
        stock['symbol'],
        TIME_PERIODS[st.session_state.selected_period],
        INTERVALS[st.session_state.selected_interval]
    )
    
    # Stock info display
    st.markdown(f"""
        <div class="stock-info">
            <span class="stock-name">{stock['symbol']}</span>
            <span class="stock-price">₹{current_price:.2f}</span>
            <span class="{'stock-change-positive' if daily_change >= 0 else 'stock-change-negative'}">
                {'+' if daily_change >= 0 else ''}{daily_change:.2f}%
            </span>
            <div style="color: #718096; font-size: 0.875rem; margin-top: 0.25rem">
                {stock['stock_name']}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Time period and interval selectors
    col1, col2 = st.columns([3, 1])
    
    with col1:
        period_cols = st.columns(len(TIME_PERIODS))
        for i, (period, _) in enumerate(TIME_PERIODS.items()):
            is_selected = st.session_state.selected_period == period
            if period_cols[i].button(
                period,
                key=f"period_{period}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_period = period
                st.rerun()
    
    with col2:
        interval_cols = st.columns(len(INTERVALS))
        for i, (interval, _) in enumerate(INTERVALS.items()):
            is_selected = st.session_state.selected_interval == interval
            if interval_cols[i].button(
                interval[0],  # Just first letter (D/W/M)
                key=f"interval_{interval}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_interval = interval
                st.rerun()
    
    # Chart
    if chart_data is not None:
        chart = StreamlitChart(height=600)
        chart.layout(
            background_color='#1a202c',
            text_color='#FFFFFF',
            font_size=12,
            font_family='Helvetica'
        )
        chart.candle_style(
            up_color='#34d399',  # Green
            down_color='#ef4444',  # Red
            wick_up_color='#34d399',
            wick_down_color='#ef4444'
        )
        
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)
            
        chart.volume_config(
            up_color='#34d399',
            down_color='#ef4444'
        )
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.legend(visible=True, font_size=12)
        chart.price_line(label_visible=True, line_visible=True)
        chart.set(chart_data)
        chart.load()
    
    # Navigation
    st.markdown("""
        <div class="nav-container">
            <button class="nav-button">← Previous</button>
            <div class="page-info">1 / 50</div>
            <button class="nav-button">Next →</button>
        </div>
    """, unsafe_allow_html=True)
