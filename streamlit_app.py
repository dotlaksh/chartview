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
    '3M' :'3mo',
    '1Y': '1y',
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

def search_stocks(search_term, stocks_df):
    """Search for stocks by symbol or name"""
    if not search_term:
        return stocks_df
    
    search_term = search_term.lower()
    return stocks_df[
        (stocks_df['symbol'].str.lower().str.contains(search_term)) |
        (stocks_df['stock_name'].str.lower().str.contains(search_term))
    ]

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='3mo', interval='1d', retries=3, delay=1):
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
        chart = StreamlitChart(height=500)
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '+' if daily_change >= 0 else '-'
        
        # Chart configuration
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
        
        formatted_volume = format_volume(volume)
        
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)

        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.legend(visible=True, font_size=12)
        chart.price_line(label_visible=True, line_visible=True)
        chart.fit()
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

st.set_page_config(layout="centered", page_title="ChartView 2.0", page_icon="📈")



# Initialize session state
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '3M'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'Daily'
if 'search_term' not in st.session_state:
    st.session_state.search_term = ''



# Sidebar
with st.sidebar:
    # Header with title
    st.markdown("""
        <h3>📊ChartView 1.0</h3>
    """, unsafe_allow_html=True)
    # Index selector
    tables = get_tables()
    selected_table = st.selectbox(
        "Index:",
        tables,
        key="selected_table"
    )
    
    # Time period selector
    new_period = st.selectbox(
        "Time Period",
        list(TIME_PERIODS.keys()),
        index=list(TIME_PERIODS.keys()).index(st.session_state.selected_period),
        key="period_selector"
    )
    if new_period != st.session_state.selected_period:
        st.session_state.selected_period = new_period
        st.rerun()

    # Interval selector
    new_interval = st.selectbox(
        "Interval",
        list(INTERVALS.keys()),
        index=list(INTERVALS.keys()).index(st.session_state.selected_interval),
        key="interval_selector"
    )
    if new_interval != st.session_state.selected_interval:
        st.session_state.selected_interval = new_interval
        st.rerun()
    
    st.markdown("### Search")
    search_term = st.text_input(
        "Search stocks by name or symbol:",
        value=st.session_state.search_term,
        key="stock_search"
    )
    if search_term != st.session_state.search_term:
        st.session_state.search_term = search_term

# Update session state for table selection
if 'last_selected_table' not in st.session_state or st.session_state.last_selected_table != st.session_state.selected_table:
    st.session_state.current_page = 1
    st.session_state.last_selected_table = st.session_state.selected_table

# Main chart section
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    # Filter stocks based on search term
    filtered_stocks = search_stocks(st.session_state.search_term, stocks_df)
    
    if filtered_stocks.empty:
        st.warning("No stocks found matching your search criteria.")
    else:
        CHARTS_PER_PAGE = 1
        total_pages = math.ceil(len(filtered_stocks) / CHARTS_PER_PAGE)

        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        # Ensure current page is valid after filtering
        st.session_state.current_page = min(st.session_state.current_page, total_pages)
        
        start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
        stock = filtered_stocks.iloc[start_idx]

        with st.spinner(f"Loading {stock['stock_name']}..."):
            chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(
                stock['symbol'],
                TIME_PERIODS[st.session_state.selected_period],
                INTERVALS[st.session_state.selected_interval]
            )
            # Determine change symbol and color based on daily change
            change_symbol = '+' if daily_change >= 0 else '-'
            change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
            
            # Display stock name and today's change
            row(
                f"### {stock['stock_name']} ({stock['symbol']})",
                f"**Current Price:** ${current_price:.2f}",
                f"**Change:** <span style='color:{change_color}'>{change_symbol}{abs(daily_change):.2f}%</span>"
            )

            # Create chart
            create_chart(chart_data, stock['stock_name'], stock['symbol'], 
                        current_price, volume, daily_change, pivot_points)

        # Navigation controls
        cols = st.columns([0.5, 0.5,0.5, 2])
        
        with cols[0]:
            st.button(
                "← Previous", 
                disabled=(st.session_state.current_page == 1), 
                on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page - 1),
                key="prev_button",
                use_container_width=True
            )
        
        with cols[2]:
            st.markdown(f"""
                <div class="page-info">
                    Stock {st.session_state.current_page} of {total_pages}
                </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.button(
                "Next →", 
                disabled=(st.session_state.current_page == total_pages), 
                on_click=lambda: setattr(st.session_state, 'current_page', st.session_state.current_page + 1),
                key="next_button",
                use_container_width=True
            )
