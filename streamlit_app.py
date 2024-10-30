import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from contextlib import contextmanager
import plotly.graph_objs as go

# Set wide layout and custom dark theme
st.set_page_config(layout="wide", page_title="Stock Dashboard", page_icon="📈")

# Apply custom dark theme styles to match your screenshot
st.markdown("""
    <style>
    body { background-color: #0E1117; color: white; }
    .css-1lcbmhc { background-color: #0E1117; }
    h1, h2, h3, .stMetric { color: #f2f2f2 !important; }
    .stButton > button { background-color: #2E3A46; color: white; }
    .stTextInput > div { background-color: #1E262F; color: white; }
    .metric-container { text-align: center; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

# Database connection (no change)
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
def fetch_stock_data(ticker, period='1y', interval='1d'):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    return df.reset_index() if not df.empty else None

# Header section with dropdown, search bar, and navigation controls
col1, col2, col3 = st.columns([2, 1, 2])

with col1:
    selected_table = st.selectbox("📊 Select Index", get_tables(), index=0)

with col2:
    search_term = st.text_input("🔍 Search stocks...")

stocks_df = get_stocks_from_table(selected_table)

# Search filtering logic (unchanged)
filtered_stocks = stocks_df[
    stocks_df["symbol"].str.contains(search_term, case=False) |
    stocks_df["stock_name"].str.contains(search_term, case=False)
] if search_term else stocks_df

# Pagination logic
current_page = st.session_state.get('page', 1)
stocks_per_page = 10
total_pages = (len(filtered_stocks) - 1) // stocks_per_page + 1

start_index = (current_page - 1) * stocks_per_page
end_index = start_index + stocks_per_page
paginated_stocks = filtered_stocks.iloc[start_index:end_index]

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("← Previous") and current_page > 1:
        st.session_state['page'] = current_page - 1

with col2:
    st.write(f"Page {current_page} of {total_pages}")

with col3:
    if st.button("Next →") and current_page < total_pages:
        st.session_state['page'] = current_page + 1

# Display stock data and charts
if not paginated_stocks.empty:
    selected_stock = paginated_stocks.iloc[0]
    stock_data = fetch_stock_data(f"{selected_stock['symbol']}.NS")

    if stock_data is not None:
        current_price = stock_data["Close"].iloc[-1]
        prev_close = stock_data["Close"].iloc[-2] if len(stock_data) > 1 else current_price
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100

        # Display metrics for current stock
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"{selected_stock['stock_name']} ({selected_stock['symbol']})")

        with col2:
            st.metric(f"₹ {current_price:.2f}", f"{price_change_pct:.2f}%", delta_color="inverse")
        st.markdown("</div>", unsafe_allow_html=True)

        # Plotly candlestick and volume chart
        fig = go.Figure()

        # Add candlestick trace
        fig.add_trace(go.Candlestick(
            x=stock_data['Date'],
            open=stock_data['Open'],
            high=stock_data['High'],
            low=stock_data['Low'],
            close=stock_data['Close'],
            name='Candlestick'
        ))

        # Add volume bar trace
        fig.add_trace(go.Bar(
            x=stock_data['Date'],
            y=stock_data['Volume'],
            name='Volume',
            marker_color='green' if price_change >= 0 else 'red',
            opacity=0.3
        ))

        # Customize layout to match your desired theme
        fig.update_layout(
            template='plotly_dark',
            height=500,
            margin=dict(l=0, r=0, t=50, b=0),
            xaxis_title='Date',
            yaxis_title='Price',
            yaxis=dict(side='right'),
        )

        # Render the chart in Streamlit
        st.plotly_chart(fig, use_container_width=True)
