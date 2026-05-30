"""
Sangeeth MIS — Streamlit web app (shareable via Streamlit Community Cloud).

Run locally:
  streamlit run app.py

Deploy: push to GitHub, then https://share.streamlit.io → New app → this repo, main file app.py
"""

from __future__ import annotations

import os
import subprocess
import sys

import streamlit as st

import mis_core as mc
from mis_views import render_full_dashboard


def apply_secrets():
    """Map Streamlit secrets / sidebar inputs into environment for mis_core."""
    secrets = getattr(st, "secrets", {})
    for key in ("SANGEETH_BASE_URL", "SANGEETH_USERNAME", "SANGEETH_PASSWORD"):
        if key in secrets:
            os.environ[key] = str(secrets[key])
    mc.reload_config()


@st.cache_resource(show_spinner="Installing Playwright Chromium (first run only)...")
def ensure_playwright_browser():
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            timeout=600,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return str(exc)


st.set_page_config(
    page_title="Sangeeth MIS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_secrets()

st.title("Sangeeth MIS Workspace")
st.caption(
    "RD active accounts, monthly closing, net for the month, and deposit outstanding comparison."
)

with st.sidebar:
    st.header("Connection")
    st.text_input(
        "Base URL",
        value=os.environ.get("SANGEETH_BASE_URL", mc.BASE_URL),
        key="base_url",
        help="Sangeeth portal URL (must be reachable from this machine).",
    )
    st.text_input(
        "Username",
        value=os.environ.get("SANGEETH_USERNAME", ""),
        key="username",
        type="default",
    )
    st.text_input(
        "Password",
        value=os.environ.get("SANGEETH_PASSWORD", ""),
        key="password",
        type="password",
    )
    if st.button("Apply credentials", use_container_width=True):
        os.environ["SANGEETH_BASE_URL"] = st.session_state.base_url.strip()
        os.environ["SANGEETH_USERNAME"] = st.session_state.username.strip()
        os.environ["SANGEETH_PASSWORD"] = st.session_state.password
        apply_secrets()
        st.success("Credentials updated for this session.")

    st.divider()
    st.markdown(
        "**Share this app:** deploy on [Streamlit Community Cloud](https://share.streamlit.io) "
        "from your GitHub repo (`app.py`). Add secrets there — see `.streamlit/secrets.toml.example`."
    )

st.warning(
    "Automation needs network access to the Sangeeth server. "
    "Streamlit Cloud runs on the public internet; private/office IPs (e.g. `202.21.37.x`) "
    "usually only work when you run `streamlit run app.py` on a PC inside that network."
)

defaults = mc.default_mis_dates()
st.subheader("Report dates")
c1, c2 = st.columns(2)
with c1:
    to_date = st.text_input("To date (MIS 1/2 end, MIS 4 today)", defaults["to_date"])
    from_month = st.text_input("From date — monthly (MIS 1 & 2)", defaults["from_date_month"])
with c2:
    from_details = st.text_input("From date — deposit details (MIS 2)", defaults["from_date_details"])
    prev_out = st.text_input("Previous outstanding as-on (MIS 4)", defaults["prev_outstanding"])

generate = st.button("Generate MIS", type="primary", use_container_width=True)

if generate:
    apply_secrets()
    os.environ["SANGEETH_BASE_URL"] = st.session_state.get("base_url", mc.BASE_URL).strip()
    os.environ["SANGEETH_USERNAME"] = st.session_state.get("username", "")
    os.environ["SANGEETH_PASSWORD"] = st.session_state.get("password", "")
    apply_secrets()

    if not mc.credentials_configured():
        st.error("Enter username and password in the sidebar (or set Streamlit secrets).")
    else:
        try:
            dates = mc.validate_dates(to_date, from_month, from_details, prev_out)
        except ValueError as err:
            st.error(str(err))
        else:
            browser_msg = ensure_playwright_browser()
            if browser_msg is not True:
                st.error(f"Playwright browser install failed: {browser_msg}")
            else:
                mc.state.prepare_run(dates)
                with st.spinner("Running MIS pipeline — this may take several minutes..."):
                    mc.background_workflow()
                if mc.state.is_done and not mc.state.error_msg:
                    st.session_state["mis_ready"] = True
                elif mc.state.error_msg:
                    st.session_state.pop("mis_ready", None)

if st.session_state.get("mis_ready") and mc.state.is_done:
    st.divider()
    render_full_dashboard()

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if mc.state.df_snap is not None and not mc.state.df_snap.empty:
            st.download_button(
                "Download MIS 1 (CSV)",
                mc.state.df_snap.to_csv(index=False).encode("utf-8"),
                file_name=f"mis1_{mc.state.dates.file_suffix}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with col_b:
        if mc.state.df_payment is not None and not mc.state.df_payment.empty:
            st.download_button(
                "Download MIS 2 (CSV)",
                mc.state.df_payment.to_csv(index=False).encode("utf-8"),
                file_name=f"mis2_{mc.state.dates.file_suffix}.csv",
                mime="text/csv",
                use_container_width=True,
            )
