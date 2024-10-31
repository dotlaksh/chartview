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
    nse_ticker = f"{ticker}.NS"  # Append `.NS` for NSE stocks
    symbol = yf.Ticker(nse_ticker)
    df = symbol.history(period=period, interval=interval)
    if df.empty:
        st.warning(f"No data found for NSE ticker {ticker}.")
    return df

def create_chart(chart_data, name, symbol, current_price, volume, daily_change, pivot_points):
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

# Sidebar for selecting the table
with st.sidebar:
    st.title("📊 ChartView 2.0")
    tables = get_tables()
    selected_table = st.selectbox("Select Table:", tables, key="selected_table")

# Initialize session state for period and interval
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = 'YTD'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'Daily'

# Main content
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    if stocks_df.empty:
        st.warning("No stocks available in the selected table.")
    else:
        # Pagination settings
        CHARTS_PER_PAGE = 1
        total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1

        # Stock pagination
        start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
        stock = stocks_df.iloc[start_idx]

        # Fetch and validate stock data
        with st.spinner(f"Loading {stock['stock_name']}..."):
            chart_data = fetch_stock_data(stock['symbol'], period=TIME_PERIODS[st.session_state.selected_period], interval=INTERVALS[st.session_state.selected_interval])
            
            if not chart_data.empty:
                # Calculate necessary values for the chart display
                current_price = chart_data['Close'].iloc[-1] if not chart_data['Close'].empty else None
                volume = chart_data['Volume'].iloc[-1] if not chart_data['Volume'].empty else None
                daily_change = ((chart_data['Close'].iloc[-1] - chart_data['Close'].iloc[-2]) / chart_data['Close'].iloc[-2]) * 100 if len(chart_data) > 1 else 0
                
                create_chart(chart_data.reset_index(), stock['stock_name'], stock['symbol'], current_price, volume, daily_change, pivot_points=None)
            else:
                st.warning(f"No data available for {stock['symbol']}.")

        # Bottom navigation bar
        bottom_navbar = st.container()
        with bottom_navbar:
            cols = st.columns([1, 1, 1, 1, 2, 2])

            # Previous button
            with cols[0]:
                st.button(
                    "← ",
                    disabled=(st.session_state.current_page == 1),
                    on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page - 1),
                    key="prev_button",
                    use_container_width=True
                )

            # Page indicator
            with cols[1]:
                st.markdown(f"""
                    <div style='text-align: center; padding: 5px 0;'>
                        Page {st.session_state.current_page} of {total_pages}
                    </div>
                """, unsafe_allow_html=True)

            # Next button
            with cols[2]:
                st.button(
                    "→",
                    disabled=(st.session_state.current_page == total_pages),
                    on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page + 1),
                    key="next_button",
                    use_container_width=True
                )

            # Spacer
            with cols[3]:
                st.empty()

            # Time period selector
            with cols[4]:
                new_period = st.selectbox(
                    "Time Period:",
                    list(TIME_PERIODS.keys()),
                    index=list(TIME_PERIODS.keys()).index(st.session_state.selected_period),
                    key="period_selector",
                    label_visibility="collapsed"
                )
                if new_period != st.session_state.selected_period:
                    st.session_state.selected_period = new_period
                    st.rerun()

            # Interval selector
            with cols[5]:
                new_interval = st.selectbox(
                    "Interval:",
                    list(INTERVALS.keys()),
                    index=list(INTERVALS.keys()).index(st.session_state.selected_interval),
                    key="interval_selector",
                    label_visibility="collapsed"
                )
                if new_interval != st.session_state.selected_interval:
                    st.session_state.selected_interval = new_interval
                    st.rerun()
