import pandas as pd
import streamlit as st
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from contextlib import contextmanager
import math
from datetime import datetime, timedelta

# Database connection management
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('stocks.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

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

# Function to validate time period and interval combination
def validate_period_interval(period, interval):
    if interval == 'Weekly':
        valid_periods = ['1Y', '2Y', '5Y', 'MAX']
        if period not in valid_periods:
            return '1Y'
    elif interval == 'Monthly':
        valid_periods = ['5Y', 'MAX']
        if period not in valid_periods:
            return '5Y'
    return period

@st.cache_data
def load_chart_data(symbol, time_period='ytd', interval='1d'):
    # Remove .NS suffix if it exists
    if '.NS' in symbol:
        ticker = symbol
    else:
        ticker = f"{symbol}.NS"
    
    try:
        # First attempt with specified period and interval
        df = yf.download(ticker, period=time_period, interval=interval)
        
        # If data is empty or insufficient, try with 'max' period
        if df.empty or len(df) < 2:
            df = yf.download(ticker, period='max', interval=interval)
            if df.empty or len(df) < 2:
                # Try without .NS suffix as a fallback
                ticker_without_ns = symbol.replace('.NS', '')
                df = yf.download(ticker_without_ns, period=time_period, interval=interval)
                if df.empty or len(df) < 2:
                    return None, None, None, None, None
        
        df.reset_index(inplace=True)
        chart_data = pd.DataFrame({
            "time": df["Date"].dt.strftime("%Y-%m-%d"),
            "open": df["Open"],
            "high": df["High"],
            "low": df["Low"],
            "close": df["Close"],
            "volume": df["Volume"]
        })
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        daily_change = ((current_price - prev_price) / prev_price) * 100
        
        return chart_data, current_price, df['Volume'].iloc[-1], daily_change
    return None, None, None, None, None
except Exception as e:
    print(f"Error loading data for {symbol}: {e}")
    # Add debug logging
    st.write(f"Debug - Symbol: {symbol}, Ticker attempted: {ticker}")
    st.write(f"Debug - Error message: {str(e)}")
    return None, None, None, None, None
        
@st.cache_data
def get_industries():
    with get_db_connection() as conn:
        query = "SELECT DISTINCT industry FROM nse WHERE industry IS NOT NULL ORDER BY industry;"
        industries = pd.read_sql_query(query, conn)
    return ['All Industries'] + industries['industry'].tolist()

@st.cache_data
def get_stocks_by_industry(industry, search_term=''):
    with get_db_connection() as conn:
        if industry == 'All Industries':
            query = """
                SELECT symbol, comp_name, industry 
                FROM nse 
                WHERE industry IS NOT NULL 
                ORDER BY comp_name;
            """
        else:
            query = f"""
                SELECT symbol, comp_name, industry 
                FROM nse 
                WHERE industry = '{industry}' 
                ORDER BY comp_name;
            """
        stocks_df = pd.read_sql_query(query, conn)
        
        if search_term:
            stocks_df = stocks_df[
                stocks_df['comp_name'].str.contains(search_term, case=False) | 
                stocks_df['symbol'].str.contains(search_term, case=False)
            ]
    return stocks_df


def create_chart(chart_data, name, symbol, current_price, volume, daily_change, industry):
    if chart_data is not None:
        chart_height = 450
        chart = StreamlitChart(height=chart_height)

        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'      
        
        st.markdown(f"""
        <div class="stock-card">
            <div class="stock-header">
                <span class="stock-name">{symbol} | ₹{current_price:.2f} | {volume:,.0f} 
                <span style='color: {change_color};'>| {change_symbol} {abs(daily_change):.2f}% </span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
        
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data)
        
        return chart
    return None

# Page setup
st.set_page_config(layout="wide", page_title="StockView Pro", page_icon="📈")

# Enhanced CSS for better styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .sidebar .sidebar-content {
        background-color: #1E222D;
        border-right: 1px solid #2D3748;
    }
    .stock-card {
        background-color: #1E222D;
        padding: 10px;
    }
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .stock-name {
        font-size: 16px;
        font-weight: bold;
        color: #ffffff;
    }
    .stock-symbol {
        font-size: 14px;
        color: #A0AEC0;
        padding: 4px 8px;
        background-color: #2D3748;
        border-radius: 4px;
    }
    .metric {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .metric-label {
        font-size: 12px;
        color: #A0AEC0;
    }
    .metric-value {
        font-size: 14px;
        font-weight: bold;
    }
    .industry-tag {
        font-size: 12px;
        color: #718096;
        padding: 4px 8px;
        background-color: #2D3748;
        border-radius: 4px;
        display: inline-block;
    }
    .search-box {
        background-color: #2D3748;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
   
    .stContainer > div {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        flex-wrap: nowrap;
        margin: 10px 0;
    }
    .pagination-button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        width: 40px;
        height: 30px;
        font-size: 16px;
        cursor: pointer;
    }
    .pagination-button:hover {
        background-color: #3e8e41;
    }
    .page-info {
        color: #A0AEC0;
        font-size: 14px;
        white-space: nowrap;
    }
    @media screen and (max-width: 640px) {
        .stContainer > div {
            gap: 10px;
            padding: 0 10px;
        }
        .pagination-button {
            width: 35px;
            height: 25px;
            font-size: 14px;
        }
        .page-info {
            font-size: 12px;
        }
    }
 

    </style>
""", unsafe_allow_html=True)


# sidebar section
with st.sidebar:
    st.title("📊 StockView")
    st.markdown("---")
    
    # Industry filter
    if 'previous_industry' not in st.session_state:
        st.session_state.previous_industry = None
    
    industries = get_industries()
    selected_industry = st.selectbox("🏢 Select Industry", industries)
    
    # Time Period and Interval Selection
    st.markdown("### ⏱️ Chart Settings")
    
    # Interval selector
    selected_interval = st.selectbox(
        "Select interval:",
        list(INTERVALS.keys()),
        index=0  # Default to Daily
    )
    
    # Time period selector with dynamic options based on interval
    if selected_interval == 'Monthly':
        period_options = ['5Y', 'MAX']
        default_index = 0
    elif selected_interval == 'Weekly':
        period_options = ['1Y', '2Y', '5Y', 'MAX']
        default_index = 0
    else:
        period_options = list(TIME_PERIODS.keys())
        default_index = 3  # Default to YTD for daily interval
    
    selected_period = st.selectbox(
        "Select time period:",
        period_options,
        index=default_index
    )
    
    # Validate and adjust period if needed
    selected_period = validate_period_interval(selected_period, selected_interval)
    
    if selected_period != st.session_state.get('last_selected_period'):
        st.session_state.current_page = 1
        st.session_state['last_selected_period'] = selected_period
    
# Reset pagination when industry changes
    if st.session_state.previous_industry != selected_industry:
        st.session_state.current_page = 1
        st.session_state.previous_industry = selected_industry
    # Enhanced search box with pagination reset
    if 'previous_search' not in st.session_state:
        st.session_state.previous_search = ""
    
    st.markdown("### 🔍 Stock Search")
    search_term = st.text_input("Search by name or symbol:", "", key="search_box")
    
    # Reset pagination when search changes
    if st.session_state.previous_search != search_term:
        st.session_state.current_page = 1
        st.session_state.previous_search = search_term
    
   # Stats display with dynamic industry counts
    st.markdown("### 📊 Quick Stats")
    with get_db_connection() as conn:
        # Total counts
        total_stocks = pd.read_sql_query("SELECT COUNT(DISTINCT symbol) as count FROM nse;", conn)['count'].iloc[0]
        total_industries = pd.read_sql_query("SELECT COUNT(DISTINCT industry) as count FROM nse;", conn)['count'].iloc[0]
        
        # Industry specific counts
        if selected_industry != 'All Industries':
            industry_stocks = pd.read_sql_query(
                f"SELECT COUNT(DISTINCT symbol) as count FROM nse WHERE industry = '{selected_industry}';", 
                conn)['count'].iloc[0]
            display_stocks = industry_stocks
            industry_text = f"Stocks in {selected_industry}"
        else:
            display_stocks = total_stocks
            industry_text = "Total Stocks"
    
    st.markdown(f"""
        <div style='padding: 10px; background-color: #2D3748; border-radius: 5px;'>
            <div style='margin-bottom: 10px;'>
                <div style='color: #A0AEC0; font-size: 12px;'>{industry_text}</div>
                <div style='font-size: 18px; font-weight: bold;'>{display_stocks}</div>
            </div>
            <div>
                <div style='color: #A0AEC0; font-size: 12px;'>Total Industries</div>
                <div style='font-size: 18px; font-weight: bold;'>{total_industries}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Initialize session states
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Get stocks data
stocks_df = get_stocks_by_industry(selected_industry, search_term)

# Display total results
st.markdown(f"### Showing {len(stocks_df)} stocks in {selected_industry}")

CHARTS_PER_PAGE = 1  # Display 9 charts per page (3 rows of 3)
total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

# Pagination controls in a single row using Streamlit container
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1], gap="small")

    # 'Previous' button logic
    with col1:
        if st.button("← Previous", disabled=(st.session_state.current_page == 1), key='prev_btn'):
            st.session_state.current_page -= 1
            st.rerun()  # Reload the app to reflect page change

    # Display the current page info
    with col2:
        st.markdown(
            f"<div class='page-info'>Page {st.session_state.current_page} of {total_pages}</div>",
            unsafe_allow_html=True
        )

    # 'Next' button logic
    with col3:
        if st.button("Next →", disabled=(st.session_state.current_page == total_pages), key='next_btn'):
            st.session_state.current_page += 1
            st.rerun()  # Reload the app to reflect page change


# Calculate start and end indices for current page
start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))
for i in range(start_idx, end_idx):
    if i < len(stocks_df):
        with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i]}..."):
            symbol = stocks_df['symbol'].iloc[i]
            name = stocks_df['comp_name'].iloc[i]
            industry = stocks_df['industry'].iloc[i]
            chart_data, current_price, volume, daily_change = load_chart_data(
                symbol, 
                TIME_PERIODS[selected_period],
                INTERVALS[selected_interval]
            )
            if chart_data is not None:
                chart = create_chart(chart_data, name, symbol, current_price, volume, 
                                  daily_change, industry)
                if chart:
                    chart.load()
            else:
                st.warning(f"No data available for {symbol} with selected settings")
# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #718096;'>
        Developed by Laksh | Data provided by Yahoo Finance
    </div>
""", unsafe_allow_html=True)
