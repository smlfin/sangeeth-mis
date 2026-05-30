# ============================================================
#  Sangeeth MIS Workspace Controller — Unified Dashboard
#
#  MIS 1 : RD Active Accounts & Instalment
#  MIS 2 : Monthly Closing Report (RD Payment Collections)
#  MIS 3 : Net for the Month  (MIS 1 Instalment − MIS 2 Amount)
#  MIS 4 : Deposit Outstanding Comparison (prev-month-end vs today)
#
#  All automation runs headless in background threads.
#  User sees only the Tkinter dashboard window.
#
#  HOW TO RUN:
#    python mis_dashboard.py
# ============================================================

from playwright.sync_api import sync_playwright
from datetime import datetime, date
from calendar import monthrange
import pandas as pd
import tkinter as tk
import threading
import re
import os


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

BASE_URL = os.environ.get("SANGEETH_BASE_URL", "http://202.21.37.156/Sangeeth/")
USERNAME = os.environ.get("SANGEETH_USERNAME", "")
PASSWORD = os.environ.get("SANGEETH_PASSWORD", "")


def reload_config():
    """Reload connection settings from environment (after Streamlit secrets / sidebar)."""
    global BASE_URL, USERNAME, PASSWORD
    BASE_URL = os.environ.get("SANGEETH_BASE_URL", BASE_URL)
    USERNAME = os.environ.get("SANGEETH_USERNAME", "")
    PASSWORD = os.environ.get("SANGEETH_PASSWORD", "")

def _default_to_date():
    return datetime.today().date()


def prev_month_end(d):
    if d.month == 1:
        return date(d.year - 1, 12, 31)
    return date(d.year, d.month - 1, monthrange(d.year, d.month - 1)[1])


def format_dmY(d):
    return d.strftime("%d/%m/%Y")


def parse_dmY(s):
    """Parse DD/MM/YYYY; raises ValueError on invalid input."""
    return datetime.strptime(s.strip(), "%d/%m/%Y").date()


def default_mis_dates():
    to_d = _default_to_date()
    return {
        "to_date": format_dmY(to_d),
        "from_date_month": format_dmY(to_d.replace(day=1)),
        "from_date_details": "01/01/2020",
        "prev_outstanding": format_dmY(prev_month_end(to_d)),
    }


class MisDateConfig:
    def __init__(self, to_date, from_date_month, from_date_details, prev_outstanding):
        self.to_date = to_date
        self.from_date_month = from_date_month
        self.from_date_details = from_date_details
        self.prev_outstanding = prev_outstanding

    @property
    def file_suffix(self):
        return parse_dmY(self.to_date).strftime("%Y%m%d")


# ─────────────────────────────────────────────
#  SHARED STATE
# ─────────────────────────────────────────────

class AutomationState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.status      = "Set report dates and click Generate MIS."
        self.is_done     = False
        self.error_msg   = None
        self.running     = False
        self.dates       = None
        self.df_snap     = None
        self.df_payment  = None
        self.out_prev    = None
        self.out_today   = None
        self.out_diff    = None
        self.out_prev_co  = {}
        self.out_today_co = {}

    def prepare_run(self, dates):
        self.reset()
        self.dates = dates
        self.running = True
        self.status = "Initializing system elements..."

state = AutomationState()


# ─────────────────────────────────────────────
#  SHARED HELPERS — company normalisation
# ─────────────────────────────────────────────

def normalise_company(raw):
    s = str(raw).strip()
    if not s or s.lower() == "nan":
        return "Unknown"
    if "VFL" in s.upper():
        return "VFL"
    if "SML" in s.upper():
        return "SML"
    if re.match(r"^\d+", s):
        return "SNL"
    return "SNL"


def split_staff_parts(name):
    if pd.isna(name) or str(name).strip() == "":
        return "", "", ""
    parts = [p.strip() for p in str(name).split("-")]
    return (
        parts[0] if len(parts) > 0 else "",
        parts[1] if len(parts) > 1 else "",
        parts[2] if len(parts) > 2 else "",
    )


