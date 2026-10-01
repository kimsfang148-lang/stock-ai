import plotly.graph_objects as go
from plotly.subplots import make_subplots

def price_chart(df, ticker):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        row_heights=[0.55,0.22,0.23])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    for col in ["MA20","MA60","MA200"]:
        if col in df:
            fig.add_trace(go.Scatter(x=df.index,y=df[col],name=col),row=1,col=1)
    if "BB_UPPER" in df:
        fig.add_trace(go.Scatter(x=df.index,y=df["BB_UPPER"],name="BB Upper",line=dict(dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["BB_LOWER"],name="BB Lower",line=dict(dash="dot")),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI"),row=2,col=1)
    fig.add_hline(y=70,row=2,col=1,line_dash="dot")
    fig.add_hline(y=30,row=2,col=1,line_dash="dot")
    fig.add_trace(go.Bar(x=df.index,y=df["MACD_HIST"],name="MACD Hist"),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["MACD"],name="MACD"),row=3,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["MACD_SIGNAL"],name="Signal"),row=3,col=1)
    fig.update_layout(title=f"{ticker} 기술적 분석", height=850, xaxis_rangeslider_visible=False)
    return fig
