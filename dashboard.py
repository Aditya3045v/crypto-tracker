import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="Pro Crypto Tracker | Bull Run Edition", layout="wide", initial_sidebar_state="collapsed")
CONTRACT_ADDRESS = "0x1Bdf71EDe1a4777dB1EebE7232BcdA20d6FC1610"
REFRESH_RATE = 2  # Safe rapid refresh rate

# --- DATA FETCHING ---
def fetch_token_data(contract):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{contract}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data and data.get('pairs'):
            # Get the pair with highest liquidity
            best_pair = sorted(data['pairs'], key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]
            return best_pair
    except Exception:
        pass
    return None

# --- ADVANCED PREDICTION ENGINE ---
def calculate_momentum_score(changes, txns):
    """Calculates a volume-weighted momentum score to predict short-term movement"""
    score = 0
    weights = {'m5': 0.5, 'h1': 0.3, 'h6': 0.15, 'h24': 0.05} # Heavily weight the last 5m to 1h for a live bull run
    
    for tf, weight in weights.items():
        change = changes.get(tf, 0)
        tf_txns = txns.get(tf, {})
        buys = tf_txns.get('buys', 0)
        sells = tf_txns.get('sells', 0)
        total_txns = buys + sells
        
        # Buy pressure multiplier (1.0 is neutral, >1.0 is bullish)
        buy_pressure = (buys / sells) if sells > 0 else 1.5
        if total_txns < 5: buy_pressure = 1.0 # Ignore low volume noise
        
        score += (change * weight * buy_pressure)
        
    return score

def generate_advanced_forecast(price_usd, changes, momentum_score):
    """Reconstructs past chart and forecasts future based on momentum"""
    # 1. Reconstruct Past Prices (Since DexScreener API only gives current snapshot)
    past_times = [
        datetime.now() - timedelta(hours=24),
        datetime.now() - timedelta(hours=6),
        datetime.now() - timedelta(hours=1),
        datetime.now() - timedelta(minutes=5),
        datetime.now()
    ]
    
    past_prices = [
        price_usd / (1 + (changes.get('h24', 0) / 100)),
        price_usd / (1 + (changes.get('h6', 0) / 100)),
        price_usd / (1 + (changes.get('h1', 0) / 100)),
        price_usd / (1 + (changes.get('m5', 0) / 100)),
        price_usd
    ]

    # 2. Forecast Future Prices
    future_times = []
    future_prices = []
    
    # Dampen momentum for realistic curve (prevent infinite exponential growth)
    hourly_growth_rate = max(min(momentum_score / 100, 0.20), -0.20) # Cap at +/- 20% per hour
    
    current_proj_price = price_usd
    for i in range(1, 13): # Project next 12 hours
        future_times.append(datetime.now() + timedelta(hours=i))
        # Add slight decay to momentum so the curve flattens out realistically
        current_proj_price = current_proj_price * (1 + (hourly_growth_rate * (0.85 ** i)))
        future_prices.append(current_proj_price)

    return past_times, past_prices, future_times, future_prices

# --- UI RENDER ---
placeholder = st.empty()

