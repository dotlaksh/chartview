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

# Function for pivot points calculation
def calculate_pivot_points(high, low, close):
    """Calculate monthly pivot points and support/resistance levels"""
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    
    return {
        'P': round(pivot, 2),
        'R1': round(r1, 2),
        'R2': round(r2, 2),
        'R3': round(r3, 2),
        'S1': round(s1, 2),
        'S2': round(s2, 2),
        'S3': round(s3, 2)
    }

@st.cache_data
def load_chart_data(symbol):
    ticker = f"{symbol}.NS"
    try:
        df = yf.download(ticker, period='ytd', interval='1d')
        df.reset_index(inplace=True)
        
        if not df.empty:
            current_month = datetime.now().strftime('%Y-%m')
            prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev_month_data = df[df['Date'].dt.strftime('%Y-%m') == prev_month]
            
            if len(prev_month_data) > 0:
                monthly_high = prev_month_data['High'].max()
                monthly_low = prev_month_data['Low'].min()
                monthly_close = prev_month_data['Close'].iloc[-1]
                pivot_points = calculate_pivot_points(monthly_high, monthly_low, monthly_close)
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
            
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            daily_change = ((current_price - prev_price) / prev_price) * 100
            
            return chart_data, current_price, df['Volume'].iloc[-1], daily_change, pivot_points
        return None, None, None, None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None, None, None

def create_chart(chart_data, name, symbol, current_price, volume, daily_change, pivot_points, industry):
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
    
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#227cf4', width=1, style='solid')
            chart.horizontal_line(pivot_points['R1'], color='#ed4807', width=1, style='dashed')
            chart.horizontal_line(pivot_points['R2'], color='#ed4807', width=1, style='dashed')
            chart.horizontal_line(pivot_points['R3'], color='#ed4807', width=1, style='dashed')
            chart.horizontal_line(pivot_points['S1'], color='#00ff55', width=1, style='dashed')
            chart.horizontal_line(pivot_points['S2'], color='#00ff55', width=1, style='dashed')
            chart.horizontal_line(pivot_points['S3'], color='#00ff55', width=1, style='dashed')

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
        font-size: 18px;
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
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        width: 100%;
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #3e8e41;
    }
    </style>
    """, unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.title("📊 StockView Pro")
    st.markdown("---")
    
    # Industry filter with pagination reset
    if 'previous_industry' not in st.session_state:
        st.session_state.previous_industry = None
    
    industries = get_industries()
    selected_industry = st.selectbox("🏢 Select Industry", industries)
    
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

CHARTS_PER_PAGE = 3
total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

# Pagination controls
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if st.button("← Previous", key='prev', disabled=(st.session_state.current_page == 1)):
        st.session_state.current_page -= 1
        st.rerun()

with col2:
    st.markdown(f"""
        <div style='text-align: center; color: #A0AEC0;'>
            Page {st.session_state.current_page} of {total_pages}
        </div>
    """, unsafe_allow_html=True)

with col3:
    if st.button("Next →", key='next', disabled=(st.session_state.current_page == total_pages)):
        st.session_state.current_page += 1
        st.rerun()

# Adjusted code for displaying three charts per row

# Display charts in a loop
start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))

# Adjust `CHARTS_PER_PAGE` to ensure we display three charts per row (a multiple of 3)
CHARTS_PER_PAGE = 9  # or any multiple of 3

for i in range(start_idx, end_idx, 3):
    col1, col2, col3 = st.columns([1, 1, 1], gap='small')  # Adjusted to have three columns per row

    # First chart
    with col1:
        if i < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i]}..."):
                symbol = stocks_df['symbol'].iloc[i]
                name = stocks_df['comp_name'].iloc[i]
                industry = stocks_df['industry'].iloc[i]
                chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, name, symbol, current_price, volume, 
                                      daily_change, pivot_points, industry)
                    if chart:
                        chart.load()

    # Second chart
    with col2:
        if i + 1 < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i + 1]}..."):
                symbol = stocks_df['symbol'].iloc[i + 1]
                name = stocks_df['comp_name'].iloc[i + 1]
                industry = stocks_df['industry'].iloc[i + 1]
                chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, name, symbol, current_price, volume, 
                                      daily_change, pivot_points, industry)
                    if chart:
                        chart.load()

    # Third chart
    with col3:
        if i + 2 < len(stocks_df):
            with st.spinner(f"Loading {stocks_df['comp_name'].iloc[i + 2]}..."):
                symbol = stocks_df['symbol'].iloc[i + 2]
                name = stocks_df['comp_name'].iloc[i + 2]
                industry = stocks_df['industry'].iloc[i + 2]
                chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(symbol)
                if chart_data is not None:
                    chart = create_chart(chart_data, name, symbol, current_price, volume, 
                                      daily_change, pivot_points, industry)
                    if chart:
                        chart.load()


# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #718096;'>
        Developed by Laksh | Data provided by Yahoo Finance
    </div>
""", unsafe_allow_html=True)
