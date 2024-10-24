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
    st.write(f"Debug - Requesting data from URL: {url}")
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0' # Add a user agent header
        # Include authentication headers if necessary
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # Add debug logging for response
        st.write(f"Debug - Response status code: {response.status_code}")
        if response.status_code != 200:
            st.write(f"Debug - Response content: {response.text}")
            
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
        st.write(f"Debug - Request exception details: {str(e)}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Unexpected error processing data for {instrument_key}: {str(e)}")
        st.write(f"Debug - Exception details: {str(e)}")
        return None, None, None, None