with placeholder.container():
    data = fetch_token_data(CONTRACT_ADDRESS)
    
    if data:
        # --- PARSE DATA ---
        token_name = data['baseToken']['symbol']
        dex_name = data.get('dexId', 'DEX').upper()
        price_usd = float(data.get('priceUsd', 0))
        liquidity = data.get('liquidity', {}).get('usd', 0)
        fdv = data.get('fdv', 0)
        
        volume = data.get('volume', {})
        txns = data.get('txns', {})
        changes = data.get('priceChange', {})
        
        momentum = calculate_momentum_score(changes, txns)
        
        # --- HEADER ---
        st.markdown(f"<h1>🚀 {token_name} / USD Live Command Center</h1>", unsafe_allow_html=True)
        st.caption(f"Contract: `{CONTRACT_ADDRESS}` | Trading on: **{dex_name}** | Auto-refresh: **{REFRESH_RATE}s**")
        st.markdown("---")
        
        # --- ROW 1: CORE METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Price", f"${price_usd:,.6f}", f"{changes.get('m5', 0):.2f}% (Last 5m)")
        c2.metric("Market Cap (FDV)", f"${fdv:,.0f}", f"{changes.get('h24', 0):.2f}% (24h)")
        
        liq_mc_ratio = (liquidity / fdv * 100) if fdv > 0 else 0
        c3.metric("Liquidity", f"${liquidity:,.0f}", f"Health: {liq_mc_ratio:.1f}% of MC")
        c4.metric("24h Volume", f"${volume.get('h24', 0):,.0f}")
        
        # --- ROW 2: TIME-FRAME ANALYSIS (BUYS VS SELLS) ---
        st.markdown("### 📊 Multi-Timeframe Battle (Buyers vs Sellers)")
        t1, t2, t3, t4 = st.columns(4)
        
        timeframes = [("5 Min", "m5", t1), ("1 Hour", "h1", t2), ("6 Hours", "h6", t3), ("24 Hours", "h24", t4)]
        
        for label, tf, col in timeframes:
            with col:
                st.markdown(f"**{label} Window**")
                tf_buys = txns.get(tf, {}).get('buys', 0)
                tf_sells = txns.get(tf, {}).get('sells', 0)
                tf_vol = volume.get(tf, 0)
                tf_change = changes.get(tf, 0)
                
                total_tx = tf_buys + tf_sells
                buy_pct = (tf_buys / total_tx) if total_tx > 0 else 0.5
                
                # Dynamic coloring for price change
                color = "green" if tf_change >= 0 else "red"
                st.markdown(f"Price Change: <span style='color:{color}; font-weight:bold;'>{tf_change}%</span>", unsafe_allow_html=True)
                st.write(f"Volume: ${tf_vol:,.0f}")
                
                st.progress(buy_pct)
                st.caption(f"🟢 {tf_buys} Buys | 🔴 {tf_sells} Sells")

        st.markdown("---")
        
        # --- ROW 3: AI PREDICTION & CHARTS ---
        col_chart, col_ai = st.columns([3, 1])
        
        with col_ai:
            st.markdown("### 🧠 AI Trading Engine")
            
            # Complex Logic Tree for Recommendation
            m5_c, h1_c = changes.get('m5', 0), changes.get('h1', 0)
            m5_b, m5_s = txns.get('m5', {}).get('buys', 0), txns.get('m5', {}).get('sells', 0)
            
            st.metric("Momentum Score", f"{momentum:.2f}", "Bullish" if momentum > 0 else "Bearish")
            
            st.markdown("#### Action Required:")
            if m5_c > 2 and h1_c > 5 and m5_b > m5_s:
                st.success("🔥 STRONG BUY\n\nMassive short-term volume pushing price up. Ride the momentum.")
            elif m5_c < -2 and h1_c > 5 and m5_b > (m5_s * 1.2):
                st.success("🟢 BUY THE DIP\n\n1h trend is strictly Bullish, but we are in a 5m pullback with buyers accumulating.")
            elif m5_c > 5 and momentum > 20:
                st.warning("⚠️ CAUTION (HOLD)\n\nToken is pumping hard. High risk of immediate taking-profit pullback.")
            elif m5_c < -3 and m5_s > m5_b * 1.5:
                st.error("🔴 SELL / SHORT\n\nSudden spike in sell pressure in the last 5 minutes. Trend reversing.")
            else:
                st.info("🟡 ACCUMULATE / HOLD\n\nMarket is deciding the next leg up/down. Choppy action.")
                
            st.markdown("#### Market Context:")
            if liq_mc_ratio < 2:
                st.warning("Low Liquidity relative to Market Cap. Prone to extreme volatility / rug risk.")
            else:
                st.success("Healthy Liquidity pool relative to Market Cap.")

        with col_chart:
            st.markdown("### 📈 Trajectory & Forecast Chart")
            past_t, past_p, fut_t, fut_p = generate_advanced_forecast(price_usd, changes, momentum)
            
            fig = go.Figure()
            
            # Historical Line
            fig.add_trace(go.Scatter(
                x=past_t, y=past_p,
                mode='lines+markers',
                name='Historical Path',
                line=dict(color='#00ff88', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 136, 0.1)'
            ))
            
            # Projection Line
            fig.add_trace(go.Scatter(
                x=[past_t[-1]] + fut_t, # Connect NOW to future
                y=[past_p[-1]] + fut_p,
                mode='lines',
                name='AI Forecast (12h)',
                line=dict(color='#ff00ff', width=3, dash='dash'),
            ))

            fig.update_layout(
                template="plotly_dark",
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Timeline",
                yaxis_title="Price (USD)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.spinner("Establishing secure connection to Blockchain DEX nodes...")

# Safe 2-second sleep to prevent IP bans
time.sleep(REFRESH_RATE)
st.rerun()