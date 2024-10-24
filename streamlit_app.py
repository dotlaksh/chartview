import pandas as pd
import streamlit as st
import requests
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math

# [Previous helper functions remain the same: load_isin_data, load_chart_data, create_chart]

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