# ─────────────────────────────────────────────
#  SHARED HELPERS — form interaction
# ─────────────────────────────────────────────

def fill_date(page, label_text, date_value):
    try:
        input_id = page.locator(f"label:has-text('{label_text}')").first.get_attribute("for")
        field = (page.locator(f"#{input_id}") if input_id
                 else page.locator(f"label:has-text('{label_text}')").locator("..").locator("input").first)
        field.evaluate(
            "(el, val) => { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }",
            date_value)
        field.click(click_count=3)
        field.type(date_value)
    except Exception:
        pass


def fill_ason_date(page, date_value):
    try:
        page.evaluate(
            "(val) => {"
            "  const inputs = Array.from(document.querySelectorAll('input[type=text]'));"
            "  if (inputs[0]) {"
            "    inputs[0].value = val;"
            "    inputs[0].dispatchEvent(new Event('change', {bubbles:true}));"
            "  }"
            "}",
            date_value)
    except Exception:
        pass


def select_dropdown(page, label_text, value):
    try:
        input_id = page.locator(f"label:has-text('{label_text}')").first.get_attribute("for")
        if input_id:
            page.select_option(f"#{input_id}", label=value)
        else:
            page.locator(f"label:has-text('{label_text}')").locator("xpath=..").locator("select").first.select_option(label=value)
    except Exception:
        pass


# ─────────────────────────────────────────────
#  SHARED HELPERS — export & download
# ─────────────────────────────────────────────

def locate_export_select(report_page):
    for sel in report_page.locator("select").all():
        try:
            opts = sel.evaluate("el => Array.from(el.options).map(o => o.text)")
            if any("CSV" in o or "Excel" in o for o in opts):
                return sel
        except Exception:
            pass
    for frame in report_page.frames:
        if frame == report_page.main_frame:
            continue
        try:
            for sel in frame.locator("select").all():
                try:
                    opts = sel.evaluate("el => Array.from(el.options).map(o => o.text)")
                    if any("CSV" in o or "Excel" in o for o in opts):
                        return sel
                except Exception:
                    pass
        except Exception:
            pass
    return None


def generate_and_download(context, page, temp_path, export_format="Excel 97-2003"):
    try:
        with context.expect_page(timeout=60000) as npi:
            page.click(
                "button:has-text('Generate'), input[value='Generate'], button:has-text('View Report')",
                timeout=15000)
        rp = npi.value
        rp.wait_for_load_state("networkidle", timeout=60000)
        export_sel = locate_export_select(rp)
        if not export_sel:
            rp.close()
            return False
        export_sel.select_option(label=export_format)
        with rp.expect_download(timeout=90000) as dl_info:
            rp.locator("a[id*='Export'], input[id*='Export'], button[id*='Export']").first.click(
                timeout=10000, no_wait_after=True)
        dl_info.value.save_as(temp_path)
        rp.close()
        return True
    except Exception as e:
        state.status = f"Download error: {e}"
        return False


# ─────────────────────────────────────────────
#  SHARED HELPERS — XLS parsing
# ─────────────────────────────────────────────

def read_xls_data_rows(filepath, repo_name):
    try:
        df = pd.read_excel(filepath, engine="xlrd", header=None, dtype=str)
    except Exception:
        return None

    if repo_name == "NCDPayment":
        headers = [
            "Sl_No", "Col_Blank_1", "Date", "Deposit_No", "Share_Name",
            "Principal", "Interest", "Col_Blank_2", "TDS", "Total_Amount",
            "Int_Accrued", "PAN_No", "TDS_Type", "Pmt_Mode"
        ]
    elif repo_name == "NCDDetails":
        headers = [
            "Sl_No", "Share_Name", "Address", "Col_Blank_1", "Pan_No",
            "Dep_No", "Date", "Amount", "Period", "Scheme", "Col_Blank_2",
            "Int_Pct", "Agent", "TDS"
        ]
    else:
        return None

    df.columns = headers[:len(df.columns)]

    def is_int(val):
        try:
            int(str(val).strip().split(".")[0])
            return True
        except Exception:
            return False

    df_data = df[df["Sl_No"].apply(is_int)].copy().reset_index(drop=True)
    df_data = df_data.drop(columns=[c for c in df_data.columns if "Blank" in c], errors="ignore")
    return df_data


