import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from contextlib import contextmanager
from lightweight_charts import Chart

# Set page layout and title
st.set_page_config(layout="wide", page_title="Stock Dashboard", page_icon="📈")

# DATABASE CONNECTION (Your original logic preserved)
@contextmanager
def get_db_connection():
    """Create a database connection and ensure proper closure."""
    conn = sqlite3.connect('stocks1.db', check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def get_tables():
    """Fetch all table names from the SQLite database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        return [table[0] for table in cursor.fetchall()]

def get_stocks_from_table(table_name):
    """Fetch stock symbols and names from a table."""
    with get_db_connection() as conn:
        query = f"SELECT DISTINCT symbol, stock_name FROM {table_name} ORDER BY symbol;"
        return pd.read_sql_query(query, conn)

@st.cache_data(ttl=300)
def fetch_stock_data(ticker, period='1y', interval='1d'):
    """Fetch stock data from Yahoo Finance."""
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    return df.reset_index() if not df.empty else None

# Header section: Dropdown, Search, and Navigation (Preserved and enhanced)
col1, col2, col3 = st.columns([2, 1, 2])

with col1:
    selected_table = st.selectbox("📊 Select Index", get_tables(), index=0)

with col2:
    search_term = st.text_input("🔍 Search stocks...", "")

# Fetching stocks from selected table
stocks_df = get_stocks_from_table(selected_table)

# Filter stocks based on user input (Preserved logic)
filtered_stocks = stocks_df[
    stocks_df["symbol"].str.contains(search_term, case=False) |
    stocks_df["stock_name"].str.contains(search_term, case=False)
] if search_term else stocks_df

# Pagination Logic (Your original lines kept)
current_page = st.session_state.get('page', 1)
stocks_per_page = 10  # Customize the number of stocks per page
total_pages = (len(filtered_stocks) - 1) // stocks_per_page + 1

start_index = (current_page - 1) * stocks_per_page
end_index = start_index + stocks_per_page
paginated_stocks = filtered_stocks.iloc[start_index:end_index]

# Navigation controls (Preserved logic)
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("← Previous") and current_page > 1:
        st.session_state['page'] = current_page - 1

with col2:
    st.write(f"Page {current_page} of {total_pages}")

with col3:
    if st.button("Next →") and current_page < total_pages:
        st.session_state['page'] = current_page + 1

# Stock Data Display (Ensuring nothing is lost)
if not paginated_stocks.empty:
    selected_stock = paginated_stocks.iloc[0]  # Default to first stock
    stock_data = fetch_stock_data(f"{selected_stock['symbol']}.NS")

    if stock_data is not None:
        # Extract price metrics (Logic unchanged)
        current_price = stock_data["Close"].iloc[-1]
        prev_close = stock_data["Close"].iloc[-2] if len(stock_data) > 1 else current_price
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100

        # Header with stock name and price change (Aligned with your design)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"{selected_stock['stock_name']} ({selected_stock['symbol']})")

        with col2:
            st.metric(f"₹ {current_price:.2f}", f"{price_change_pct:.2f}%", delta_color="inverse")

        # Chart setup (Preserving everything and matching your UI screenshot)
        chart = Chart(width="100%", height=450)

        # Candlestick data preparation
        candle_data = [
            {
                "time": int(row["Date"].timestamp()),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"]
            }
            for _, row in stock_data.iterrows()
        ]
        chart.set(series="candlestick", data=candle_data)

        # Volume data preparation
        volume_data = [
            {
                "time": int(row["Date"].timestamp()),
                "value": row["Volume"]
            }
            for _, row in stock_data.iterrows()
        ]
        chart.set(series="volume", data=volume_data, color="#00ff55" if price_change >= 0 else "#ed4807")

        # Render chart in Streamlit
        st.components.v1.html(chart.get(), height=500)

# Custom CSS (Dark mode to match your UI screenshot)
st.markdown("""
    <style>
    body {
        background-color: #0E1117;
        color: white;
    }
    .css-1lcbmhc {
        background-color: #0E1117;
    }
    .stMetric {
        font-size: 20px;
    }
    </style>
""", unsafe_allow_html=True)
