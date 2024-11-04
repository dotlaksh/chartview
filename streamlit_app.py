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
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.grid_options_builder import GridOptionsBuilder
from streamlit_extras.row import row


# Time period and interval mappings
TIME_PERIODS = {
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

# Updated CSS for better mobile responsiveness
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .stSelectbox {
            margin-bottom: 0.5rem;
        }
        .chart-container {
            margin: 1rem 0;
        }
        .controls-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            align-items: center;
            margin-bottom: 1rem;
        }
        .control-item {
            flex: 1;
            min-width: 120px;
        }
        @media (max-width: 768px) {
            .controls-container {
                flex-direction: row;
            }
            .control-item {
                min-width: 100px;
            }
        }
        .nav-container {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 1rem 0;
            gap: 1rem;
        }
        .page-info {
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            background-color: #2d3748;
            color: white;
            text-align: center;
            min-width: 100px;
        }
        .ag-theme-streamlit {
            --ag-header-background-color: #1E222D;
            --ag-header-foreground-color: white;
            --ag-background-color: #2d3748;
            --ag-foreground-color: white;
            --ag-row-hover-color: #4a5568;
            --ag-selected-row-background-color: #4a5568;
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 1rem;'>📊 ChartView 2.0</h1>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = '1Y'
if 'selected_interval' not in st.session_state:
    st.session_state.selected_interval = 'Daily'

# Create a container for controls
with st.container():
    # Use columns for responsive layout
    cols = st.columns([1, 1, 1])
    
    with cols[0]:
        tables = get_tables()
        selected_table = st.selectbox(
            "Index:",
            tables,
            key="selected_table"
        )

    with cols[1]:
        new_period = st.selectbox(
            "Time Period",
            list(TIME_PERIODS.keys()),
            index=list(TIME_PERIODS.keys()).index(st.session_state.selected_period),
            key="period_selector"
        )

    with cols[2]:
        new_interval = st.selectbox(
            "Interval",
            list(INTERVALS.keys()),
            index=list(INTERVALS.keys()).index(st.session_state.selected_interval),
            key="interval_selector"
        )

# Update session states
if new_period != st.session_state.selected_period:
    st.session_state.selected_period = new_period
    st.rerun()

if new_interval != st.session_state.selected_interval:
    st.session_state.selected_interval = new_interval
    st.rerun()

# Main content
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(stocks_df)
    gb.configure_selection(selection_mode='single', use_checkbox=False)
    gb.configure_grid_options(domLayout='normal')
    gb.configure_column("symbol", headerName="Symbol", width=100)
    gb.configure_column("stock_name", headerName="Stock Name", width=200)
    
    grid_response = AgGrid(
        stocks_df,
        gridOptions=gb.build(),
        update_mode='selection_changed',
        height=200,
        theme='streamlit',
        allow_unsafe_jscode=True
    )

    selected_rows = grid_response['selected_rows']
    
    if selected_rows:
        selected_stock = selected_rows[0]
        
        with st.spinner(f"Loading {selected_stock['stock_name']}..."):
            chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(
                selected_stock['symbol'],
                TIME_PERIODS[st.session_state.selected_period],
                INTERVALS[st.session_state.selected_interval]
            )
            
            if chart_data is not None:
                create_chart(
                    chart_data,
                    selected_stock['stock_name'],
                    selected_stock['symbol'],
                    current_price,
                    volume,
                    daily_change,
                    pivot_points
                )
            else:
                st.warning("No data available for the selected stock.")
    else:
        st.info("Please select a stock from the grid above.")
