"""Desktop Tkinter UI for Sangeeth MIS. Run: python snap1.py"""
import tkinter as tk
import threading

from mis_core import (
    state,
    default_mis_dates,
    validate_dates,
    background_workflow,
)

# ─────────────────────────────────────────────
#  GUI — MODERN TKINTER DASHBOARD
# ─────────────────────────────────────────────

class ModernDashboardApp(tk.Tk):

    BG_MAIN   = "#12131c"
    BG_CARD   = "#1a1c29"
    BG_ITEM   = "#222538"
    FG_WHITE  = "#ffffff"
    FG_GRAY   = "#8e94b0"
    ACCENT    = "#5383e6"
    ACCENT2   = "#3fc495"
    ACCENT3   = "#e6a233"
    ACCENT4   = "#b06adb"   # purple for MIS 3 net
    RED_NEG   = "#f05454"
    GREEN_POS = "#3fc495"
    SPINNER   = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Window is resizable — starts at a generous size
    WIN_W = 780
    WIN_H = 900

    def __init__(self):
        super().__init__()
        self.title("Sangeeth MIS Workspace Controller")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.minsize(680, 500)
        self.resizable(True, True)
        self.configure(bg=self.BG_MAIN)
        self._spin_idx = 0
        self._date_vars = {}
        self._setup_ui()
        self._poll()

    # ── Loading UI ────────────────────────────────────────

    def _setup_ui(self):
        hdr = tk.Frame(self, bg=self.BG_CARD, height=58)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="SANGEETH MIS AUTOMATION",
            font=("Segoe UI", 15, "bold"), fg=self.FG_WHITE, bg=self.BG_CARD
        ).pack(side=tk.LEFT, padx=25, pady=14)

        self._container = tk.Frame(self, bg=self.BG_MAIN)
        self._container.pack(fill=tk.BOTH, expand=True, padx=22, pady=16)

        defaults = default_mis_dates()
        self._date_form = tk.Frame(self._container, bg=self.BG_MAIN)
        self._date_form.pack(fill=tk.X, pady=(0, 12))

        card = tk.Frame(self._date_form, bg=self.BG_CARD, padx=20, pady=16)
        card.pack(fill=tk.X)
        tk.Label(
            card, text="REPORT DATES",
            font=("Segoe UI", 10, "bold"), fg=self.FG_GRAY, bg=self.BG_CARD
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            card, text="Use DD/MM/YYYY. MIS 1 & 2 use monthly range; MIS 4 compares outstanding dates.",
            font=("Segoe UI", 9), fg=self.FG_GRAY, bg=self.BG_CARD, wraplength=640, justify="left"
        ).pack(anchor="w", pady=(0, 12))

        fields = [
            ("to_date", "To date (MIS 1/2 end, MIS 4 today)", defaults["to_date"]),
            ("from_date_month", "From date — monthly (MIS 1 & 2 payments)", defaults["from_date_month"]),
            ("from_date_details", "From date — deposit details (MIS 2 lookup)", defaults["from_date_details"]),
            ("prev_outstanding", "Previous outstanding as-on (MIS 4)", defaults["prev_outstanding"]),
        ]
        for key, label, default in fields:
            row = tk.Frame(card, bg=self.BG_CARD)
            row.pack(fill=tk.X, pady=4)
            tk.Label(
                row, text=label, font=("Segoe UI", 9), fg=self.FG_WHITE,
                bg=self.BG_CARD, width=42, anchor="w"
            ).pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            self._date_vars[key] = var
            tk.Entry(
                row, textvariable=var, font=("Segoe UI", 10), width=14,
                bg=self.BG_ITEM, fg=self.FG_WHITE, insertbackground=self.FG_WHITE,
                relief=tk.FLAT, highlightthickness=1, highlightbackground="#2a2d40"
            ).pack(side=tk.RIGHT)

        self._lbl_date_err = tk.Label(
            card, text="", font=("Segoe UI", 9), fg=self.RED_NEG, bg=self.BG_CARD)
        self._lbl_date_err.pack(anchor="w", pady=(8, 0))

        tk.Button(
            card, text="Generate MIS", font=("Segoe UI", 11, "bold"),
            fg=self.FG_WHITE, bg=self.ACCENT, activebackground="#3d6fd4",
            activeforeground=self.FG_WHITE, relief=tk.FLAT, padx=18, pady=8,
            cursor="hand2", command=self._start_generation
        ).pack(anchor="w", pady=(14, 0))

        self._loading = tk.Frame(self._container, bg=self.BG_MAIN)

        self._lbl_spin = tk.Label(
            self._loading, text="⠋", font=("Courier", 44, "bold"),
            fg=self.ACCENT, bg=self.BG_MAIN)
        self._lbl_spin.pack(pady=(40, 14))

        self._lbl_status = tk.Label(
            self._loading, text=state.status,
            font=("Segoe UI", 11), fg=self.FG_GRAY, bg=self.BG_MAIN,
            wraplength=580, justify="center")
        self._lbl_status.pack()

    def _start_generation(self):
        if state.running:
            return
        self._lbl_date_err.config(text="")
        try:
            dates = validate_dates(
                self._date_vars["to_date"].get(),
                self._date_vars["from_date_month"].get(),
                self._date_vars["from_date_details"].get(),
                self._date_vars["prev_outstanding"].get(),
            )
        except ValueError as err:
            self._lbl_date_err.config(text=str(err))
            return

        state.prepare_run(dates)
        self._date_form.pack_forget()
        self._loading.pack(fill=tk.BOTH, expand=True)
        threading.Thread(target=background_workflow, daemon=True).start()

    # ── Poll loop ─────────────────────────────────────────

    def _poll(self):
        if not state.running:
            self.after(200, self._poll)
            return
        if state.error_msg:
            self._lbl_spin.pack_forget()
            self._lbl_status.config(
                text=state.error_msg, fg=self.RED_NEG, font=("Segoe UI", 11, "bold"))
            return
        if not state.is_done:
            self._spin_idx = (self._spin_idx + 1) % len(self.SPINNER)
            self._lbl_spin.config(text=self.SPINNER[self._spin_idx])
            self._lbl_status.config(text=state.status)
            self.after(80, self._poll)
        else:
            self._render_dashboard()

    # ── Dashboard scaffold ────────────────────────────────

    def _render_dashboard(self):
        self._loading.pack_forget()

        canvas = tk.Canvas(self._container, bg=self.BG_MAIN, highlightthickness=0)
        sb = tk.Scrollbar(self._container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sf = tk.Frame(canvas, bg=self.BG_MAIN)
        cw = canvas.create_window((0, 0), window=sf, anchor="nw")

        sf.bind("<Configure>",  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._build_mis1(sf)
        self._build_mis2(sf)
        self._build_mis3(sf)
        self._build_mis4(sf)
        tk.Frame(sf, bg=self.BG_MAIN, height=24).pack()

    # ── Reusable widgets ──────────────────────────────────

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text,
            font=("Segoe UI", 9, "bold"), fg=self.FG_GRAY, bg=self.BG_MAIN
        ).pack(anchor="w", pady=(16, 4))

    def _divider(self, parent):
        tk.Frame(parent, bg="#2a2d40", height=1).pack(fill=tk.X, pady=(0, 2))

    def _stat_cards_2(self, parent, label0, val0, color0, label1, val1, color1):
        """Two equal-width stat cards side by side."""
        cards = tk.Frame(parent, bg=self.BG_MAIN)
        cards.pack(fill=tk.X, pady=(0, 6))
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)
        for col, (lbl, val, clr, px) in enumerate([
            (label0, val0, color0, (0, 6)),
            (label1, val1, color1, (6, 0)),
        ]):
            c = tk.Frame(cards, bg=self.BG_CARD, padx=16, pady=11)
            c.grid(row=0, column=col, sticky="nsew", padx=px)
            tk.Label(c, text=lbl, font=("Segoe UI", 9, "bold"),
                     fg=self.FG_GRAY, bg=self.BG_CARD).pack(anchor="w")
            tk.Label(c, text=val, font=("Segoe UI", 19, "bold"),
                     fg=clr, bg=self.BG_CARD).pack(anchor="w", pady=(3, 0))

    def _stat_cards_3(self, parent, items):
        """
        Three equal-width stat cards.
        items = list of (label, value, color)
        """
        cards = tk.Frame(parent, bg=self.BG_MAIN)
        cards.pack(fill=tk.X, pady=(0, 6))
        for col in range(3):
            cards.grid_columnconfigure(col, weight=1)
        padx_map = [(0, 5), (5, 5), (5, 0)]
        for col, ((lbl, val, clr), px) in enumerate(zip(items, padx_map)):
            c = tk.Frame(cards, bg=self.BG_CARD, padx=13, pady=11)
            c.grid(row=0, column=col, sticky="nsew", padx=px)
            tk.Label(c, text=lbl, font=("Segoe UI", 8, "bold"),
                     fg=self.FG_GRAY, bg=self.BG_CARD).pack(anchor="w")
            tk.Label(c, text=val, font=("Segoe UI", 15, "bold"),
                     fg=clr, bg=self.BG_CARD).pack(anchor="w", pady=(3, 0))

    def _company_table_3col(self, parent, rows, headers, col_fns):
        """Standard 3-column company table: Company | col2 | col3."""
        tbl = tk.Frame(parent, bg=self.BG_CARD)
        tbl.pack(fill=tk.X, pady=(0, 4))

        thr = tk.Frame(tbl, bg=self.BG_ITEM, height=34)
        thr.pack(fill=tk.X)
        thr.pack_propagate(False)
        tk.Label(thr, text=headers[0], font=("Segoe UI", 9, "bold"),
                 fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.LEFT, padx=16)
        tk.Label(thr, text=headers[2], font=("Segoe UI", 9, "bold"),
                 fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=16)
        tk.Label(thr, text=headers[1], font=("Segoe UI", 9, "bold"),
                 fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=70)

        for idx, row in enumerate(rows):
            bg = self.BG_CARD if idx % 2 == 0 else "#1e202f"
            rf = tk.Frame(tbl, bg=bg, height=36)
            rf.pack(fill=tk.X)
            rf.pack_propagate(False)
            tk.Label(rf, text=col_fns[0](row), font=("Segoe UI", 10, "bold"),
                     fg=self.FG_WHITE, bg=bg).pack(side=tk.LEFT, padx=16)
            tk.Label(rf, text=col_fns[2](row), font=("Segoe UI", 10),
                     fg=self.FG_GRAY, bg=bg).pack(side=tk.RIGHT, padx=16)
            tk.Label(rf, text=col_fns[1](row), font=("Segoe UI", 10),
                     fg=self.FG_GRAY, bg=bg).pack(side=tk.RIGHT, padx=70)

    def _no_data(self, parent, msg="No data available."):
        tk.Label(parent, text=msg, fg=self.RED_NEG,
                 bg=self.BG_MAIN, font=("Segoe UI", 10)).pack(anchor="w", padx=4, pady=4)

    # ── MIS 1 ─────────────────────────────────────────────

    def _build_mis1(self, parent):
        self._section_label(parent, "▸  MIS 1 — ACTIVE RD ACCOUNTS & INSTALMENT")
        df = state.df_snap
        if df is None or df.empty:
            self._no_data(parent)
            return

        total_count  = len(df)
        total_inst   = df["Instalment"].sum() if "Instalment" in df.columns else 0

        self._stat_cards_2(parent,
            "TOTAL ACCOUNT RECORDS",   f"{total_count:,}",        self.ACCENT,
            "TOTAL INSTALMENT AMOUNT", f"₹ {total_inst:,.2f}",    self.ACCENT2)

        if "Company" in df.columns and "Instalment" in df.columns:
            summary = (df.groupby("Company")
                       .agg(Count=("Instalment", "count"), Total=("Instalment", "sum"))
                       .reset_index().sort_values("Total", ascending=False).to_dict("records"))
            self._company_table_3col(parent, summary,
                ["COMPANY BRAND", "ACCOUNTS", "TOTAL INSTALMENT"],
                [lambda r: str(r["Company"]),
                 lambda r: f"{r['Count']:,}",
                 lambda r: f"₹ {r['Total']:,.2f}"])

    # ── MIS 2 ─────────────────────────────────────────────

    def _build_mis2(self, parent):
        self._section_label(parent, "▸  MIS 2 — MONTHLY CLOSING REPORT")
        df = state.df_payment
        if df is None or df.empty:
            self._no_data(parent)
            return

        total_txn    = len(df)
        total_princ  = df["Principal"].sum() if "Principal" in df.columns else 0

        self._stat_cards_2(parent,
            "TOTAL TRANSACTIONS",        f"{total_txn:,}",           self.ACCENT,
            "TOTAL PRINCIPAL COLLECTED", f"₹ {total_princ:,.2f}",    self.ACCENT2)

        if "Company" in df.columns and "Principal" in df.columns:
            summary = (df.groupby("Company")
                       .agg(Count=("Principal", "count"), Total=("Principal", "sum"))
                       .reset_index().sort_values("Total", ascending=False).to_dict("records"))
            self._company_table_3col(parent, summary,
                ["COMPANY BRAND", "TRANSACTIONS", "TOTAL PRINCIPAL"],
                [lambda r: str(r["Company"]),
                 lambda r: f"{r['Count']:,}",
                 lambda r: f"₹ {r['Total']:,.2f}"])

    # ── MIS 3 — NET FOR THE MONTH ──────────────────────────

    def _build_mis3(self, parent):
        self._section_label(parent, "▸  MIS 3 — NET FOR THE MONTH  (MIS 1 Instalment − MIS 2 Amount)")

        df_snap = state.df_snap
        df_pay  = state.df_payment

        if (df_snap is None or df_snap.empty) and (df_pay is None or df_pay.empty):
            self._no_data(parent, "Insufficient data for net calculation.")
            return

        # ── Totals
        inst_total  = df_snap["Instalment"].sum() if (df_snap is not None and "Instalment" in df_snap.columns) else 0
        amt_total   = df_pay["Amount"].sum()       if (df_pay  is not None and "Amount"     in df_pay.columns)  else 0
        net_total   = inst_total - amt_total

        net_val_str   = f"₹ {abs(net_total):,.2f}"
        net_lbl_pfx   = "▲ " if net_total >= 0 else "▼ "
        net_color     = self.GREEN_POS if net_total >= 0 else self.RED_NEG

        self._stat_cards_3(parent, [
            ("MIS 1  INSTALMENT",              f"₹ {inst_total:,.2f}", self.ACCENT),
            ("MIS 2  AMOUNT",                  f"₹ {amt_total:,.2f}",  self.ACCENT2),
            ("NET  (INSTALMENT − AMOUNT)",     f"{net_lbl_pfx}{net_val_str}", net_color),
        ])

        # ── Company-wise net table
        # Build per-company sums from both frames
        co_inst = {}
        if df_snap is not None and "Company" in df_snap.columns and "Instalment" in df_snap.columns:
            for co, grp in df_snap.groupby("Company"):
                co_inst[co] = grp["Instalment"].sum()

        co_amt = {}
        if df_pay is not None and "Company" in df_pay.columns and "Amount" in df_pay.columns:
            for co, grp in df_pay.groupby("Company"):
                co_amt[co] = grp["Amount"].sum()

        all_cos = sorted(set(list(co_inst.keys()) + list(co_amt.keys())))
        if all_cos:
            rows = []
            for co in all_cos:
                inst = co_inst.get(co, 0)
                amt  = co_amt.get(co, 0)
                net  = inst - amt
                rows.append({"co": co, "inst": inst, "amt": amt, "net": net})
            rows.sort(key=lambda r: r["net"], reverse=True)

            # 4-column table: Company | Instalment | Amount | Net
            tbl = tk.Frame(parent, bg=self.BG_CARD)
            tbl.pack(fill=tk.X, pady=(0, 4))

            thr = tk.Frame(tbl, bg=self.BG_ITEM, height=34)
            thr.pack(fill=tk.X)
            thr.pack_propagate(False)
            tk.Label(thr, text="COMPANY",    font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.LEFT,  padx=16)
            tk.Label(thr, text="NET",        font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=16)
            tk.Label(thr, text="AMOUNT",     font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=90)
            tk.Label(thr, text="INSTALMENT", font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=90)

            for idx, row in enumerate(rows):
                bg     = self.BG_CARD if idx % 2 == 0 else "#1e202f"
                rf     = tk.Frame(tbl, bg=bg, height=36)
                rf.pack(fill=tk.X)
                rf.pack_propagate(False)

                net_c  = self.GREEN_POS if row["net"] >= 0 else self.RED_NEG
                sign   = "▲ " if row["net"] >= 0 else "▼ "
                net_t  = f"{sign}₹ {abs(row['net']):,.2f}"

                tk.Label(rf, text=row["co"],                    font=("Segoe UI", 10, "bold"), fg=self.FG_WHITE, bg=bg).pack(side=tk.LEFT,  padx=16)
                tk.Label(rf, text=net_t,                         font=("Segoe UI", 10, "bold"), fg=net_c,         bg=bg).pack(side=tk.RIGHT, padx=16)
                tk.Label(rf, text=f"₹ {row['amt']:,.2f}",       font=("Segoe UI", 10),          fg=self.FG_GRAY,  bg=bg).pack(side=tk.RIGHT, padx=90)
                tk.Label(rf, text=f"₹ {row['inst']:,.2f}",      font=("Segoe UI", 10),          fg=self.FG_GRAY,  bg=bg).pack(side=tk.RIGHT, padx=90)

    # ── MIS 4 — DEPOSIT OUTSTANDING COMPARISON ────────────

    def _build_mis4(self, parent):
        d = state.dates
        self._section_label(
            parent,
            f"▸  MIS 4 — DEPOSIT OUTSTANDING  ({d.prev_outstanding}  vs  {d.to_date})")

        prev_val  = state.out_prev
        today_val = state.out_today
        diff_val  = state.out_diff

        if prev_val is None and today_val is None:
            self._no_data(parent, "Outstanding data unavailable.")
            return

        prev_lbl  = f"₹ {prev_val:,.2f}"  if prev_val  is not None else "N/A"
        today_lbl = f"₹ {today_val:,.2f}" if today_val is not None else "N/A"

        if diff_val is not None:
            sign       = "▲ " if diff_val >= 0 else "▼ "
            diff_lbl   = f"{sign}₹ {abs(diff_val):,.2f}"
            diff_color = self.GREEN_POS if diff_val >= 0 else self.RED_NEG
        else:
            diff_lbl, diff_color = "N/A", self.FG_GRAY

        self._stat_cards_3(parent, [
            (f"OUTSTANDING\n{d.prev_outstanding}", prev_lbl,  self.ACCENT3),
            (f"OUTSTANDING\n{d.to_date}",          today_lbl, self.ACCENT3),
            ("MOVEMENT\n(TODAY − PREV MONTH END)",  diff_lbl,  diff_color),
        ])

        # Company breakdown: 4 columns
        prev_co  = state.out_prev_co  or {}
        today_co = state.out_today_co or {}
        all_cos  = sorted(set(list(prev_co.keys()) + list(today_co.keys())))

        if all_cos:
            rows = []
            for co in all_cos:
                p = prev_co.get(co, 0)
                t = today_co.get(co, 0)
                rows.append({"co": co, "prev": p, "today": t, "diff": t - p})
            rows.sort(key=lambda r: r["today"], reverse=True)

            tbl = tk.Frame(parent, bg=self.BG_CARD)
            tbl.pack(fill=tk.X, pady=(0, 4))

            thr = tk.Frame(tbl, bg=self.BG_ITEM, height=34)
            thr.pack(fill=tk.X)
            thr.pack_propagate(False)
            tk.Label(thr, text="COMPANY",                       font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.LEFT,  padx=16)
            tk.Label(thr, text="MOVEMENT",                      font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=16)
            tk.Label(thr, text=f"TODAY ({d.to_date})",         font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=25)
            tk.Label(thr, text=f"PREV ({d.prev_outstanding})",  font=("Segoe UI", 9, "bold"), fg=self.FG_WHITE, bg=self.BG_ITEM).pack(side=tk.RIGHT, padx=25)

            for idx, row in enumerate(rows):
                bg     = self.BG_CARD if idx % 2 == 0 else "#1e202f"
                rf     = tk.Frame(tbl, bg=bg, height=36)
                rf.pack(fill=tk.X)
                rf.pack_propagate(False)

                diff_c = self.GREEN_POS if row["diff"] >= 0 else self.RED_NEG
                sign   = "▲ " if row["diff"] >= 0 else "▼ "
                diff_t = f"{sign}₹ {abs(row['diff']):,.0f}"

                tk.Label(rf, text=row["co"],               font=("Segoe UI", 10, "bold"), fg=self.FG_WHITE, bg=bg).pack(side=tk.LEFT,  padx=16)
                tk.Label(rf, text=diff_t,                   font=("Segoe UI", 10, "bold"), fg=diff_c,        bg=bg).pack(side=tk.RIGHT, padx=16)
                tk.Label(rf, text=f"₹ {row['today']:,.0f}", font=("Segoe UI", 10),          fg=self.FG_GRAY,  bg=bg).pack(side=tk.RIGHT, padx=25)
                tk.Label(rf, text=f"₹ {row['prev']:,.0f}",  font=("Segoe UI", 10),          fg=self.FG_GRAY,  bg=bg).pack(side=tk.RIGHT, padx=25)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = ModernDashboardApp()
    app.mainloop()
Output