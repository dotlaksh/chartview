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

# Enhanced time period and interval mappings with descriptions
TIME_PERIODS = {
    '1D': {'value': '1d', 'description': 'Last 24 hours'},
    '1W': {'value': '1wk', 'description': 'Last 7 days'},
    '1M': {'value': '1mo', 'description': 'Last 30 days'},
    '1Y': {'value': '1y', 'description': 'Last 12 months'},
    '5Y': {'value': '5y', 'description': '5 years history'},
    'MAX': {'value': 'max', 'description': 'Maximum available data'}
}

INTERVALS = {
    '1min': {'value': '1m', 'description': '1 minute intervals'},
    '5min': {'value': '5m', 'description': '5 minute intervals'},
    'Daily': {'value': '1d', 'description': 'Daily intervals'},
    'Weekly': {'value': '1wk', 'description': 'Weekly intervals'},
    'Monthly': {'value': '1mo', 'description': 'Monthly intervals'}
}

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks1.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

# Enhanced error handling for database operations
def get_tables():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            return [table[0] for table in cursor.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return []

def get_stocks_from_table(table_name):
    try:
        with get_db_connection() as conn:
            query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
            return pd.read_sql_query(query, conn)
    except sqlite3.Error as e:
        st.error(f"Error fetching stocks: {str(e)}")
        return pd.DataFrame(columns=['symbol', 'stock_name'])

def calculate_pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    return {
        'P': round(pivot, 2),
        'R1': round(r1, 2),
        'S1': round(s1, 2)
    }

def format_volume(volume):
    if volume >= 1_000_000_000:
        return f'{volume/1_000_000_000:.1f}B'
    elif volume >= 1_000_000:
        return f'{volume/1_000_000:.1f}M'
    elif volume >= 1_000:
        return f'{volume/1_000:.1f}K'
    return str(volume)

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='1y', interval='1d', retries=3, delay=1):
    for attempt in range(retries):
        try:
            with st.spinner(f"Fetching data for {ticker}... Attempt {attempt + 1}/{retries}"):
                stock = yf.Ticker(ticker)
                df = stock.history(period=period, interval=interval)
                
                if df.empty:
                    raise ValueError("No data received from Yahoo Finance")
                
                return df
                
        except (RequestException, ValueError) as e:
            if attempt == retries - 1:
                st.error(f"Failed to fetch data after {retries} attempts. Please try again later.")
                return None
            time.sleep(delay)
            delay *= 2

def create_modern_chart(chart_data, stock_info, metrics):
    chart = StreamlitChart(height=500)
    
    # Modern color scheme
    COLORS = {
        'up': '#00c853',
        'down': '#ff3d00',
        'neutral': '#90a4ae',
        'grid': '#37474f',
        'text': '#eceff1',
        'background': '#263238'
    }
    
    change_color = COLORS['up'] if metrics['daily_change'] >= 0 else COLORS['down']
    change_symbol = '+' if metrics['daily_change'] >= 0 else ''
    
    # Enhanced chart configuration
    chart.layout(
        background_color=COLORS['background'],
        text_color=COLORS['text'],
        font_size=14,
        font_family='Inter'
    )
    
    chart.candle_style(
        up_color=COLORS['up'],
        down_color=COLORS['down'],
        wick_up_color=COLORS['up'],
        wick_down_color=COLORS['down']
    )
    
    # Add technical indicators
    if metrics['pivot_points']:
        for level, value in metrics['pivot_points'].items():
            chart.horizontal_line(
                value,
                color=COLORS['neutral'],
                line_style='dashed',
                line_width=1,
                label=f'{level}: {value}'
            )
    
    chart.volume_config(
        up_color=COLORS['up'],
        down_color=COLORS['down']
    )
    
    # Enhanced crosshair and navigation
    chart.crosshair(
        mode='magnet',
        line_color=COLORS['neutral']
    )
    
    chart.time_scale(
        right_offset=10,
        min_bar_spacing=6,
        visible=True
    )
    
    chart.grid(
        vert_enabled=True,
        horz_enabled=True,
        vert_color=COLORS['grid'],
        horz_color=COLORS['grid']
    )
    
    # Improved legend
    chart.legend(
        visible=True,
        font_size=12,
        text_color=COLORS['text']
    )
    
    # Enhanced top bar with more information
    formatted_price = f"₹{metrics['current_price']:,.2f}"
    formatted_volume = format_volume(metrics['volume'])
    chart.topbar.textbox(
        'info',
        f"{stock_info['stock_name']} ({stock_info['symbol']}) | {change_symbol}{metrics['daily_change']:.2f}% | {formatted_price} | Vol: {formatted_volume}"
    )
    
    chart.price_line(
        label_visible=True,
        line_visible=True,
        color=change_color
    )
    
    chart.fit()
    chart.set(chart_data)
    return chart

