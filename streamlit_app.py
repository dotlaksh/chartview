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

# --- Custom CSS for Modern Mobile-First Design ---
st.markdown("""
    <style>
    /* General layout */
    .stApp { 
        background-color: #181818; 
        color: #e0e0e0; 
        max-width: 600px;  /* Constrain width for mobile feel */
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
TIME_PERIODS = {'6M': '6mo', '1Y': '1y', '5Y': '5y', 'MAX': 'max'}
INTERVALS = {'Daily': '1d', 'Weekly': '1wk', 'Monthly': '1mo'}

# --- Initialize Session State ---
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '6M'
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

def load_chart_data(symbol, period, interval):
    ticker = f"{symbol}.NS"
    try:
        df = fetch_stock_data(ticker, period=period, interval=interval)
        
        if df is None or df.empty:
            return None, None, None, None, None
            
        df = df.reset_index()
        
        # Ensure 'Date' column is datetime
        df['Date'] = pd.to_datetime(df['Date'])

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

# --- Create Chart ---
def create_chart(chart_data, stock_name, price, volume):
    if chart_data is not None:
        chart = StreamlitChart(height=350)  # Reduced height for mobile
        chart.layout(background_color='#1E222D', text_color='#e0e0e0', font_size=10, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.legend(visible=True, font_size=10)
        
        # Custom info bar
        st.markdown(f"<div class='top-bar'>{stock_name} | Price: ${price} | Volume: {volume}</div>", unsafe_allow_html=True)
        
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
            st.experimental_rerun()
    
    with col2:
        if st.button("Next", use_container_width=True, key="next_btn"):
            st.session_state.current_stock_index = (st.session_state.current_stock_index + 1) % total_stocks
            st.experimental_rerun()
