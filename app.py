from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import os

app = Flask(__name__)

# Ensure static/charts directory exists
os.makedirs("static/charts", exist_ok=True)

# Helper functions
def fetch_stock_data(ticker, period="1mo", interval="1d"):
    try:
        stock_data = yf.download(ticker, period=period, interval=interval)
        if stock_data.empty:
            return None, "No data available for the given ticker."
        stock_data.reset_index(inplace=True)
        return stock_data, None
    except Exception as e:
        return None, str(e)

def calculate_indicators(data):
    try:
        data['SMA_10'] = SMAIndicator(data['Close'], window=10).sma_indicator()
        data['EMA_20'] = EMAIndicator(data['Close'], window=20).ema_indicator()
        data['RSI'] = RSIIndicator(data['Close'], window=14).rsi()
        return data
    except Exception as e:
        raise ValueError(f"Error calculating indicators: {e}")

def generate_chart(data, ticker):
    try:
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.6, 0.2, 0.2],
            vertical_spacing=0.05,
            subplot_titles=(f"{ticker} Stock Price and Volume", "RSI")
        )

        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=data['Date'],
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="Candlestick",
            increasing_line_color='green',
            decreasing_line_color='red'
        ), row=1, col=1)

        # Add SMA and EMA
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data['SMA_10'],
            mode='lines',
            name='10-Day SMA',
            line=dict(color='orange')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data['EMA_20'],
            mode='lines',
            name='20-Day EMA',
            line=dict(color='blue')
        ), row=1, col=1)

        # Add Volume bars
        fig.add_trace(go.Bar(
            x=data['Date'],
            y=data['Volume'],
            name='Volume',
            marker_color='rgba(128,128,128,0.5)'
        ), row=2, col=1)

        # Add RSI
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color='purple')
        ), row=3, col=1)

        # Add RSI thresholds
        fig.add_trace(go.Scatter(
            x=data['Date'], y=[70] * len(data),
            mode='lines',
            name='Overbought (70)',
            line=dict(color='red', dash='dot')
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=data['Date'], y=[30] * len(data),
            mode='lines',
            name='Oversold (30)',
            line=dict(color='green', dash='dot')
        ), row=3, col=1)

        # Style and layout
        fig.update_layout(
            title=f"{ticker} Stock Analysis",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_white",
            height=None,  # Remove fixed height to make chart responsive
            autosize=True,
            legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.2)
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)

        # Save chart
        chart_path = f"static/charts/{ticker}_chart.html"
        fig.write_html(chart_path)
        return chart_path
    except Exception as e:
        raise ValueError(f"Error generating chart: {e}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form.get('ticker')
    period = request.form.get('period', '1mo')
    interval = request.form.get('interval', '1d')

    if not ticker:
        return jsonify({"error": "Ticker symbol is required."}), 400

    stock_data, error = fetch_stock_data(ticker, period, interval)
    if error:
        return jsonify({"error": error}), 500

    try:
        stock_data = calculate_indicators(stock_data)
        chart_path = generate_chart(stock_data, ticker)
        return jsonify({"chart_url": chart_path, "success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
