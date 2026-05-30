"""Streamlit dashboard sections for MIS results."""

import pandas as pd
import streamlit as st

from mis_core import state


def _inr(amount):
    return f"₹ {amount:,.2f}"


def render_mis1():
    st.subheader("MIS 1 — Active RD accounts & instalment")
    df = state.df_snap
    if df is None or df.empty:
        st.warning("No MIS 1 data available.")
        return
    c1, c2 = st.columns(2)
    total_inst = df["Instalment"].sum() if "Instalment" in df.columns else 0
    c1.metric("Total account records", f"{len(df):,}")
    c2.metric("Total instalment", _inr(total_inst))
    if "Company" in df.columns and "Instalment" in df.columns:
        summary = (
            df.groupby("Company")
            .agg(Accounts=("Instalment", "count"), Total_Instalment=("Instalment", "sum"))
            .reset_index()
            .sort_values("Total_Instalment", ascending=False)
        )
        summary["Total_Instalment"] = summary["Total_Instalment"].map(_inr)
        st.dataframe(summary, use_container_width=True, hide_index=True)


def render_mis2():
    st.subheader("MIS 2 — Monthly closing report")
    df = state.df_payment
    if df is None or df.empty:
        st.warning("No MIS 2 data available.")
        return
    c1, c2 = st.columns(2)
    total_princ = df["Principal"].sum() if "Principal" in df.columns else 0
    c1.metric("Total transactions", f"{len(df):,}")
    c2.metric("Total principal collected", _inr(total_princ))
    if "Company" in df.columns and "Principal" in df.columns:
        summary = (
            df.groupby("Company")
            .agg(Transactions=("Principal", "count"), Total_Principal=("Principal", "sum"))
            .reset_index()
            .sort_values("Total_Principal", ascending=False)
        )
        summary["Total_Principal"] = summary["Total_Principal"].map(_inr)
        st.dataframe(summary, use_container_width=True, hide_index=True)


def render_mis3():
    st.subheader("MIS 3 — Net for the month (MIS 1 instalment − MIS 2 amount)")
    df_snap = state.df_snap
    df_pay = state.df_payment
    if (df_snap is None or df_snap.empty) and (df_pay is None or df_pay.empty):
        st.warning("Insufficient data for net calculation.")
        return
    inst_total = (
        df_snap["Instalment"].sum()
        if df_snap is not None and "Instalment" in df_snap.columns
        else 0
    )
    amt_total = (
        df_pay["Amount"].sum()
        if df_pay is not None and "Amount" in df_pay.columns
        else 0
    )
    net_total = inst_total - amt_total
    c1, c2, c3 = st.columns(3)
    c1.metric("MIS 1 instalment", _inr(inst_total))
    c2.metric("MIS 2 amount", _inr(amt_total))
    c3.metric("Net", _inr(net_total), delta=f"{net_total:,.2f}")

    co_inst, co_amt = {}, {}
    if df_snap is not None and "Company" in df_snap.columns:
        for co, grp in df_snap.groupby("Company"):
            co_inst[co] = grp["Instalment"].sum()
    if df_pay is not None and "Company" in df_pay.columns:
        for co, grp in df_pay.groupby("Company"):
            co_amt[co] = grp["Amount"].sum()
    rows = []
    for co in sorted(set(co_inst) | set(co_amt)):
        inst = co_inst.get(co, 0)
        amt = co_amt.get(co, 0)
        rows.append(
            {
                "Company": co,
                "Instalment": inst,
                "Amount": amt,
                "Net": inst - amt,
            }
        )
    if rows:
        net_df = pd.DataFrame(rows).sort_values("Net", ascending=False)
        net_df["Instalment"] = net_df["Instalment"].map(_inr)
        net_df["Amount"] = net_df["Amount"].map(_inr)
        net_df["Net"] = net_df["Net"].map(_inr)
        st.dataframe(net_df, use_container_width=True, hide_index=True)


def render_mis4():
    d = state.dates
    title = f"MIS 4 — Deposit outstanding ({d.prev_outstanding} vs {d.to_date})"
    st.subheader(title)
    if state.out_prev is None and state.out_today is None:
        st.warning("Outstanding data unavailable.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Outstanding {d.prev_outstanding}", _inr(state.out_prev or 0))
    c2.metric(f"Outstanding {d.to_date}", _inr(state.out_today or 0))
    diff = state.out_diff
    c3.metric("Movement", _inr(diff or 0) if diff is not None else "N/A")

    prev_co = state.out_prev_co or {}
    today_co = state.out_today_co or {}
    rows = []
    for co in sorted(set(prev_co) | set(today_co)):
        p, t = prev_co.get(co, 0), today_co.get(co, 0)
        rows.append({"Company": co, "Previous": p, "Today": t, "Movement": t - p})
    if rows:
        out_df = pd.DataFrame(rows).sort_values("Today", ascending=False)
        for col in ("Previous", "Today", "Movement"):
            out_df[col] = out_df[col].map(lambda x: f"₹ {x:,.0f}")
        st.dataframe(out_df, use_container_width=True, hide_index=True)


def render_full_dashboard():
    render_mis1()
    st.divider()
    render_mis2()
    st.divider()
    render_mis3()
    st.divider()
    render_mis4()
