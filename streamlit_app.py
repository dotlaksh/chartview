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

def format_volume(volume):
    """
    Format volume to display in M or K
    Examples:
    1,500,000 -> 1.5M
    150,000 -> 150K
    1,000 -> 1K
    """
    if volume >= 1_000_000:
        return f'{volume/1_000_000:.1f}M'
    elif volume >= 1_000:
        return f'{volume/1_000:.0f}K'
    else:
        return str(volume)


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
            df = stock.history(period='ytd', interval='1d')
            
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
                # Get today's and yesterday's dates
                today = pd.Timestamp.now().strftime('%Y-%m-%d')
                
                # Get today's data
                today_data = df[df['Date'].dt.strftime('%Y-%m-%d') == today]
                
                # If no data for today (e.g., market holiday or weekend),
                # use the latest available day
                if today_data.empty:
                    current_price = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
                else:
                    # Get today's index
                    today_idx = df[df['Date'].dt.strftime('%Y-%m-%d') == today].index[0]
                    current_price = df['Close'].iloc[today_idx]
                    prev_close = df['Close'].iloc[today_idx - 1] if today_idx > 0 else current_price

                # Calculate daily change
                daily_change = ((current_price - prev_close) / prev_close) * 100
                
                # Get latest volume
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
        chart = StreamlitChart(height=525)  # Fixed height in pixels
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '+' if daily_change >= 0 else '-'
        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        # Format volume
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
        chart.price_line(label_visible=True,line_visible=True)
        chart.fit()
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# Initial page config
st.set_page_config(layout="wide", page_title="ChartView 2.0", page_icon="📈")

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


# Main content
    if selected_table:
        stocks_df = get_stocks_from_table(selected_table)
        
        CHARTS_PER_PAGE = 1
        total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1

        start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
        stock = stocks_df.iloc[start_idx]

        with st.spinner(f"Loading {stock['stock_name']}..."):
            chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(stock['symbol'])
            create_chart(chart_data, stock['stock_name'], stock['symbol'], current_price, volume, daily_change, pivot_points)

        # Updated pagination with flex layout
        st.markdown("""
            <style>
                .pagination-container {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 10px;
                    margin: 10px 0;
                    flex-wrap: nowrap;
                }
                .pagination-button {
                    background-color: #1E222D;
                    color: white;
                    border: 1px solid #404756;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    min-width: 100px;
                    text-align: center;
                }
                .pagination-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .pagination-info {
                    padding: 0 15px;
                    white-space: nowrap;
                }
                @media (max-width: 768px) {
                    .pagination-container {
                        padding: 0 5px;
                    }
                    .pagination-button {
                        min-width: 80px;
                        padding: 6px 12px;
                        font-size: 14px;
                    }
                    .pagination-info {
                        padding: 0 10px;
                        font-size: 14px;
                    }
                }
            </style>
            <div class="pagination-container">
                <button 
                    class="pagination-button"
                    onclick="document.querySelector('[data-testid=\'stFormSubmitButton\']').click()"
                    {}
                >
                    ← Previous
                </button>
                <div class="pagination-info">
                    Page {current} of {total}
                </div>
                <button 
                    class="pagination-button"
                    onclick="document.querySelector('[data-testid=\'stFormSubmitButton\']').click()"
                    {}
                >
                    Next →
                </button>
            </div>
        """.format(
            'disabled style="opacity: 0.5"' if st.session_state.current_page == 1 else '',
            'disabled style="opacity: 0.5"' if st.session_state.current_page == total_pages else '',
            current=st.session_state.current_page,
            total=total_pages
        ), unsafe_allow_html=True)

        # Hidden form for handling button clicks
        with st.form(key='pagination_form'):
            prev_clicked = st.form_submit_button('Previous', type='primary', style='display: none;')
            next_clicked = st.form_submit_button('Next', type='primary', style='display: none;')
            
            if prev_clicked and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()
            elif next_clicked and st.session_state.current_page < total_pages:
                st.session_state.current_page += 1
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; padding: 10px; font-size: 12px;'>
        Developed by Laksh | Data from Yahoo Finance
    </div>
""", unsafe_allow_html=True)
