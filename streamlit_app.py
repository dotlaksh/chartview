import pandas as pd
import streamlit as st
import sqlite3
import requests
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

# Time period mappings
TIME_PERIODS = {
    '1M': 30,
    '3M': 90,
    '6M': 180,
    'YTD': None,  # Will be calculated dynamically
    '1Y': 365,
    '2Y': 730,
    '5Y': 1825,
    'MAX': 3650  # About 10 years
}

INTERVALS = {
    'Daily': 'day',
    'Weekly': 'week',
    'Monthly': 'month'
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

def get_date_range(time_period):
    end_date = datetime.now()
    
    if time_period == 'YTD':
        start_date = datetime(end_date.year, 1, 1)
    else:
        days = TIME_PERIODS[time_period]
        start_date = end_date - timedelta(days=days)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# Modified load_chart_data function to use Upstox API
@st.cache_data
def load_chart_data(symbol, time_period='YTD', interval='day'):
    try:
        # Get date range based on time period
        start_date, end_date = get_date_range(time_period)
        
        # Construct the Upstox API URL
        url = f'https://api.upstox.com/v2/historical-candle/NSE_EQ|{symbol}/{interval}/{start_date}/{end_date}'
        
        headers = {
            'Accept': 'application/json',
            'Api-Version': '2.0',
            'Authorization': f'Bearer {st.secrets["upstox_api_key"]}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()['data']
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            chart_data = pd.DataFrame({
                "time": df["timestamp"].dt.strftime("%Y-%m-%d"),
                "open": df["open"],
                "high": df["high"],
                "low": df["low"],
                "close": df["close"],
                "volume": df["volume"]
            })
            
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2]
            daily_change = ((current_price - prev_price) / prev_price) * 100
            
            return {
                'chart_data': chart_data,
                'current_price': current_price,
                'volume': df['volume'].iloc[-1],
                'daily_change': daily_change
            }
        return None
    except Exception as e:
        print(f"Error loading data for {symbol}: {e}")
        return None

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

# CSS styles
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stock-card {
        background-color: #1E222D;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .stock-name {
        font-size: 16px;
        font-weight: bold;
    }
    .page-info {
        text-align: center;
        color: #A0AEC0;
        font-size: 14px;
    }
    .stButton>button {
        width: 100%;
        background-color: #2D3748;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #4A5568;
    }
    .stButton>button:disabled {
        background-color: #1A202C;
        color: #718096;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar setup
with st.sidebar:
    st.title("📊 StockView")
    
    # Industry filter
    if 'previous_industry' not in st.session_state:
        st.session_state.previous_industry = None
    
    industries = get_industries()
    selected_industry = st.selectbox("🏢 Select Industry", industries)
    
    # Time Period and Interval Selection
    st.markdown("### ⏱️ Chart Settings")
    
    selected_interval = st.selectbox(
        "Select interval:",
        list(INTERVALS.keys()),
        index=0
    )
    
    if selected_interval == 'Monthly':
        period_options = ['5Y', 'MAX']
        default_index = 0
    elif selected_interval == 'Weekly':
        period_options = ['1Y', '2Y', '5Y', 'MAX']
        default_index = 0
    else:
        period_options = list(TIME_PERIODS.keys())
        default_index = 3
    
    selected_period = st.selectbox(
        "Select time period:",
        period_options,
        index=default_index
    )
    
    selected_period = validate_period_interval(selected_period, selected_interval)
    
    if selected_period != st.session_state.get('last_selected_period'):
        st.session_state.current_page = 1
        st.session_state['last_selected_period'] = selected_period
    
    # Reset pagination when industry changes
    if st.session_state.previous_industry != selected_industry:
        st.session_state.current_page = 1
        st.session_state.previous_industry = selected_industry

    # Search box
    if 'previous_search' not in st.session_state:
        st.session_state.previous_search = ""
    
    st.markdown("### 🔍 Stock Search")
    search_term = st.text_input("Search by name or symbol:", "", key="search_box")
    
    if st.session_state.previous_search != search_term:
        st.session_state.current_page = 1
        st.session_state.previous_search = search_term
    
    # Stats display
    st.markdown("### 📊 Quick Stats")
    with get_db_connection() as conn:
        total_stocks = pd.read_sql_query("SELECT COUNT(DISTINCT symbol) as count FROM nse;", conn)['count'].iloc[0]
        total_industries = pd.read_sql_query("SELECT COUNT(DISTINCT industry) as count FROM nse;", conn)['count'].iloc[0]
        
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

CHARTS_PER_PAGE = 3
total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

# Pagination controls
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1], gap="small")

    with col1:
        if st.button("← Previous", disabled=(st.session_state.current_page == 1), key='prev_btn'):
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        st.markdown(
            f"<div class='page-info'>Page {st.session_state.current_page} of {total_pages}</div>",
            unsafe_allow_html=True
        )

    with col3:
        if st.button("Next →", disabled=(st.session_state.current_page == total_pages), key='next_btn'):
            st.session_state.current_page += 1
            st.rerun()

# Calculate page indices
start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))

# Display charts
for i in range(start_idx, end_idx, 3):
    col1, col2, col3 = st.columns([1, 1, 1], gap='small')
    
    # First chart
    with col1:
        if i < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i]}..."):
                symbol = stocks_df['symbol'].iloc[i]
                name = stocks_df['comp_name'].iloc[i]
                industry = stocks_df['industry'].iloc[i]
                
                result = load_chart_data(
                    symbol, 
                    selected_period,
                    INTERVALS[selected_interval]
                )
                
                if result is not None:
                    chart = create_chart(
                        result['chart_data'],
                        name,
                        symbol,
                        result['current_price'],
                        result['volume'],
                        result['daily_change'],
                        industry
                    )
                    if chart:
                        chart.load()
                else:
                    st.warning(f"No data available for {symbol} with selected settings")

    # Second chart
    with col2:
        if i + 1 < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i + 1]}..."):
                symbol = stocks_df['symbol'].iloc[i + 1]
                name = stocks_df['comp_name'].iloc[i + 1]
                industry = stocks_df['industry'].iloc[i + 1]
                
                result = load_chart_data(
                    symbol,
                    TIME_PERIODS[selected_period],
                    INTERVALS[selected_interval]
                )
                
                if result is not None:
                    chart = create_chart(
                        result['chart_data'],
                        name,
                        symbol,
                        result['current_price'],
                        result['volume'],
                        result['daily_change'],
                        industry
                    )
                    if chart:
                        chart.load()
                else:
                    st.warning(f"No data available for {symbol} with selected settings")

    # Third chart
    with col3:
        if i + 2 < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i + 2]}..."):
                symbol = stocks_df['symbol'].iloc[i + 2]
                name = stocks_df['comp_name'].iloc[i + 2]
                industry = stocks_df['industry'].iloc[i + 2]
                
                result = load_chart_data(
                    symbol,
                    TIME_PERIODS[selected_period],
                    INTERVALS[selected_interval]
                )
                
                if result is not None:
                    chart = create_chart(
                        result['chart_data'],
                        name,
                        symbol,
                        result['current_price'],
                        result['volume'],
                        result['daily_change'],
                        industry
                    )
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
