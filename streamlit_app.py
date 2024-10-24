import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from lightweight_charts.widgets import StreamlitChart

class UpstoxDataFetcher:
    def __init__(self):
        self.base_url = 'https://api.upstox.com/v2'
        self.headers = {
            'Accept': 'application/json'
        }
    
    def get_instrument_key(self, isin):
        return f"NSE_EQ|{isin}"
    
    def get_historical_data(self, isin, interval='day', start_date=None):
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        # Correct instrument key formatting
        instrument_key = self.get_instrument_key(isin)
        url = f'{self.base_url}/historical-candle/{instrument_key}/{interval}/{start_date}'
        
        try:
            st.write(f"Fetching data from: {url}")  # Debug log for the request URL
    
            response = requests.get(url, headers=self.headers)
    
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'candles' in data['data']:
                    return self._process_candle_data(data['data']['candles'])
                else:
                    st.warning("No data available for the selected stock or date range.")
                    return None
            elif response.status_code == 404:
                st.error("Stock not found. Please verify the symbol and try again.")
                return None
            elif response.status_code in [401, 403]:
                st.error("API authorization error. Please check your API token.")
                return None
            else:
                st.error(f"Unexpected error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return None

    
    def _process_candle_data(self, candles):
        processed_data = []
        for candle in candles:
            timestamp = datetime.fromtimestamp(candle[0] / 1000)
            processed_data.append({
                'time': timestamp.timestamp(),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })
        return processed_data

def load_isin_data():
    try:
        # Read CSV with the correct column names
        df = pd.read_csv('isin.csv')
        required_columns = ['Company Name', 'Industry', 'Symbol', 'ISIN']
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing columns in CSV: {', '.join(missing_columns)}")
            return None
        
        return df
    except Exception as e:
        st.error(f"Error loading ISIN data: {str(e)}")
        return None

def main():
    st.title("Stock Market Data Visualization")
    
    # Load ISIN data
    isin_data = load_isin_data()
    if isin_data is None:
        return
    
    # Sidebar for stock selection and date range
    st.sidebar.header("Settings")
    
    # Create a search/filter box for companies
    search_term = st.sidebar.text_input("Search Company/Symbol").lower()
    
    # Filter the dataframe based on search term
    if search_term:
        filtered_data = isin_data[
            isin_data['Company Name'].str.lower().str.contains(search_term) |
            isin_data['Symbol'].str.lower().str.contains(search_term)
        ]
    else:
        filtered_data = isin_data
    
    # Stock selection with company name and symbol
    stock_options = [f"{row['Symbol']} - {row['Company Name']}" 
                    for _, row in filtered_data.iterrows()]
    
    if not stock_options:
        st.sidebar.warning("No matches found")
        return
        
    selected_option = st.sidebar.selectbox(
        "Select Stock",
        options=stock_options,
        index=0
    )
    
    # Extract symbol and get corresponding ISIN
    selected_symbol = selected_option.split(' - ')[0]
    selected_stock_data = isin_data[isin_data['Symbol'] == selected_symbol].iloc[0]
    selected_isin = selected_stock_data['ISIN']
    
    # Display company information
    with st.expander("Company Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Company Name:**", selected_stock_data['Company Name'])
            st.write("**Symbol:**", selected_stock_data['Symbol'])
        with col2:
            st.write("**Industry:**", selected_stock_data['Industry'])
            st.write("**ISIN:**", selected_stock_data['ISIN'])
    
    # Date range selection
    start_date = st.sidebar.date_input(
        "Start Date",
        datetime.now() - timedelta(days=30)
    )
    
    # Initialize Upstox client
    upstox_client = UpstoxDataFetcher()
    
    if st.sidebar.button("Fetch Data"):
        with st.spinner("Fetching data..."):
            data = upstox_client.get_historical_data(
                selected_isin,
                start_date=start_date.strftime('%Y-%m-%d')
            )
            
            if data:
                # Create chart
                chart = StreamlitChart(
                    width=800,
                    height=600,
                    layout={
                        "textColor": "black",
                        "background": {
                            "type": "solid",
                            "color": "white"
                        }
                    }
                )

                # Add candlestick series
                candlestick_series = chart.create_candlestick_series(
                    title=f"{selected_symbol} Price",
                    price_format={"type": "price", "precision": 2},
                )
                candlestick_series.set_data(data)

                # Add volume series
                volume_series = chart.create_histogram_series(
                    title="Volume",
                    price_format={"type": "volume"},
                    color="#26a69a",
                    price_scale_id="volume",
                    price_scale={
                        "scaleMargins": {
                            "top": 0.8,
                            "bottom": 0
                        },
                        "position": "right"
                    }
                )

                # Process volume data
                volume_data = [{
                    'time': d['time'],
                    'value': d['volume'],
                    'color': '#26a69a' if d['close'] >= d['open'] else '#ef5350'
                } for d in data]
                volume_series.set_data(volume_data)

                # Display chart
                st.write(chart)
                
                # Display stats
                latest_data = data[-1]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Open", f"₹{latest_data['open']:.2f}")
                with col2:
                    st.metric("High", f"₹{latest_data['high']:.2f}")
                with col3:
                    st.metric("Low", f"₹{latest_data['low']:.2f}")
                with col4:
                    st.metric("Close", f"₹{latest_data['close']:.2f}")
                
                # Display raw data in table format
                if st.checkbox("Show Raw Data"):
                    display_data = [{
                        'Date': datetime.fromtimestamp(d['time']).strftime('%Y-%m-%d'),
                        'Open': f"₹{d['open']:.2f}",
                        'High': f"₹{d['high']:.2f}",
                        'Low': f"₹{d['low']:.2f}",
                        'Close': f"₹{d['close']:.2f}",
                        'Volume': f"{int(d['volume']):,}"
                    } for d in data]
                    st.dataframe(pd.DataFrame(display_data))

if __name__ == "__main__":
    st.set_page_config(
        page_title="Stock Market Data Visualization",
        page_icon="📈",
        layout="wide"
    )
    main()
