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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_data(ticker, retries=3, delay=1):
    """
    Fetch stock data with retry mechanism and proper error handling
    """
    for attempt in range(retries):
        try:
            # Create a yfinance Ticker object
            stock = yf.Ticker(ticker)
            
            # Get historical data
            df = stock.history(period='ytd', interval='1w')
            
            if df.empty:
                raise ValueError("No data received from Yahoo Finance")
            
            return df
            
        except (RequestException, ValueError, Exception) as e:
            if attempt == retries - 1:  # Last attempt
                st.error(f"Failed to fetch data for {ticker} after {retries} attempts. Error: {str(e)}")
                return None
            time.sleep(delay)  # Wait before retrying
            delay *= 2  # Exponential backoff

def load_chart_data(symbol):
    ticker = f"{symbol}.NS"
    try:
        # Use the new fetch function with retry mechanism
        df = fetch_stock_data(ticker)
        
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

            # Add additional error checking for financial calculations
            try:
                current_price = df['Close'].iloc[-1]
                if len(df) > 1:
                    daily_change = ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                else:
                    daily_change = 0
                volume = df['Volume'].iloc[-1]
            except (IndexError, ZeroDivisionError):
                st.warning(f"Unable to calculate some metrics for {symbol}")
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
        chart = StreamlitChart(height=480)  # Fixed height in pixels
        
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'

        st.markdown(f"""
        <style>
            .stock-info {{
                padding: 10px;
                margin-bottom: 10px;
                font-size: 18px;
                white-space: nowrap;
                overflow-x: auto;
            }}
            @media (max-width: 768px) {{
                .stock-info {{
                    font-size: 14px;
                    padding: 5px;
                }}
            }}
        </style>
        <div class="stock-info">
            <span style='font-weight: bold;'>{name}</span>
            <span style='color: #00ff55;'>₹{current_price:.2f}</span> | 
            <span style='color: {change_color};'>{change_symbol} {abs(daily_change):.2f}%</span> | 
            Vol: {volume:,.0f}
        </div>
        """, unsafe_allow_html=True)

        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')

        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)


        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=10)
        chart.grid(vert_enabled=False, horz_enabled=False)  
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# Initial page config
st.set_page_config(layout="centered", page_title="ChartView 2.0", page_icon="📈")

# Global styles
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 300px;
        }
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                min-width: 180px;
            }
            .stButton button {
                padding: 0.3rem !important;
                font-size: 12px !important;
            }
            div[data-testid="column"] {
                padding: 0 0.2rem !important;
            }
        }
        .stButton button {
            width: 100%;
            padding: 0.5rem;
        }
        div[data-testid="column"] {
            padding: 0 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📊 ChartView 2.0")
    tables = get_tables()
    selected_table = st.selectbox("Select a table:", tables, key="selected_table")

    if 'last_selected_table' not in st.session_state or st.session_state.last_selected_table != st.session_state.selected_table:
        st.session_state.current_page = 1
        st.session_state.last_selected_table = st.session_state.selected_table

    search_term = st.text_input("🔍 Search for a stock:")

# Main content
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    if search_term:
        stocks_df = stocks_df[stocks_df['stock_name'].str.contains(search_term, case=False)]

    CHARTS_PER_PAGE = 1
    total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
    stock = stocks_df.iloc[start_idx]

    with st.spinner(f"Loading {stock['stock_name']}..."):
        chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(stock['symbol'])
        create_chart(chart_data, stock['stock_name'], stock['symbol'], current_price, volume, daily_change, pivot_points)

    # Pagination with improved mobile layout
    container = st.container()
    with container:
        col1, col2, col3 = st.columns([2, 3, 2])
        
        with col1:
            st.button(
                "← Previous", 
                disabled=(st.session_state.current_page == 1), 
                on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page - 1),
                key="prev_button",
                use_container_width=True
            )
        
        with col2:
            st.markdown(f"""
                <div style='text-align: center; padding: 8px 0;'>
                    Page {st.session_state.current_page} of {total_pages}
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.button(
                "Next →", 
                disabled=(st.session_state.current_page == total_pages), 
                on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page + 1),
                key="next_button",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; padding: 10px; font-size: 12px;'>
        Developed by Laksh | Data from Yahoo Finance
    </div>
""", unsafe_allow_html=True)
