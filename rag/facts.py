from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats as sps

def _n(x, d=0):  return f"{x:,.{d}f}"
def _p(x):       return f"{x*100:.2f}%"

def _build_all_percentiles(q: pd.Series) -> str:
    p_vals = [f"p{p}={_n(np.percentile(q, p))}" for p in range(1, 100)]
    lines = []
    for i in range(0, 100, 10):
        chunk = p_vals[i:i+10]
        if chunk:
            lines.append(" · ".join(chunk))
    return "\n  ".join(lines)

def tier1_pk(df: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in df.groupby("PN"):
        q = g["Quantity"].astype(float)
        unit = str(g["Order Unit"].iloc[0]) if "Order Unit" in g else "PC"
        dates = g["Entry Date"].dt.date
        span = f"{dates.min().isoformat()} → {dates.max().isoformat()}"
        cv = (q.std(ddof=1) / q.mean()) if q.mean() else 0.0
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        y_span = int(y.index.max() - y.index.min() + 1) if len(y) > 0 else 0
        skew = q.skew()
        kurt = q.kurtosis()
        shape = "right-skewed" if skew > 0.5 else "left-skewed" if skew < -0.5 else "symmetric"
        
        body = f"# Part {pk} — SAP Entries Summary\n\n"
        body += f"- **Order Unit**: {unit}\n"
        body += f"- **Rows**: {len(g)} | **Date Span**: {span}\n"
        body += f"- **Years**: {len(y)} distinct | First {int(y.index.min()) if len(y)>0 else '—'} | Last {int(y.index.max()) if len(y)>0 else '—'} | Span {y_span}\n"
        body += f"- **Total Quantity**: {_n(q.sum())} {unit}\n"
        body += f"- **Mean**: {_n(q.mean(), 2)} | **Median**: {_n(q.median())} | **Std**: {_n(q.std(ddof=1), 2)} | **Variance**: {_n(q.var(ddof=1), 2)} | **CV**: {_p(cv)}\n"
        body += f"- **Min**: {_n(q.min())} | **Max**: {_n(q.max())} | **Range**: {_n(q.max() - q.min())} | **IQR**: {_n(q.quantile(.75) - q.quantile(.25))}\n"
        body += f"- **Distribution Shape**: {shape} (skew {skew:.4f} · kurtosis {kurt:.4f})\n"
        body += f"- **Exact Percentiles (1st to 99th)**:\n  {_build_all_percentiles(q)}\n"
        out.append(body)
    return out

def tier2_year(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in df.groupby("PN"):
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        unit = str(g["Order Unit"].iloc[0]) if "Order Unit" in g else "PC"
        if len(y) > 0:
            body = f"# Part {pk} — Yearly Quantity Breakdown\n\n"
            body += "| Year | Total | Rows | Mean | Median | Std | Min | Max | YoY |\n"
            body += "|---|---|---|---|---|---|---|---|---|\n"
            for i, (yr, total) in enumerate(y.items()):
                yy = g[g["Year"] == yr]["Quantity"].astype(float)
                yoy = "—" if i == 0 else _p((total / y.iloc[i-1]) - 1)
                std_val = _n(yy.std(ddof=1), 2) if len(yy) > 1 else "0.00"
                body += f"| {int(yr)} | {_n(total)} | {len(yy)} | {_n(yy.mean())} | {_n(yy.median())} | {std_val} | {_n(yy.min())} | {_n(yy.max())} | {yoy} |\n"
            if len(y) > 1:
                body += f"\n- **Yearly Totals Stats**: mean {_n(y.mean())} · median {_n(y.median())} · std {_n(y.std(ddof=1))} · range {_n(y.max() - y.min())} · CV {_p(y.std(ddof=1) / y.mean())}\n"
                slope, icept = np.polyfit(range(len(y)), y.values, 1)
                body += f"- **Linear Trend**: slope {_n(slope)} {unit}/yr · intercept {_n(icept)} {unit}"
                if len(y) >= 3:
                    r = sps.linregress(range(len(y)), y.values)
                    body += f" · R² {r.rvalue ** 2:.4f} · p-value {r.pvalue:.4f}"
                body += "\n"
                gr = y.pct_change().dropna()
                if not gr.empty:
                    body += f"- **Growth**: mean YoY {_p(gr.mean())} · std YoY {_p(gr.std(ddof=1))} · max growth {_p(gr.max())} in {int(gr.idxmax())} · max decline {_p(gr.min())} in {int(gr.idxmin())}\n"
                    body += f"- **Lifetime Change**: {_p(y.iloc[-1] / y.iloc[0] - 1)} · **CAGR**: {_p((y.iloc[-1] / y.iloc[0]) ** (1/(len(y)-1)) - 1)}\n"
            d = y.diff().dropna()
            if not d.empty:
                pr = nr = bp = bn = 0
                for v in d:
                    if v > 0: pr += 1; nr = 0
                    elif v < 0: nr += 1; pr = 0
                    else: pr = nr = 0
                    bp = max(bp, pr); bn = max(bn, nr)
                body += f"- **Consecutive Runs**: longest increase {bp} · longest decrease {bn}\n"
            out.append(body.strip())
    return out

def tier1_contract(t: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in t.groupby("PN"):
        body = f"# Part {pk} — Contract vs Actual\n\n"
        body += "| Year | Forecast | Actual | Δ | Deviation | Price | Impact |\n"
        body += "|---|---|---|---|---|---|---|\n"
        for _, r in g.sort_values("Year").iterrows():
            prc = _n(r.Price, 2) if not np.isnan(r.Price) else "—"
            imp = _n(r.FinancialImpact, 2) if not np.isnan(r.FinancialImpact) else "—"
            body += f"| {int(r.Year)} | {_n(r.Forecast)} | {_n(r.Actual)} | {_n(r.Actual - r.Forecast)} | {_p(r.Deviation)} | {prc} | {imp} |\n"
        
        body += f"\n- **Totals**: Forecast {_n(g.Forecast.sum())} · Actual {_n(g.Actual.sum())} · Δ {_n(g.Actual.sum() - g.Forecast.sum())}\n"
        body += f"- **Deviation Stats**: mean {_p(g.Deviation.mean())} · std {_p(g.Deviation.std(ddof=1)) if len(g)>1 else '0%'} · max |dev| {_p(g.Deviation.abs().max())} · min |dev| {_p(g.Deviation.abs().min())}\n"
        body += f"- **Financials**: Σ impact {_n(g.FinancialImpact.sum(), 2)} EUR · Σ |impact| {_n(g.FinancialImpact.abs().sum(), 2)} EUR\n"
        
        hits15 = (g.Deviation.abs() > 0.15).sum()
        hits20 = (g.Deviation.abs() > 0.20).sum()
        hits45 = (g.Deviation.abs() > 0.45).sum()
        body += f"- **Thresholds**: Years with |dev| > 15%: {hits15} · > 20%: {hits20} · > 45%: {hits45}\n"
        
        hits = g[g.Deviation.abs() > 0.15]
        if not hits.empty:
            body += "- **Years > 15%**: " + " · ".join([f"{int(r.Year)} ({_p(r.Deviation)})" for _, r in hits.iterrows()]) + "\n"
        
        ex = g[g.Actual > g.Forecast]
        be = g[g.Actual < g.Forecast]
        body += f"- **Actual > Forecast in**: {', '.join(map(str, ex.Year.astype(int))) if not ex.empty else 'None'}\n"
        body += f"- **Actual < Forecast in**: {', '.join(map(str, be.Year.astype(int))) if not be.empty else 'None'}\n"
        out.append(body.strip())
    return out

def tier0_verdicts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out: list[str] = []
    if not t.empty:
        body = "# Global Verdicts & Rankings\n\n"
        
        g6 = t.groupby("PN")["FinancialImpact"].sum().sort_values(key=abs, ascending=False)
        body += "**Financial Impact Ranking (|Sum| EUR)**:\n"
        body += " · ".join([f"{pk} ({_n(v, 2)})" for pk, v in g6.items()]) + "\n\n"

        g9 = t.groupby("PN")["Deviation"].std().sort_values(ascending=False)
        body += "**Deviation Volatility (Std Dev)**:\n"
        body += " · ".join([f"{pk} ({_p(v)})" for pk, v in g9.items()]) + "\n\n"

        t10 = t.copy()
        t10["Combined"] = t10.Deviation.abs() * t10.Actual * t10.Price
        g10 = t10.groupby("PN")["Combined"].sum().sort_values(ascending=False)
        body += "**Risk Score (|Dev| × Actual × Price)**:\n"
        body += " · ".join([f"{pk} ({_n(v, 2)} EUR)" for pk, v in g10.items()]) + "\n\n"

        t7 = t.copy()
        t7["Ratio"] = t7.Actual / t7.Forecast
        c7 = t7[(t7.Ratio >= 0.80) & (t7.Ratio <= 1.00)]
        body += f"**Actual/Forecast in [0.80, 1.00]**: {', '.join(sorted(c7.PN.unique())) if not c7.empty else 'None'}\n\n"

        g8 = []
        for pk, g in df.groupby("PN"):
            y = g.groupby("Year")["Quantity"].sum().sort_index()
            if len(y) >= 2:
                r = y.pct_change().dropna()
                g8.append((pk, float(r.max()), int(r.idxmax())))
        g8.sort(key=lambda x: x[1], reverse=True)
        body += "**Max YoY Growth Ranking**:\n"
        body += " · ".join([f"{pk} ({_p(val)} in {yr})" for pk, val, yr in g8]) if g8 else "None"
        
        out.append(body.strip())

    inc = []
    for pk, g in df.groupby("PN"):
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        if len(y) >= 3 and (np.diff(y.values) > 0).all():
            inc.append(pk)
    if inc:
        out.append(f"# Strictly Increasing PNs\n\n{', '.join(inc)}")

    for pk, g in t.groupby("PN"):
        dev = float(g.Deviation.abs().max())
        imp = float(g.FinancialImpact.abs().sum())
        act_y = g.set_index("Year")["Actual"].sort_index()
        if len(act_y) >= 2:
            d = np.diff(act_y.values)
            trend = "increase" if (d > 0).all() else "decrease" if (d < 0).all() else "mixed"
        else:
            trend = "mixed"

        s = 0
        if dev > 0.45:   s += 3
        elif dev > 0.20: s += 2
        if imp >= 65_000_000:   s += 3
        elif imp >= 23_000_000: s += 2
        if trend == "increase":   s += 2
        elif trend == "decrease": s += 1
        prio = "Low" if s <= 3 else "Medium" if s <= 6 else "High"

        body = f"# Part {pk} — Priority Classification\n\n"
        body += f"- **Score**: {s} / 10 (Class: **{prio}**)\n"
        body += f"- **Max |Deviation|**: {_p(dev)}\n"
        body += f"- **Sum |Financial Impact|**: {_n(imp, 2)} EUR\n"
        body += f"- **Actual Trend**: {trend}\n"
        out.append(body.strip())
    return out

def global_facts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out = []
    q_all = df["Quantity"].astype(float)
    
    body = f"# Global SAP Entries Overview\n\n"
    body += f"- **Distinct PN count**: {df['PN'].nunique()}\n"
    body += f"- **Total rows**: {_n(len(df))}\n"
    body += f"- **Total Quantity**: {_n(q_all.sum())} pieces\n"
    body += f"- **Mean Quantity per row**: {_n(q_all.mean(), 2)} · **Median**: {_n(q_all.median())} · **Std**: {_n(q_all.std(ddof=1), 2)}\n"
    body += f"- **Min**: {_n(q_all.min())} · **Max**: {_n(q_all.max())} · **Range**: {_n(q_all.max() - q_all.min())}\n"
    body += f"- **Exact Percentiles (1st to 99th)**:\n  {_build_all_percentiles(q_all)}"
    out.append(body)

    if not t.empty:
        body = f"# Global Contracts Overview\n\n"
        body += f"- **Total Forecast**: {_n(t.Forecast.sum())} pieces\n"
        body += f"- **Total Actual**: {_n(t.Actual.sum())} pieces\n"
        body += f"- **Total Δ**: {_n(t.Actual.sum() - t.Forecast.sum())} pieces\n"
        body += f"- **Total Financial Impact**: {_n(t.FinancialImpact.sum(), 2)} EUR\n"
        body += f"- **Mean Deviation**: {_p(t.Deviation.mean())} · **Max |Deviation|**: {_p(t.Deviation.abs().max())}"
        out.append(body)
    return out

def build_facts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    return (
        tier0_verdicts(df, t)
        + tier1_pk(df)
        + tier1_contract(t)
        + tier2_year(df, t)
        + global_facts(df, t)
    )