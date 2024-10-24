import pandas as pd
import streamlit as st
import requests
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math

# Load ISIN data from CSV with better error handling
def load_isin_data():
    try:
        isin_df = pd.read_csv('isin.csv')
        
        # Check if ISIN column exists (case-insensitive)
        isin_column = None
        for col in isin_df.columns:
            if col.upper() == 'ISIN':
                isin_column = col
                break
        
        if isin_column is None:
            st.error("No 'ISIN' column found in the CSV file. Available columns: " + ", ".join(isin_df.columns))
            return pd.DataFrame()
            
        # Standardize column name to 'ISIN'
        isin_df = isin_df.rename(columns={isin_column: 'ISIN'})
        
        # Validate data
        if len(isin_df) == 0:
            st.warning("CSV file is empty")
            return pd.DataFrame()
            
        return isin_df
        
    except FileNotFoundError:
        st.error("Could not find 'isin.csv'. Please make sure the file exists in the same directory as the application.")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        st.error("The CSV file is empty")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading ISIN data: {str(e)}")
        return pd.DataFrame()

# Define a function to load chart data from Upstox API
@st.cache_data
def load_chart_data(instrument_key):
    if not instrument_key:
        return None, None, None, None
        
    interval = "day"
    to_date = datetime.now().strftime('%Y-%m-%d')
    
    # Properly encode the instrument key in the URL
    encoded_instrument = requests.utils.quote(f"NSE_EQ|{instrument_key}")
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_instrument}/{interval}/{to_date}"
    
    # Add logging to help debug URL construction
    st.debug(f"Requesting data from URL: {url}")
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0' # Add a user agent header
        # Include authentication headers if necessary
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # Add debug logging for response
        st.debug(f"Response status code: {response.status_code}")
        if response.status_code != 200:
            st.debug(f"Response content: {response.text}")
            
        response.raise_for_status()
        data = response.json()
        
        if not data.get('candles'):
            st.warning(f"No data available for {instrument_key}")
            return None, None, None, None
            
        df = pd.DataFrame(data['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        chart_data = pd.DataFrame({
            "time": df["timestamp"].dt.strftime("%Y-%m-%d"),
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "volume": df["volume"]
        })

        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2] if len(df) > 1 else current_price
        daily_change = ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0

        return chart_data, current_price, df['volume'].iloc[-1], daily_change
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading data for {instrument_key}: {str(e)}")
        st.debug(f"Request exception details: {str(e)}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Unexpected error processing data for {instrument_key}: {str(e)}")
        st.debug(f"Exception details: {str(e)}")
        return None, None, None, None

def create_chart(chart_data, name, instrument_key, current_price, volume, daily_change):
    if chart_data is not None:
        chart_height = 450
        chart = StreamlitChart(height=chart_height)

        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        change_symbol = '▲' if daily_change >= 0 else '▼'      
        
        st.markdown(f"""
        <div class="stock-info">
            <span style='font-size: 16px; font-weight: bold;'>{name}</span>
            <span style='color: #00ff55;'>₹{current_price:.2f}</span> | 
            <span style='color: {change_color};'>{change_symbol} {abs(daily_change):.2f}%</span> | 
            Vol: {volume:,.0f}
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
        
        chart.time_scale(right_offset=5, min_bar_spacing=10)
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.set(chart_data)
        return chart
    return None

# Page setup
st.set_page_config(layout="wide", page_title="ChartView 2.0", page_icon="📈")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stSelectbox, .stTextInput {
        background-color: #262730;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
    }
    .stock-info {
        background-color: #1E222D;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Load ISIN data
stocks_df = load_isin_data()

# Only proceed if we have valid data
if not stocks_df.empty:
    # Initialize session states
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Sidebar for controls
    with st.sidebar:
        st.title("📊 ChartView 2.0")
        st.markdown("---")
        
        CHARTS_PER_PAGE = 12
        total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)

        # Pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.button("← Previous", key='prev', disabled=(st.session_state.current_page == 1)):
                st.session_state.current_page -= 1
                st.rerun()

        with col2:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")

        with col3:
            if st.button("Next →", key='next', disabled=(st.session_state.current_page == total_pages)):
                st.session_state.current_page += 1
                st.rerun()

    # Main content area
    st.title("Market Overview")
    
    # Determine start and end indices for pagination
    start_idx = (st.session_state.current_page - 1) * CHARTS_PER_PAGE
    end_idx = min(start_idx + CHARTS_PER_PAGE, len(stocks_df))

    # Display charts in a loop in the main area
    for i in range(start_idx, end_idx, 2):
        col1, col2 = st.columns([1, 1], gap='small')

        # First chart
        with col1:
            try:
                with st.spinner(f"Loading {stocks_df['ISIN'].iloc[i]}..."):
                    instrument_key = stocks_df['ISIN'].iloc[i]
                    name = f"Stock {i + 1}"
                    if 'Name' in stocks_df.columns:
                        name = stocks_df['Name'].iloc[i]
                    chart_data, current_price, volume, daily_change = load_chart_data(instrument_key)
                    if chart_data is not None:
                        chart = create_chart(chart_data, name, instrument_key, current_price, volume, daily_change)
                        if chart:
                            chart.load()
            except Exception as e:
                st.error(f"Error displaying chart {i + 1}: {str(e)}")

        # Second chart (if available)
        with col2:
            if i + 1 < end_idx:
                try:
                    with st.spinner(f"Loading {stocks_df['ISIN'].iloc[i + 1]}..."):
                        instrument_key = stocks_df['ISIN'].iloc[i + 1]
                        name = f"Stock {i + 2}"
                        if 'Name' in stocks_df.columns:
                            name = stocks_df['Name'].iloc[i + 1]
                        chart_data, current_price, volume, daily_change = load_chart_data(instrument_key)
                        if chart_data is not None:
                            chart = create_chart(chart_data, name, instrument_key, current_price, volume, daily_change)
                            if chart:
                                chart.load()
                except Exception as e:
                    st.error(f"Error displaying chart {i + 2}: {str(e)}")

    # Footer in main content area
    st.markdown("---")
    st.markdown("Developed by Laksh | Data provided by Upstox")
else:
    st.error("Unable to load stock data. Please check the CSV file and try again.")
