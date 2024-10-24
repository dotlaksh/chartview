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
    
    def get_historical_data(self, isin, interval='day', start_date=None):
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
        url = f'{self.base_url}/historical-candle/NSE_EQ%7C{isin}/{interval}/{start_date}'
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return self._process_candle_data(data['data']['candles'])
            else:
                st.error(f"Error fetching data: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            st.error(f"Error: {str(e)}")
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
        df = pd.read_csv('isin.csv')
        return df
    except Exception as e:
        st.error(f"Error loading ISIN data: {str(e)}")
        return None

def main():
    st.title("Stock Market Data Visualization")
    
    # Load ISIN data
    isin_data = load_isin_data()
    if isin_data is None:
        st.error("Could not load ISIN data. Please check if 'isin.csv' exists.")
        return
    
    # Sidebar for stock selection and date range
    st.sidebar.header("Settings")
    
    # Stock selection
    selected_stock = st.sidebar.selectbox(
        "Select Stock",
        isin_data['Symbol'].tolist(),
        index=0
    )
    
    # Get ISIN for selected stock
    selected_isin = isin_data[isin_data['Symbol'] == selected_stock]['ISIN'].iloc[0]
    
    # Date range selection
    start_date = st.sidebar.date_input(
        "Start Date",
        datetime.now() - timedelta(days=365)
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
                    title=f"{selected_stock} Price",
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
            else:
                st.error("Failed to fetch data. Please try again.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Stock Market Data Visualization",
        page_icon="📈",
        layout="wide"
    )
    main()
