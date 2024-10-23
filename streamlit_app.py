import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Streamlit app details
st.set_page_config(page_title="NSE Stock Analysis", layout="wide")

# Format large numbers into readable format
def format_value(value):
    if pd.isna(value) or value == 'N/A':
        return 'N/A'
    try:
        value = float(value)
        suffixes = ["", "K", "M", "B", "T"]
        suffix_index = 0
        while value >= 1000 and suffix_index < len(suffixes) - 1:
            value /= 1000
            suffix_index += 1
        return f"₹{value:.1f}{suffixes[suffix_index]}"
    except:
        return 'N/A'

# Main app
def main():
    # Sidebar controls
    with st.sidebar:
        st.title("NSE Stock Analysis")
        
        # Stock selection
        ticker = st.text_input("Enter stock symbol (e.g., TCS, RELIANCE)", "TCS")
        if ticker:
            ticker = f"{ticker.upper()}.NS"
        
        # Time period selection
        periods = {
            "1 Day": "1d",
            "5 Days": "5d",
            "1 Month": "1mo",
            "3 Months": "3mo",
            "6 Months": "6mo",
            "1 Year": "1y",
            "2 Years": "2y",
            "5 Years": "5y",
            "YTD": "ytd",
        }
        selected_period = st.selectbox("Select Time Period", list(periods.keys()))
        
        intervals = {
            "1 Day": "1m",
            "5 Days": "5m",
            "1 Month": "1h",
            "3 Months": "1d",
            "6 Months": "1d",
            "1 Year": "1d",
            "2 Years": "1wk",
            "5 Years": "1wk",
            "YTD": "1d",
        }
        
        button = st.button("Analyze")

    if button and ticker:
        try:
            # Fetch stock data
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get historical data
            history = stock.history(
                period=periods[selected_period],
                interval=intervals[selected_period]
            )
            
            if len(history) == 0:
                st.error("No data available for the selected stock and period.")
                return

            # Display stock header with company name
            company_name = info.get('longName', ticker)
            st.subheader(f"{company_name} ({ticker})")

            # Create price chart using Plotly
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=history.index,
                open=history['Open'],
                high=history['High'],
                low=history['Low'],
                close=history['Close'],
                name='Price'
            ))
            fig.update_layout(
                title='Stock Price Movement',
                yaxis_title='Price (₹)',
                xaxis_title='Date',
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Create three columns for metrics
            col1, col2, col3 = st.columns(3)
            
            # Company Info
            with col1:
                st.subheader("Company Information")
                company_info = pd.DataFrame({
                    "Metric": [
                        "Sector",
                        "Industry",
                        "Market Cap",
                        "Enterprise Value",
                        "P/E Ratio",
                        "PEG Ratio"
                    ],
                    "Value": [
                        info.get('sector', 'N/A'),
                        info.get('industry', 'N/A'),
                        format_value(info.get('marketCap', 'N/A')),
                        format_value(info.get('enterpriseValue', 'N/A')),
                        f"{info.get('trailingPE', 'N/A'):.2f}" if info.get('trailingPE') else 'N/A',
                        f"{info.get('pegRatio', 'N/A'):.2f}" if info.get('pegRatio') else 'N/A'
                    ]
                })
                st.dataframe(company_info, hide_index=True)

            # Price Information
            with col2:
                st.subheader("Price Information")
                current_price = info.get('currentPrice', history['Close'][-1])
                prev_close = info.get('previousClose', history['Close'][-2] if len(history) > 1 else None)
                
                price_info = pd.DataFrame({
                    "Metric": [
                        "Current Price",
                        "Previous Close",
                        "Day High",
                        "Day Low",
                        "52 Week High",
                        "52 Week Low"
                    ],
                    "Value": [
                        f"₹{current_price:.2f}" if current_price else 'N/A',
                        f"₹{prev_close:.2f}" if prev_close else 'N/A',
                        f"₹{info.get('dayHigh', 'N/A'):.2f}" if info.get('dayHigh') else 'N/A',
                        f"₹{info.get('dayLow', 'N/A'):.2f}" if info.get('dayLow') else 'N/A',
                        f"₹{info.get('fiftyTwoWeekHigh', 'N/A'):.2f}" if info.get('fiftyTwoWeekHigh') else 'N/A',
                        f"₹{info.get('fiftyTwoWeekLow', 'N/A'):.2f}" if info.get('fiftyTwoWeekLow') else 'N/A'
                    ]
                })
                st.dataframe(price_info, hide_index=True)

            # Trading Statistics
            with col3:
                st.subheader("Trading Statistics")
                trading_stats = pd.DataFrame({
                    "Metric": [
                        "Volume",
                        "Avg. Volume (10d)",
                        "Beta",
                        "Forward P/E",
                        "Dividend Rate",
                        "Dividend Yield"
                    ],
                    "Value": [
                        format_value(info.get('volume', 'N/A')),
                        format_value(info.get('averageVolume10days', 'N/A')),
                        f"{info.get('beta', 'N/A'):.2f}" if info.get('beta') else 'N/A',
                        f"{info.get('forwardPE', 'N/A'):.2f}" if info.get('forwardPE') else 'N/A',
                        f"₹{info.get('dividendRate', 'N/A'):.2f}" if info.get('dividendRate') else 'N/A',
                        f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else 'N/A'
                    ]
                })
                st.dataframe(trading_stats, hide_index=True)

        except Exception as e:
            st.error(f"An error occurred while analyzing the stock: {e}")

if __name__ == "__main__":
    main()
