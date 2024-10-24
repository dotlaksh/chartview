import pandas as pd
import streamlit as st
import requests
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math
import json

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

@st.cache_data
def load_chart_data(instrument_key):
    if not instrument_key:
        st.error("No instrument key provided")
        return None, None, None, None

    interval = "day"
    to_date = datetime.now().strftime('%Y-%m-%d')
    encoded_instrument = requests.utils.quote(f"NSE_EQ|{instrument_key}")
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_instrument}/{interval}/{to_date}"

    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0',
        'Authorization': 'Bearer YOUR_API_KEY'  # Replace with actual API key
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if 'status' not in response_data or response_data['status'] != 'success':
            st.error("API response indicates failure")
            return None, None, None, None

        if 'data' not in response_data or 'candles' not in response_data['data']:
            st.error("Missing expected data structure in API response")
            return None, None, None, None

        candles = response_data['data']['candles']
        if not candles:
            st.warning(f"No candle data available for {instrument_key}")
            return None, None, None, None

        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')

        chart_data = pd.DataFrame({
            "time": df["timestamp"],
            "open": df["open"].astype(float),
            "high": df["high"].astype(float),
            "low": df["low"].astype(float),
            "close": df["close"].astype(float),
            "volume": df["volume"].astype(float)
        })

        current_price = float(df['close'].iloc[-1])
        prev_price = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
        daily_change = ((current_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
        volume = float(df['volume'].iloc[-1])

        return chart_data, current_price, volume, daily_change

    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {str(e)}")
        if hasattr(e.response, 'text'):
            st.write(f"Debug - Error response content: {e.response.text}")
        return None, None, None, None
    except json.JSONDecodeError as e:
        st.error(f"JSON Parsing Error: {str(e)}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Unexpected Error: {str(e)}")
        import traceback
        st.write("Debug - Full error traceback:", traceback.format_exc())
        return None, None, None, None

def create_chart(chart_data, name, instrument_key, current_price, volume, daily_change):
    if chart_data is None or chart_data.empty:
        st.warning(f"No chart data available for {name}")
        return None

    try:
        formatted_data = chart_data.to_dict('records')
        st.write("Debug - Formatted chart data sample:", formatted_data[0])

        chart = StreamlitChart(height=450)

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

        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12, font_family='Helvetica')
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.volume_config(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal', vert_color='#FFFFFF', horz_color='#FFFFFF')
        chart.time_scale(visible=True, time_visible=True)
        chart.grid(vert_enabled=False, horz_enabled=False)

        chart.set(formatted_data)
        return chart

    except Exception as e:
        st.error(f"Error creating chart for {name}: {str(e)}")
        import traceback
        st.write("Debug - Chart creation error traceback:", traceback.format_exc())
        return None

# Page setup
st.set_page_config(layout="wide", page_title="ChartView 2.0", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stock-info { background-color: #1E222D; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

stocks_df = load_isin_data()

if not stocks_df.empty:
    st.title("Market Overview")
    for i, row in stocks_df.iterrows():
        instrument_key = row['ISIN']
        name = row.get('Name', f"Stock {i + 1}")
        chart_data, current_price, volume, daily_change = load_chart_data(instrument_key)
        if chart_data is not None:
            chart = create_chart(chart_data, name, instrument_key, current_price, volume, daily_change)
            if chart:
                chart.load()
else:
    st.error("Unable to load stock data. Please check the CSV file.")
