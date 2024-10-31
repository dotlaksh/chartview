import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from lightweight_charts.widgets import StreamlitChart
from datetime import datetime, timedelta
import math
import time

st.set_page_config(layout="wide", page_title="ChartView Pro", page_icon="📈")

# Enhanced styling
st.markdown("""
    <style>
        .sidebar .sidebar-content {
            background-color: #2E4053;
        }
        .stButton>button {
            width: 100%;
            height: 100%;
            font-size: 18px;
            padding: 10px;
        }
        .chart-container {
            padding: 20px;
            background-color: #1E2E42;
            border-radius: 10px;
        }
        .footer {
            color: #AAB2BD;
            padding: 10px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar with theme
with st.sidebar:
    st.title("📊 ChartView Pro")
    st.write("Track and analyze stock performance with ease.")
    tables = get_tables()
    selected_table = st.selectbox("Select Dataset:", tables, key="selected_table")
    st.markdown("---")
    
    # Time Period & Interval Selection
    st.header("Settings")
    st.selectbox("Select Period:", options=list(TIME_PERIODS.keys()), index=3, key="selected_period")
    st.selectbox("Select Interval:", options=list(INTERVALS.keys()), index=0, key="selected_interval")

def create_chart(chart_data, name, symbol, current_price, volume, daily_change, pivot_points):
    if chart_data is not None:
        chart = StreamlitChart(height=525)
        change_color = '#00ff55' if daily_change >= 0 else '#ed4807'
        chart.layout(background_color='#1E222D', text_color='#FFFFFF', font_size=12)
        chart.candle_style(up_color='#00ff55', down_color='#ed4807', wick_up_color='#00ff55', wick_down_color='#ed4807')
        chart.crosshair(mode='normal')
        chart.time_scale(right_offset=5, min_bar_spacing=5)
        
        # Adding pivot line if available
        if pivot_points:
            chart.horizontal_line(pivot_points['P'], color='#39FF14', width=1)
        
        # Display in a container with a title
        st.markdown(f"<h3 style='color:#FFEB3B'>{name} ({symbol})</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#AAB2BD;'>Current Price: ${current_price:.2f} | Volume: {format_volume(volume)} | Change: <span style='color:{change_color}'>{daily_change:.2f}%</span></p>", unsafe_allow_html=True)
        chart.set(chart_data)
        chart.load()
    else:
        st.warning("No data available.")

# Main content with loading animation and dynamic layout
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

# Navigation buttons in footer
st.markdown("<hr>", unsafe_allow_html=True)
with st.container():
    cols = st.columns(5)
    if cols[0].button("Previous", disabled=(current_page == 1)):
        st.session_state.current_page -= 1

    cols[2].markdown(f"<div style='text-align: center; padding: 10px;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)

    if cols[4].button("Next", disabled=(current_page == total_pages)):
        st.session_state.current_page += 1