# ─────────────────────────────────────────────
#  SHARED HELPERS — session management
# ─────────────────────────────────────────────

def ensure_logged_in(context):
    page = context.new_page()
    try:
        page.goto(BASE_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        if page.locator("input[type='password']").is_visible():
            page.fill("input[type='text'], input[name*='user' i], input[id*='user' i]", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            page.click(
                "input[type='submit'], button[type='submit'], "
                "button:has-text('Login'), button:has-text('Sign In')")
            page.wait_for_load_state("networkidle")
    finally:
        page.close()


# ─────────────────────────────────────────────
#  MIS 1 — ACTIVE RD INSTALMENT
# ─────────────────────────────────────────────

SNAP_HEADERS = [
    "Branch_Total", "Branch", "Branch_Amount", "Product",
    "Amount", "Sl_No", "Account_No", "Date", "Instalment",
    "Scheme", "Address", "PAN", "Customer_Name", "Duration",
    "Rate", "Staff_Name", "Col17", "Col18", "Mobile"
]

def scrape_mis1(context):
    state.status = "MIS 1: Loading active RD account data..."
    ensure_logged_in(context)
    page = context.new_page()
    page.goto(f"{BASE_URL}Reports/ReportOptions?repo_name=NCDDetails", timeout=30000)
    page.wait_for_load_state("networkidle")
    d = state.dates
    fill_date(page, "From Date", d.from_date_month)
    fill_date(page, "To Date",   d.to_date)
    select_dropdown(page, "Branch",        "All Branch")
    select_dropdown(page, "Staff Members", "All")
    select_dropdown(page, "Master",        "RD")
    select_dropdown(page, "Scheme",        "All")
    page.wait_for_timeout(300)

    temp = f"temp_mis1_{d.file_suffix}.csv"
    ok = False
    try:
        with context.expect_page(timeout=60000) as npi:
            page.click(
                "button:has-text('Generate'), input[value='Generate'], button:has-text('View Report')",
                timeout=15000)
        rp = npi.value
        rp.wait_for_load_state("networkidle", timeout=60000)
        state.status = "MIS 1: Exporting report data..."
        export_sel = locate_export_select(rp)
        if export_sel:
            export_sel.select_option(label="CSV (comma delimited)")
            with rp.expect_download(timeout=60000) as dl_info:
                rp.click("a[id*='Export'], input[id*='Export'], button[id*='Export']", timeout=10000)
            dl_info.value.save_as(temp)
            ok = True
        rp.close()
    except Exception as e:
        state.status = f"MIS 1 export failed: {e}"
    finally:
        page.close()

    if not ok:
        return

    try:
        state.status = "MIS 1: Processing downloaded data..."
        df = pd.read_csv(temp, header=None, dtype=str)
        df.columns = (SNAP_HEADERS[:len(df.columns)] if len(SNAP_HEADERS) == len(df.columns)
                      else [f"Col{i+1}" for i in range(len(df.columns))])
        df = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

        if "Staff_Name" in df.columns:
            split_r = df["Staff_Name"].apply(
                lambda x: pd.Series(split_staff_parts(x), index=["Staff_Name", "Company", "Branch"]))
            df["Staff_Name"] = split_r["Staff_Name"]
            df["Company"]    = split_r["Company"].apply(normalise_company)
            df["Branch"]     = split_r["Branch"]

        df["Instalment"] = (df["Instalment"].astype(str)
                            .str.replace(",", "", regex=False)
                            .str.replace("₹", "", regex=False).str.strip())
        df["Instalment"] = pd.to_numeric(df["Instalment"], errors="coerce").fillna(0)
        state.df_snap = df
    except Exception as e:
        state.status = f"MIS 1 processing failed: {e}"
    finally:
        if os.path.exists(temp):
            os.remove(temp)


# ─────────────────────────────────────────────
#  MIS 2 — MONTHLY CLOSING REPORT
# ─────────────────────────────────────────────

def scrape_mis2(context):
    state.status = "MIS 2: Scraping monthly closing payment report..."
    ensure_logged_in(context)

    # ── NCDPayment
    page = context.new_page()
    page.goto(f"{BASE_URL}Reports/ReportOptions?repo_name=NCDPayment", timeout=30000)
    page.wait_for_load_state("networkidle")
    d = state.dates
    fill_date(page, "From Date", d.from_date_month)
    fill_date(page, "To Date",   d.to_date)
    select_dropdown(page, "Branch",         "All Branch")
    select_dropdown(page, "MasterName",     "RD")
    select_dropdown(page, "Deposit Scheme", "All")
    select_dropdown(page, "Payment Status", "All")
    select_dropdown(page, "Payment Mode",   "All")
    page.wait_for_timeout(300)

    temp_pay = f"temp_mis2_pay_{d.file_suffix}.xls"
    pay_df = None
    if generate_and_download(context, page, temp_pay, "Excel 97-2003"):
        pay_df = read_xls_data_rows(temp_pay, "NCDPayment")
    page.close()
    if os.path.exists(temp_pay):
        os.remove(temp_pay)

    if pay_df is None:
        state.status = "MIS 2: Payment data unavailable."
        return

    # ── NCDDetails (for staff + Amount lookup)
    state.status = "MIS 2: Scraping deposit details for staff & amount lookup..."
    ensure_logged_in(context)
    page = context.new_page()
    page.goto(f"{BASE_URL}Reports/ReportOptions?repo_name=NCDDetails", timeout=30000)
    page.wait_for_load_state("networkidle")
    fill_date(page, "From Date", d.from_date_details)
    fill_date(page, "To Date",   d.to_date)
    select_dropdown(page, "Branch",        "All Branch")
    select_dropdown(page, "Staff Members", "All")
    select_dropdown(page, "Master",        "RD")
    select_dropdown(page, "Scheme",        "All")
    page.wait_for_timeout(300)

    temp_det = f"temp_mis2_det_{d.file_suffix}.xls"
    det_df = None
    if generate_and_download(context, page, temp_det, "Excel 97-2003"):
        det_df = read_xls_data_rows(temp_det, "NCDDetails")
    page.close()
    if os.path.exists(temp_det):
        os.remove(temp_det)

    # ── Merge staff + Amount into payment
    state.status = "MIS 2: Merging staff & amount information..."

    if det_df is not None and "Agent" in det_df.columns and "Dep_No" in det_df.columns:
        split = det_df["Agent"].apply(
            lambda x: pd.Series(split_staff_parts(x), index=["Staff_Name", "Company", "Branch"]))
        det_df["Staff_Name"] = split["Staff_Name"]
        det_df["Company"]    = split["Company"].apply(normalise_company)
        det_df["Branch"]     = split["Branch"]

        # Include Amount from NCDDetails in the lookup
        lookup_cols = ["Dep_No", "Staff_Name", "Company", "Branch"]
        if "Amount" in det_df.columns:
            lookup_cols.append("Amount")
        lookup = det_df[lookup_cols].drop_duplicates(subset=["Dep_No"]).copy()
        lookup["Dep_No"] = lookup["Dep_No"].astype(str).str.strip()

        pay_df["Deposit_No"] = pay_df["Deposit_No"].astype(str).str.strip()
        merged = pay_df.merge(lookup, left_on="Deposit_No", right_on="Dep_No", how="left")
        merged.drop(columns=["Dep_No"], inplace=True, errors="ignore")
    else:
        merged = pay_df.copy()

    for col in ["Staff_Name", "Company", "Branch"]:
        if col not in merged.columns:
            merged[col] = ""
        else:
            merged[col] = merged[col].fillna("")

    # Numeric conversions
    for col in ["Principal", "Amount"]:
        if col in merged.columns:
            merged[col] = (merged[col].astype(str)
                           .str.replace(",", "", regex=False)
                           .str.replace("₹", "", regex=False).str.strip())
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
        else:
            merged[col] = 0

    state.df_payment = merged


# ─────────────────────────────────────────────
#  MIS 4 — DEPOSIT OUTSTANDING COMPARISON
# ─────────────────────────────────────────────

OUTSTANDING_FORM_VALUES = {
    "Area":   "None",
    "Branch": "All Branch",
    "Master": "RD",
    "Scheme": "All",
}

_DEP_PATTERN   = re.compile(r"^[A-Z]{2}\d+", re.IGNORECASE)
_SKIP_PREFIXES = ("Branch", "Deposit", "Total", "Dep.Number", "Sangeeth", "Area", "nan")


def parse_outstanding_xls(filepath):
    try:
        df = pd.read_excel(filepath, engine="xlrd", header=None, dtype=str)
    except Exception:
        return None

    records = []
    current_staff = None

    for _, row in df.iterrows():
        col0 = str(row[0]).strip() if not pd.isna(row[0]) else ""
        col7 = str(row[7]).strip() if len(row) > 7 and not pd.isna(row[7]) else ""

        if col0 in ("", "nan") and col7 and col7 not in ("nan", "Staff  Members", "Staff Members"):
            current_staff = col7
            continue

        if col0 and not col0.startswith(_SKIP_PREFIXES) and _DEP_PATTERN.match(col0):
            try:
                princ_raw = str(row[19]).strip() if len(row) > 19 else ""
                princ = float(princ_raw.replace(",", "")) if princ_raw not in ("", "nan") else 0.0
            except Exception:
                princ = 0.0

            staff_name = current_staff or ""
            _, company_raw, _ = split_staff_parts(staff_name)
            company = normalise_company(company_raw) if company_raw else "SNL"
            records.append({"dep": col0, "staff": staff_name, "company": company, "princ": princ})

    return records


def scrape_outstanding_for_date(context, ason_date_str, label):
    state.status = f"MIS 4: Fetching outstanding as of {ason_date_str}..."
    ensure_logged_in(context)
    page = context.new_page()
    page.goto(f"{BASE_URL}Reports/ReportOptions?repo_name=DepositOutstanding", timeout=30000)
    page.wait_for_load_state("networkidle")

    fill_ason_date(page, ason_date_str)
    page.wait_for_timeout(500)
    for lbl, val in OUTSTANDING_FORM_VALUES.items():
        select_dropdown(page, lbl, val)
    page.wait_for_timeout(300)

    temp = f"temp_outstanding_{label}_{state.dates.file_suffix}.xls"
    total_princ = None
    company_breakdown = {}

    try:
        with context.expect_page(timeout=90000) as npi:
            page.click(
                "button:has-text('Generate'), input[value='Generate'], button:has-text('View Report')",
                timeout=20000)
        rp = npi.value
        rp.wait_for_load_state("networkidle", timeout=120000)
        state.status = f"MIS 4: Exporting outstanding ({ason_date_str})..."

        export_sel = locate_export_select(rp)
        if not export_sel:
            raise Exception("Export dropdown not found")

        export_sel.select_option(label="Excel 97-2003")
        with rp.expect_download(timeout=120000) as dl_info:
            rp.locator("a[id*='Export'], input[id*='Export'], button[id*='Export']").first.click(
                timeout=15000, no_wait_after=True)
        dl_info.value.save_as(temp)
        rp.close()

        state.status = f"MIS 4: Parsing outstanding data ({ason_date_str})..."
        records = parse_outstanding_xls(temp)
        if records:
            total_princ = sum(r["princ"] for r in records)
            for r in records:
                company_breakdown[r["company"]] = company_breakdown.get(r["company"], 0) + r["princ"]
    except Exception as e:
        state.status = f"MIS 4 ({ason_date_str}) failed: {e}"
    finally:
        page.close()
        if os.path.exists(temp):
            os.remove(temp)

    return total_princ, company_breakdown


def scrape_mis4(context):
    d = state.dates
    prev_total, prev_co   = scrape_outstanding_for_date(context, d.prev_outstanding, "prev")
    today_total, today_co = scrape_outstanding_for_date(context, d.to_date, "today")
    state.out_prev    = prev_total
    state.out_today   = today_total
    state.out_prev_co  = prev_co  or {}
    state.out_today_co = today_co or {}
    if prev_total is not None and today_total is not None:
        state.out_diff = today_total - prev_total
    else:
        state.out_diff = None


# ─────────────────────────────────────────────
#  BACKGROUND WORKFLOW
# ─────────────────────────────────────────────

def credentials_configured():
    return bool(USERNAME and PASSWORD)


def background_workflow():
    reload_config()
    if not credentials_configured():
        state.error_msg = (
            "Missing credentials. Set SANGEETH_USERNAME and SANGEETH_PASSWORD "
            "(or Streamlit secrets) before generating MIS."
        )
        state.running = False
        return
    try:
        with sync_playwright() as p:
            state.status = "Launching quiet automation instance..."
            browser = p.chromium.launch(headless=True, slow_mo=100)
            context = browser.new_context()

            state.status = "Login: Authenticating with Sangeeth..."
            page = context.new_page()
            page.goto(BASE_URL, timeout=45000)
            page.wait_for_load_state("networkidle")
            page.fill("input[type='text'], input[name*='user' i], input[id*='user' i]", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            page.click(
                "input[type='submit'], button[type='submit'], "
                "button:has-text('Login'), button:has-text('Sign In')")
            page.wait_for_load_state("networkidle")

            if page.locator("input[type='password']").is_visible():
                state.error_msg = "Authentication failure: Invalid credential keys."
                browser.close()
                return

            state.status = "Connected! Starting MIS pipeline..."
            page.close()

            scrape_mis1(context)
            scrape_mis2(context)
            scrape_mis4(context)

            browser.close()

        state.status = "All MIS data compiled. Rendering dashboard..."
        state.is_done = True

    except Exception as e:
        state.error_msg = f"Fatal Interruption: {str(e)}"
    finally:
        state.running = False


def validate_dates(to_date, from_date_month, from_date_details, prev_outstanding):
    """Returns MisDateConfig or raises ValueError with message."""
    try:
        parsed = {
            "to_date": parse_dmY(to_date),
            "from_date_month": parse_dmY(from_date_month),
            "from_date_details": parse_dmY(from_date_details),
            "prev_outstanding": parse_dmY(prev_outstanding),
        }
    except ValueError:
        raise ValueError("Invalid date. Use DD/MM/YYYY (e.g. 30/05/2026).") from None
    if parsed["from_date_month"] > parsed["to_date"]:
        raise ValueError("Monthly from date must be on or before to date.")
    if parsed["from_date_details"] > parsed["to_date"]:
        raise ValueError("Details from date must be on or before to date.")
    return MisDateConfig(
        to_date=format_dmY(parsed["to_date"]),
        from_date_month=format_dmY(parsed["from_date_month"]),
        from_date_details=format_dmY(parsed["from_date_details"]),
        prev_outstanding=format_dmY(parsed["prev_outstanding"]),
    )


