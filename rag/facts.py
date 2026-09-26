from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats as sps


def _n(x, d=0):  return f"{x:,.{d}f}"
def _p(x):       return f"{x*100:.2f}%"
def _pk(pk):     return f"PN {pk}"


def tier1_pk(df: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in df.groupby("PN"):
        q = g["Quantity"].astype(float)
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        cv = (q.std(ddof=1) / q.mean()) if q.mean() else 0.0
        unit = str(g["Order Unit"].iloc[0]) if "Order Unit" in g else "PC"

        out += [
            f"{_pk(pk)}: {len(g)} rows in SAP 'Entradas' file (columns: Entry Date, Quantity, Order Unit, PN).",
            f"{_pk(pk)}: total Quantity = {_n(q.sum())} {unit}.",
            f"{_pk(pk)}: mean Quantity per Entry Date row = {_n(q.mean(), 2)} {unit}.",
            f"{_pk(pk)}: median Quantity per Entry Date row = {_n(q.median())} {unit}.",
            f"{_pk(pk)}: std of Quantity across Entry Date rows = {_n(q.std(ddof=1), 2)} {unit}.",
            f"{_pk(pk)}: variance of Quantity across Entry Date rows = {_n(q.var(ddof=1), 2)}.",
            f"{_pk(pk)}: min Quantity = {_n(q.min())} {unit}.",
            f"{_pk(pk)}: max Quantity = {_n(q.max())} {unit}.",
            f"{_pk(pk)}: range of Quantity (max - min) = {_n(q.max() - q.min())} {unit}.",
            f"{_pk(pk)}: coefficient of variation of Quantity = {_p(cv)}.",
            f"{_pk(pk)}: skewness of Quantity = {q.skew():.4f}.",
            f"{_pk(pk)}: kurtosis of Quantity = {q.kurtosis():.4f}.",
            f"{_pk(pk)}: IQR of Quantity (Q3 - Q1) = {_n(q.quantile(.75) - q.quantile(.25))} {unit}.",
            f"{_pk(pk)}: number of distinct Year values = {len(y)}.",
            f"{_pk(pk)}: first Year = {int(y.index.min())}.",
            f"{_pk(pk)}: last Year = {int(y.index.max())}.",
            f"{_pk(pk)}: Year span (last - first + 1) = {int(y.index.max() - y.index.min() + 1)}.",
            f"{_pk(pk)}: lifetime total Quantity grouped by Year = {_n(y.sum())} {unit}.",
            f"{_pk(pk)}: mean Quantity per Year = {_n(y.mean(), 2)} {unit}.",
            f"{_pk(pk)}: median Quantity per Year = {_n(y.median())} {unit}.",
            f"{_pk(pk)}: std of Quantity across Year = {_n(y.std(ddof=1), 2) if len(y) > 1 else '0.00'} {unit}.",
            f"{_pk(pk)}: min Quantity by Year = {_n(y.min())} {unit} in Year {int(y.idxmin())}.",
            f"{_pk(pk)}: max Quantity by Year = {_n(y.max())} {unit} in Year {int(y.idxmax())}.",
            f"{_pk(pk)}: range of Quantity across Year = {_n(y.max() - y.min())} {unit}.",
        ]
        if len(y) > 1:
            out.append(
                f"{_pk(pk)}: coefficient of variation of Quantity across Year = {_p(y.std(ddof=1) / y.mean())}."
            )
        for p in (5, 10, 25, 50, 75, 90, 95, 99):
            out.append(
                f"{_pk(pk)}: {p}th percentile of Quantity = {_n(np.percentile(q, p))} {unit}."
            )

        if len(y) >= 2:
            gr = y.pct_change().dropna()
            out += [
                f"{_pk(pk)}: mean YoY change of Quantity across Year = {_p(gr.mean())}.",
                f"{_pk(pk)}: std of YoY change of Quantity across Year = {_p(gr.std(ddof=1))}.",
                f"{_pk(pk)}: min YoY change of Quantity = {_p(gr.min())} in Year {int(gr.idxmin())}.",
                f"{_pk(pk)}: max YoY change of Quantity = {_p(gr.max())} in Year {int(gr.idxmax())}.",
                f"{_pk(pk)}: total YoY change of Quantity (last Year / first Year - 1) = {_p(y.iloc[-1] / y.iloc[0] - 1)}.",
            ]
            n = len(y) - 1
            if n > 0 and y.iloc[0] > 0:
                out.append(
                    f"{_pk(pk)}: CAGR of Quantity over Year = {_p((y.iloc[-1] / y.iloc[0]) ** (1 / n) - 1)}."
                )
            slope, icept = np.polyfit(range(len(y)), y.values, 1)
            out += [
                f"{_pk(pk)}: linear trend slope of Quantity vs Year = {_n(slope, 2)} {unit}/Year.",
                f"{_pk(pk)}: linear trend intercept of Quantity vs Year = {_n(icept, 2)} {unit}.",
            ]
            if len(y) >= 3:
                r = sps.linregress(range(len(y)), y.values)
                out += [
                    f"{_pk(pk)}: linear trend R-squared of Quantity vs Year = {r.rvalue ** 2:.4f}.",
                    f"{_pk(pk)}: linear trend p-value of Quantity vs Year = {r.pvalue:.4f}.",
                ]

        d = y.diff().dropna()
        if not d.empty:
            pr = nr = bp = bn = 0
            for v in d:
                if v > 0: pr += 1; nr = 0
                elif v < 0: nr += 1; pr = 0
                else: pr = nr = 0
                bp = max(bp, pr); bn = max(bn, nr)
            out += [
                f"{_pk(pk)}: longest run of consecutive Year-over-Year Quantity increases = {bp}.",
                f"{_pk(pk)}: longest run of consecutive Year-over-Year Quantity decreases = {bn}.",
            ]
    return out


def tier2_year(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in df.groupby("PN"):
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        unit = str(g["Order Unit"].iloc[0]) if "Order Unit" in g else "PC"
        for yr, v in y.items():
            yy = g[g["Year"] == yr]["Quantity"].astype(float)
            out += [
                f"{_pk(pk)} | Year {int(yr)}: total Quantity = {_n(v)} {unit}.",
                f"{_pk(pk)} | Year {int(yr)}: number of Entry Date rows = {len(yy)}.",
                f"{_pk(pk)} | Year {int(yr)}: mean Quantity per Entry Date row = {_n(yy.mean(), 2)} {unit}.",
                f"{_pk(pk)} | Year {int(yr)}: median Quantity per Entry Date row = {_n(yy.median())} {unit}.",
                f"{_pk(pk)} | Year {int(yr)}: std of Quantity across Entry Date rows = {_n(yy.std(ddof=1), 2) if len(yy) > 1 else '0.00'} {unit}.",
                f"{_pk(pk)} | Year {int(yr)}: min Quantity = {_n(yy.min())} {unit}.",
                f"{_pk(pk)} | Year {int(yr)}: max Quantity = {_n(yy.max())} {unit}.",
            ]
    for _, r in t.iterrows():
        pk, yr = r.PN, int(r.Year)
        out += [
            f"{_pk(pk)} | Year {yr}: Forecast Quantity = {_n(r.Forecast)} pieces.",
            f"{_pk(pk)} | Year {yr}: Actual Quantity = {_n(r.Actual)} pieces.",
            f"{_pk(pk)} | Year {yr}: Actual - Forecast = {_n(r.Actual - r.Forecast)} pieces.",
            f"{_pk(pk)} | Year {yr}: Deviation = {_p(r.Deviation)}.",
            f"{_pk(pk)} | Year {yr}: |Deviation| = {_p(abs(r.Deviation))}.",
        ]
        if not np.isnan(r.Price):
            out += [
                f"{_pk(pk)} | Year {yr}: Price = {_n(r.Price, 2)} EUR.",
                f"{_pk(pk)} | Year {yr}: FinancialImpact = {_n(r.FinancialImpact, 2)} EUR.",
                f"{_pk(pk)} | Year {yr}: Actual * Price = {_n(r.Actual * r.Price, 2)} EUR.",
                f"{_pk(pk)} | Year {yr}: Forecast * Price = {_n(r.Forecast * r.Price, 2)} EUR.",
            ]
    for pk, g in df.groupby("PN"):
        unit = str(g["Order Unit"].iloc[0]) if "Order Unit" in g else "PC"
        for i, (_, r) in enumerate(g.sort_values("Entry Date").iterrows()):
            out.append(
                f"{_pk(pk)} | entry #{i + 1}: Entry Date = {r['Entry Date'].date().isoformat()}, "
                f"Quantity = {_n(r['Quantity'])} {unit}, Order Unit = {r['Order Unit']}."
            )
    return out


def tier1_contract(t: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for pk, g in t.groupby("PN"):
        out += [
            f"{_pk(pk)} contract totals: Forecast = {_n(g.Forecast.sum())} pieces.",
            f"{_pk(pk)} contract totals: Actual = {_n(g.Actual.sum())} pieces.",
            f"{_pk(pk)} contract totals: Actual - Forecast = {_n(g.Actual.sum() - g.Forecast.sum())} pieces.",
            f"{_pk(pk)} contract totals: mean Deviation = {_p(g.Deviation.mean())}.",
            f"{_pk(pk)} contract totals: std of Deviation = {_p(g.Deviation.std(ddof=1)) if len(g) > 1 else '0.00%'}.",
            f"{_pk(pk)} contract totals: max |Deviation| = {_p(g.Deviation.abs().max())}.",
            f"{_pk(pk)} contract totals: min |Deviation| = {_p(g.Deviation.abs().min())}.",
            f"{_pk(pk)} contract totals: sum of FinancialImpact = {_n(g.FinancialImpact.sum(), 2)} EUR.",
            f"{_pk(pk)} contract totals: sum of |FinancialImpact| = {_n(g.FinancialImpact.abs().sum(), 2)} EUR.",
            f"{_pk(pk)} contract totals: count of Year with |Deviation| > 15% = {int((g.Deviation.abs() > 0.15).sum())}.",
            f"{_pk(pk)} contract totals: count of Year with |Deviation| > 20% = {int((g.Deviation.abs() > 0.20).sum())}.",
            f"{_pk(pk)} contract totals: count of Year with |Deviation| > 45% = {int((g.Deviation.abs() > 0.45).sum())}.",
            f"{_pk(pk)} contract totals: count of Year where Actual > Forecast = {int((g.Actual > g.Forecast).sum())}.",
            f"{_pk(pk)} contract totals: count of Year where Actual < Forecast = {int((g.Actual < g.Forecast).sum())}.",
        ]
    return out


def tier0_verdicts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out: list[str] = []

    hits = t[t.Deviation.abs() > 0.15]
    out.append(
        f"Verdict Q1: count of (PN, Year) rows with |Deviation| > 15% = {len(hits)}."
    )
    for _, r in hits.iterrows():
        out.append(
            f"Verdict Q1 detail: {_pk(r.PN)} | Year {int(r.Year)}: Deviation = {_p(r.Deviation)}."
        )
    out.append(
        "Verdict Q1 PK_list (PN values with |Deviation| > 15%) = "
        + (", ".join(sorted(hits.PN.unique())) if not hits.empty else "none")
        + "."
    )

    inc: list[str] = []
    for pk, g in df.groupby("PN"):
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        if len(y) >= 3 and (np.diff(y.values) > 0).all():
            inc.append(pk)
    out.append(
        f"Verdict Q2: count of PN with strictly increasing Quantity across Year (>= 3 Year values) = {len(inc)}."
    )
    out.append("Verdict Q2 PK_list = " + (", ".join(inc) if inc else "none") + ".")

    ex = t[t.Actual > t.Forecast]
    out.append(f"Verdict Q3: count of (PN, Year) rows where Actual > Forecast = {len(ex)}.")
    out.append(
        "Verdict Q3 PK_list (PN with Actual > Forecast) = "
        + (", ".join(sorted(ex.PN.unique())) if not ex.empty else "none")
        + "."
    )

    be = t[t.Actual < t.Forecast]
    out.append(f"Verdict Q4: count of (PN, Year) rows where Actual < Forecast = {len(be)}.")
    out.append(
        "Verdict Q4 PK_list (PN with Actual < Forecast) = "
        + (", ".join(sorted(be.PN.unique())) if not be.empty else "none")
        + "."
    )

    cr = t[t.Deviation.abs() > 0.20]
    out.append(f"Verdict Q5: count of (PN, Year) rows with |Deviation| > 20% = {len(cr)}.")
    out.append(
        "Verdict Q5 PK_list = "
        + (", ".join(sorted(cr.PN.unique())) if not cr.empty else "none")
        + "."
    )

    if not t.empty:
        g6 = t.groupby("PN")["FinancialImpact"].sum().sort_values(key=abs, ascending=False)
        for pk, v in g6.items():
            out.append(
                f"Verdict Q6: {_pk(pk)}: sum of FinancialImpact = {_n(v, 2)} EUR."
            )
        out.append(
            "Verdict Q6 ranking (PN ordered by |sum of FinancialImpact|, descending) = "
            + ", ".join(g6.index)
            + "."
        )
        if len(g6):
            out.append(
                f"Verdict Q6 top_PK (largest |FinancialImpact|) = {g6.index[0]}."
            )

    t7 = t.copy()
    t7["Ratio"] = t7.Actual / t7.Forecast
    c7 = t7[(t7.Ratio >= 0.80) & (t7.Ratio <= 1.00)]
    out.append(
        f"Verdict Q7: count of (PN, Year) rows with Actual/Forecast in [0.80, 1.00] = {len(c7)}."
    )
    out.append(
        "Verdict Q7 PK_list = "
        + (", ".join(sorted(c7.PN.unique())) if not c7.empty else "none")
        + "."
    )

    g8: list[tuple[str, float, int]] = []
    for pk, g in df.groupby("PN"):
        y = g.groupby("Year")["Quantity"].sum().sort_index()
        if len(y) >= 2:
            r = y.pct_change().dropna()
            g8.append((pk, float(r.max()), int(r.idxmax())))
    g8.sort(key=lambda x: x[1], reverse=True)
    out.append(
        "Verdict Q8 ranking (PN ordered by max YoY change of Quantity across Year, descending) = "
        + ", ".join(p for p, _, _ in g8)
        + "."
    )
    if g8:
        out.append(f"Verdict Q8 top_PK (largest single-year Quantity growth) = {g8[0][0]}.")
        out.append(
            f"Verdict Q8 top_growth = {_p(g8[0][1])} in Year {g8[0][2]}."
        )

    if not t.empty:
        g9 = t.groupby("PN")["Deviation"].std().sort_values(ascending=False)
        for pk, v in g9.items():
            out.append(
                f"Verdict Q9: {_pk(pk)}: std of Deviation across Year = {_p(v)}."
            )
        out.append(
            "Verdict Q9 ranking (PN ordered by std of Deviation, descending) = "
            + ", ".join(g9.index)
            + "."
        )

    if not t.empty:
        t10 = t.copy()
        t10["Combined"] = t10.Deviation.abs() * t10.Actual * t10.Price
        g10 = t10.groupby("PN")["Combined"].sum().sort_values(ascending=False)
        for pk, v in g10.items():
            out.append(
                f"Verdict Q10: {_pk(pk)}: combined score |Deviation| * Actual * Price summed over Year = {_n(v, 2)} EUR."
            )
        out.append(
            "Verdict Q10 ranking (PN ordered by combined |Deviation|*Actual*Price, descending) = "
            + ", ".join(g10.index)
            + "."
        )

    m = t[t.Deviation.abs() > 0.15]
    out.append(f"Verdict Q11: count of (PN, Year) rows with |Deviation| > 15% = {len(m)}.")
    out.append(
        "Verdict Q11 PK_list = "
        + (", ".join(sorted(m.PN.unique())) if not m.empty else "none")
        + "."
    )

    for _, r in t.iterrows():
        out.append(
            f"Verdict Q12: {_pk(r.PN)} | Year {int(r.Year)}: Actual - Forecast = "
            f"{_n(r.Actual - r.Forecast)} pieces."
        )

    for pk, g in t.groupby("PN"):
        dev = float(g.Deviation.abs().max())
        imp = float(g.FinancialImpact.abs().sum())
        y = g.set_index("Year")["Actual"].sort_index()
        if len(y) >= 2:
            d = np.diff(y.values)
            trend = (
                "increase" if (d > 0).all()
                else "decrease" if (d < 0).all()
                else "mixed"
            )
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

        out += [
            f"PRIO for {_pk(pk)}: score = {s} (max 10).",
            f"PRIO for {_pk(pk)}: class = {prio}.",
            f"PRIO for {_pk(pk)}: max |Deviation| = {_p(dev)}.",
            f"PRIO for {_pk(pk)}: sum of |FinancialImpact| = {_n(imp, 2)} EUR.",
            f"PRIO for {_pk(pk)}: trend of Actual across Year = {trend}.",
        ]
    return out


def global_facts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    out = [
        f"ALL: distinct PN count = {df['PN'].nunique()}.",
        f"ALL: number of rows in SAP 'Entradas' file = {len(df)}.",
        f"ALL: total Quantity = {_n(df['Quantity'].sum())} pieces.",
        f"ALL: mean Quantity per Entry Date row = {_n(df['Quantity'].mean(), 2)} pieces.",
        f"ALL: median Quantity per Entry Date row = {_n(df['Quantity'].median())} pieces.",
        f"ALL: std of Quantity = {_n(df['Quantity'].std(ddof=1), 2)} pieces.",
        f"ALL: min Quantity = {_n(df['Quantity'].min())} pieces.",
        f"ALL: max Quantity = {_n(df['Quantity'].max())} pieces.",
    ]
    for p in (5, 10, 25, 50, 75, 90, 95, 99):
        out.append(
            f"ALL: {p}th percentile of Quantity = {_n(np.percentile(df['Quantity'], p))} pieces."
        )
    if not t.empty:
        out += [
            f"ALL contracts: total Forecast = {_n(t.Forecast.sum())} pieces.",
            f"ALL contracts: total Actual = {_n(t.Actual.sum())} pieces.",
            f"ALL contracts: total Actual - Forecast = {_n(t.Actual.sum() - t.Forecast.sum())} pieces.",
            f"ALL contracts: total FinancialImpact = {_n(t.FinancialImpact.sum(), 2)} EUR.",
            f"ALL contracts: mean Deviation = {_p(t.Deviation.mean())}.",
            f"ALL contracts: max |Deviation| = {_p(t.Deviation.abs().max())}.",
        ]
    return out


def build_facts(df: pd.DataFrame, t: pd.DataFrame) -> list[str]:
    return (
        tier0_verdicts(df, t)
        + tier1_pk(df)
        + tier1_contract(t)
        + tier2_year(df, t)
        + global_facts(df, t)
    )