def main():
    st.set_page_config(
        layout="wide",
        page_title="📈 ChartView Pro",
        page_icon="📈",
        initial_sidebar_state="collapsed"
    )

    # Modern UI styling
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
            
            :root {
                --primary-color: #2196f3;
                --background-color: #1a1a1a;
                --text-color: #ffffff;
            }
            
            .stApp {
                font-family: 'Inter', sans-serif;
                background-color: var(--background-color);
                color: var(--text-color);
            }
            
            .stSelectbox > div > div {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                color: var(--text-color);
            }
            
            .stButton > button {
                border-radius: 8px;
                padding: 0.5rem 1rem;
                background-color: var(--primary-color);
                color: white;
                border: none;
                transition: all 0.3s ease;
            }
            
            .stButton > button:hover {
                background-color: #1976d2;
                transform: translateY(-1px);
            }
            
            .chart-container {
                background-color: #1e1e1e;
                border-radius: 12px;
                padding: 1rem;
                margin: 1rem 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .metrics-container {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
            }
            
            .stock-search {
                margin: 1rem 0;
            }
            
            /* Mobile optimizations */
            @media (max-width: 768px) {
                .block-container {
                    padding: 0.5rem !important;
                }
                
                .stButton > button {
                    width: 100%;
                }
                
                .chart-container {
                    padding: 0.5rem;
                }
            }
        </style>
    """, unsafe_allow_html=True)

    # App header with modern design
    st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h1 style='font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem;'>📈 ChartView Pro</h1>
            <p style='font-size: 1rem; color: #90a4ae;'>Professional Stock Analysis Tool</p>
        </div>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = '1Y'
    if 'selected_interval' not in st.session_state:
        st.session_state.selected_interval = 'Daily'
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Modern control panel
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            tables = get_tables()
            selected_table = st.selectbox(
                "Select Market Index",
                tables,
                help="Choose the market index to analyze"
            )

        with col2:
            period = st.selectbox(
                "Time Period",
                list(TIME_PERIODS.keys()),
                format_func=lambda x: f"{x} ({TIME_PERIODS[x]['description']})",
                index=list(TIME_PERIODS.keys()).index(st.session_state.selected_period)
            )

        with col3:
            interval = st.selectbox(
                "Interval",
                list(INTERVALS.keys()),
                format_func=lambda x: f"{x} ({INTERVALS[x]['description']})",
                index=list(INTERVALS.keys()).index(st.session_state.selected_interval)
            )

    # Update session state and handle changes
    if period != st.session_state.selected_period:
        st.session_state.selected_period = period
        st.experimental_rerun()

    if interval != st.session_state.selected_interval:
        st.session_state.selected_interval = interval
        st.experimental_rerun()

    # Main chart section
    if selected_table:
        stocks_df = get_stocks_from_table(selected_table)
        
        if not stocks_df.empty:
            CHARTS_PER_PAGE = 1
            total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)
            start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
            
            # Get current stock
            stock = stocks_df.iloc[start_idx]
            
            # Load chart data
            chart_data, metrics = load_chart_data(
                stock['symbol'],
                TIME_PERIODS[st.session_state.selected_period]['value'],
                INTERVALS[st.session_state.selected_interval]['value']
            )
            
            if chart_data is not None:
                # Create chart container
                with st.container():
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                    chart = create_modern_chart(chart_data, stock, metrics)
                    chart.load()
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # Navigation controls
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    if st.button("← Previous", disabled=(st.session_state.current_page == 1)):
                        st.session_state.current_page -= 1
                        st.experimental_rerun()
                
                with col2:
                    st.markdown(f"""
                        <div style='text-align: center; padding: 0.5rem;'>
                            <span style='background-color: #2d2d2d; padding: 0.5rem 1rem; border-radius: 4px;'>
                                Page {st.session_state.current_page} of {total_pages}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    if st.button("Next →", disabled=(st.session_state.current_page == total_pages)):
                        st.session_state.current_page += 1
                        st.experimental_rerun()

if __name__ == "__main__":
    main()
