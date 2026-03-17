import streamlit as st
import plotly.express as px

from storage import init_db
from analytics_engine import (
    calculate_summary,
    build_equity_curve,
    by_ticker_stats,
    by_signal_stats,
    recent_closed_trades,
    recent_open_trades,
    load_signals,
    load_risk_events,
    load_feed_audit,
    get_asset_ranking,
    get_capital_allocation_table,
    get_trade_intelligence
)

init_db()

st.set_page_config(
    page_title="Shark V10 Dashboard",
    layout="wide"
)

st.title("🦈 Shark V10 Dashboard")
st.caption("Session + Volatility + Trade Intelligence + Adaptive Capital Allocation + Feed Audit + Final Gate")

summary = calculate_summary()
equity_df = build_equity_curve()
ticker_df = by_ticker_stats()
signal_df = by_signal_stats()
closed_df = recent_closed_trades(limit=20)
open_df = recent_open_trades()
signals_df = load_signals(limit=20)
risk_df = load_risk_events(limit=20)
feed_df = load_feed_audit(limit=30)
ranking_df = get_asset_ranking()
allocation_df = get_capital_allocation_table()
intelligence_df = get_trade_intelligence()

row1 = st.columns(4)
row1[0].metric("Capital actual", f"{summary['capital_actual']:.2f}")
row1[1].metric("PnL total", f"{summary['total_pnl']:.2f}")
row1[2].metric("Profit Factor", f"{summary['profit_factor']:.2f}")
row1[3].metric("Max Drawdown", f"{summary['max_drawdown']:.2f}")

row2 = st.columns(4)
row2[0].metric("Trades cerrados", f"{summary['trades_cerrados']}")
row2[1].metric("Trades abiertos", f"{summary['trades_abiertos']}")
row2[2].metric("Winrate", f"{summary['winrate']:.2f}%")
row2[3].metric("Avg Trade", f"{summary['avg_trade']:.2f}")

row3 = st.columns(6)
row3[0].metric("Bloqueos por riesgo", f"{summary['risk_blocks']}")
row3[1].metric("Bloqueos por AI", f"{summary['ai_blocks']}")
row3[2].metric("Bloqueos por inteligencia", f"{summary['intel_blocks']}")
row3[3].metric("Bloqueos por sesión", f"{summary['session_blocks']}")
row3[4].metric("Bloqueos por volatilidad", f"{summary['volatility_blocks']}")
row3[5].metric("Bloqueos finales", f"{summary['final_blocks']}")

st.divider()

st.subheader("Equity Curve")
if not equity_df.empty:
    fig_equity = px.line(
        equity_df,
        x="step",
        y="equity",
        title="Evolución del capital"
    )
    st.plotly_chart(fig_equity, use_container_width=True)
else:
    st.info("Todavía no hay equity curve disponible.")

st.divider()

left_alloc, right_rank = st.columns(2)

with left_alloc:
    st.subheader("Adaptive Capital Allocation")
    if not allocation_df.empty:
        st.dataframe(allocation_df, use_container_width=True)
    else:
        st.info("No hay asignación adaptativa disponible.")

with right_rank:
    st.subheader("Asset Ranking")
    if not ranking_df.empty:
        st.dataframe(ranking_df, use_container_width=True)
    else:
        st.info("No hay ranking disponible.")

st.divider()

st.subheader("Trade Intelligence Engine")
if not intelligence_df.empty:
    st.dataframe(intelligence_df, use_container_width=True)
else:
    st.info("Todavía no hay datos suficientes para trade intelligence.")

st.divider()

st.subheader("Feed Audit")
if not feed_df.empty:
    st.dataframe(feed_df, use_container_width=True)
else:
    st.info("Todavía no hay auditoría de feed.")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Performance por ticker")
    if not ticker_df.empty:
        st.dataframe(ticker_df, use_container_width=True)
    else:
        st.info("Todavía no hay trades cerrados por ticker.")

with right:
    st.subheader("Performance por señal")
    if not signal_df.empty:
        st.dataframe(signal_df, use_container_width=True)
    else:
        st.info("Todavía no hay trades cerrados por señal.")

st.divider()

col_open, col_closed = st.columns(2)

with col_open:
    st.subheader("Trades abiertos")
    if not open_df.empty:
        st.dataframe(open_df, use_container_width=True)
    else:
        st.info("No hay trades abiertos.")

with col_closed:
    st.subheader("Últimos trades cerrados")
    if not closed_df.empty:
        st.dataframe(closed_df, use_container_width=True)
    else:
        st.info("No hay trades cerrados todavía.")

st.divider()

col_signals, col_risk = st.columns(2)

with col_signals:
    st.subheader("Últimas señales registradas")
    if not signals_df.empty:
        st.dataframe(signals_df, use_container_width=True)
    else:
        st.info("No hay señales guardadas todavía.")

with col_risk:
    st.subheader("Últimos eventos de riesgo / AI")
    if not risk_df.empty:
        st.dataframe(risk_df, use_container_width=True)
    else:
        st.info("No hay eventos de riesgo todavía.")

st.divider()
st.caption("Refresca el navegador para actualizar datos.")