import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math
import time

# Setting up a mobile-first page config
st.set_page_config(layout="centered", page_title="📈 ChartView Mobile", page_icon="📈")

# Mobile-friendly styling
st.markdown("""
    <style>
        /* Main background and font adjustments for mobile */
        .reportview-container {
            font-family: 'Arial', sans-serif;
            padding: 10px;
        }

        /* Sidebar styling for a simplified, mobile look */
        .sidebar .sidebar-content {
            background-color: #333745;
            color: white;
        }
        
        /* Center elements on mobile, with padding */
        .centered-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        /* Button style */
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px;
            font-size: 16px;
            width: 100%;
            transition: background-color 0.3s ease;
        }

        .stButton>button:hover {
            background-color: #45a049;
        }
        
        /* Navigation buttons styling */
        .nav-btn {
            font-size: 20px;
            padding: 10px;
        }

        /* Header text */
        h2 {
            font-weight: bold;
            color: #FFB830;
            margin-top: 0;
        }

        /* Card and container styles */
        .chart-container {
            width: 100%;
            padding: 15px;
            background-color: #FFFFFF;
            border-radius: 15px;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            transition: box-shadow 0.3s ease;
        }
        
        /* Footer text styling */
        .footer {
            color: #AAB2BD;
            font-size: 14px;
            padding: 5px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar with mobile-friendly design
with st.sidebar:
    st.title("📊 ChartView Pro Mobile")
    st.write("Track stocks on the go with a simplified view.")
    
    # Dataset selection with minimalistic dropdown
    tables = get_tables()
    selected_table = st.selectbox("Dataset", tables, key="selected_table")
    st.markdown("---")
    
    # Time Period & Interval Selector
    st.header("Settings")
    st.selectbox("Period", options=list(TIME_PERIODS.keys()), index=3, key="selected_period")
    st.selectbox("Interval", options=list(INTERVALS.keys()), index=0, key="selected_interval")

def create_chart(chart_data, name, symbol, current_price, volume, daily_change, pivot_points):
    if chart_data is not None:
        chart = StreamlitChart(height=400)  # Adjusted height for mobile
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        
        # Chart setup with compact layout for mobile
        chart.layout(background_color='#FFFFFF', text_color='#333745', font_size=12)
        chart.candle_style(up_color='#00ff55', down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        
        # Pivot line if available
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)
        
        # Display in card style
        st.markdown(f"<div class='chart-container'><h2>{name} ({symbol})</h2>", unsafe_allow_html=True)
        st.markdown(f"<p>Price: ${current_price:.2f} | Vol: {format_volume(volume)} | Change: <span style='color:{change_color}'>{daily_change:.2f}%</span></p>", unsafe_allow_html=True)
        
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# Main content in a mobile-friendly layout
if selected_table:
    stocks_df = get_stocks_from_table(selected_table)
    
    CHARTS_PER_PAGE = 1
    total_pages = math.ceil(len(stocks_df) / CHARTS_PER_PAGE)
    current_page = st.session_state.get('current_page', 1)

    start_idx = (current_page - 1) * CHARTS_PER_PAGE
    stock = stocks_df.iloc[start_idx]

    with st.spinner(f"Loading {stock['stock_name']}..."):
        chart_data, current_price, volume, daily_change, pivot_points = load_chart_data(
            stock['symbol'],
            TIME_PERIODS[st.session_state.selected_period],
            INTERVALS[st.session_state.selected_interval]
        )
        create_chart(chart_data, stock['stock_name'], stock['symbol'], current_price, volume, daily_change, pivot_points)

# Footer with page navigation, adapted for mobile
st.markdown("<hr>", unsafe_allow_html=True)
with st.container():
    cols = st.columns([1, 2, 1])

    # Previous button
    if cols[0].button("◀", key="prev", help="Previous stock", disabled=(current_page == 1)):
        st.session_state.current_page -= 1

    # Page display
    cols[1].markdown(f"<div class='centered-content'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)

    # Next button
    if cols[2].button("▶", key="next", help="Next stock", disabled=(current_page == total_pages)):
        st.session_state.current_page += 1

# Footer with minimalistic style
st.markdown("<div class='footer'>© 2023 ChartView Pro</div>", unsafe_allow_html=True)
