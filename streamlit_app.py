import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math

# Page configuration
st.set_page_config(layout="wide", page_title="Stock Dashboard")
st.title("NSE Stocks Dashboard")

# Read stock data
@st.cache_data
def load_stock_data():
    return pd.read_csv('nse.csv')

# Fetch stock data from yfinance
@st.cache_data
def fetch_stock_data(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    try:
        stock = yf.download(symbol, start=start_date, end=end_date)
        return stock
    except:
        return None

# Create candlestick chart
def create_candlestick(data, symbol):
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                                        open=data['Open'],
                                        high=data['High'],
                                        low=data['Low'],
                                        close=data['Close'])])
    
    fig.update_layout(
        title=f'{symbol} Stock Price',
        yaxis_title='Price',
        xaxis_title='Date',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    return fig

# Load stock data
stocks_df = load_stock_data()
symbols = stocks_df['Symbol'].tolist()  # Assuming 'Symbol' is the column name

# Calculate total pages
CHARTS_PER_PAGE = 9
CHARTS_PER_ROW = 3
total_pages = math.ceil(len(symbols) / CHARTS_PER_PAGE)

# Add pagination controls
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    current_page = st.number_input('Page', min_value=1, max_value=total_pages, value=1)

# Calculate start and end index for current page
start_idx = (current_page - 1) * CHARTS_PER_PAGE
end_idx = min(start_idx + CHARTS_PER_PAGE, len(symbols))

# Create progress bar
progress_bar = st.progress(0)

# Display charts in grid
for i in range(start_idx, end_idx, CHARTS_PER_ROW):
    cols = st.columns(CHARTS_PER_ROW)
    for j in range(CHARTS_PER_ROW):
        if i + j < end_idx:
            symbol = symbols[i + j]
            with cols[j]:
                data = fetch_stock_data(symbol)
                if data is not None and not data.empty:
                    fig = create_candlestick(data, symbol)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Unable to fetch data for {symbol}")
        
        # Update progress
        progress = (i + j - start_idx + 1) / min(CHARTS_PER_PAGE, end_idx - start_idx)
        progress_bar.progress(progress)

# Add page navigation buttons
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    if current_page > 1:
        if st.button('← Previous'):
            current_page -= 1

with col4:
    if current_page < total_pages:
        if st.button('Next →'):
            current_page += 1

# Display page information
st.write(f"Page {current_page} of {total_pages}")
