import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager
import math

# Database connection management
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

@st.cache_data
def get_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [table[0] for table in cursor.fetchall()]
    return tables

@st.cache_data
def get_stocks_from_table(table_name):
    with get_db_connection() as conn:
        query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
        stocks_df = pd.read_sql_query(query, conn)
    return stocks_df

# Modified function to load chart data and calculate percentage change
@st.cache_data
def load_chart_data(symbol):
    ticker = f"{symbol}.NS"
    try:
        df = yf.download(ticker, period='6mo', interval='1d')
        df.reset_index(inplace=True)
        
        if not df.empty:
            chart_data = pd.DataFrame({
                "time": df["Date"].dt.strftime("%Y-%m-%d"),
                "open": df["Open"],
                "high": df["High"],
                "low": df["Low"],
                "close": df["Close"],
                "volume": df["Volume"]
            })
            
            # Calculate daily percentage change
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            daily_change = ((current_price - prev_price) / prev_price) * 100
            
            return chart_data, current_price, df['Volume'].iloc[-1], daily_change
        return None, None, None, None
    except Exception:
        return None, None, None, None

# Modified function to create chart with percentage change
def create_chart(chart_data, name, symbol, current_price, volume, daily_change):
    if chart_data is not None:
        CHART_WIDTH = 800
        
        # Create change color and symbol based on value
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'
        
        # Modified HTML to include percentage change
        st.markdown(f"""
        <div style='width: {CHART_WIDTH}px; padding: 10px; background-color: #1E222D; border-radius: 5px;'>
            <span style='font-size: 16px; font-weight: bold;'>{name} ({symbol})</span>
            <br/>
            <span style='color: #00ff55;'>₹{current_price:.2f}</span> | 
            <span style='color: {change_color};'>{change_symbol} {abs(daily_change):.2f}%</span> | 
            Vol: {volume:,.0f}
        </div>
        """, unsafe_allow_html=True)
        
        chart = StreamlitChart(width=CHART_WIDTH, height=600)
        chart.layout(
            background_color='#1E222D',
            text_color='#FFFFFF',
            font_size=12,
            font_family='Helvetica'
        )
        chart.candle_style(
            up_color='#00ff55',
            down_color='#ed4807',
            wick_up_color='#00ff55',
            wick_down_color='#ed4807'
        )
        chart.volume_config(
            up_color='#00ff55',
            down_color='#ed4807'
        )
        chart.crosshair(
            mode='normal',
            vert_color='#FFFFFF',
            vert_style='dotted',
            horz_color='#FFFFFF',
            horz_style='dotted'
        )
        chart.time_scale(right_offset=10, min_bar_spacing=6)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data)
        return chart
    return None

# Page setup
st.set_page_config(layout="wide")
# Table selection using selectbox
tables = get_tables()
col1, col2 = st.columns([1,2])
with col1:
    selected_table = st.selectbox("Select a table:", tables, key='table_selector')

# Initialize session state for pagination
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Reset page when table changes
if 'previous_table' not in st.session_state:
    st.session_state.previous_table = selected_table
if st.session_state.previous_table != selected_table:
    st.session_state.current_page = 1
    st.session_state.previous_table = selected_table

# Get stocks data and display charts
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)

    CHARTS_PER_PAGE = 10
    total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

    # Determine start and end indices for pagination
    start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
    end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))

    # Display charts in a loop
    for i in range(start_idx, end_idx, 2):
        col1, col2 = st.columns([1, 1])

        # First chart
        with col1:
            symbol = stocks_df['symbol'].iloc[i]
            name = stocks_df['stock_name'].iloc[i]
            chart_data, current_price, volume, daily_change = load_chart_data(symbol)
            if chart_data is not None:
                chart = create_chart(chart_data, name, symbol, current_price, volume, daily_change)
                if chart:
                    chart.load()

        # Second chart (if available)
        with col2:
            if i + 1 < end_idx:
                symbol = stocks_df['symbol'].iloc[i + 1]
                name = stocks_df['stock_name'].iloc[i + 1]
                chart_data, current_price, volume, daily_change = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, name, symbol, current_price, volume, daily_change)
                    if chart:
                        chart.load()

    # Pagination controls at the bottom
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Previous", key='prev') and st.session_state.current_page > 1:
            st.session_state.current_page -= 1

    with col2:
        st.write(f"Page {st.session_state.current_page} of {total_pages} | Total Stocks: {len(stocks_df)}")

    with col3:
        if st.button("Next →", key='next') and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1

