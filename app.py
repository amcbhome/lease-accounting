import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="IFRS 16 Lease (Lessee) — Educational App",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("IFRS 16 Lease Accounting — Plant & Machinery (Lessee)")

st.markdown(
    """
This app illustrates **IFRS 16 lease accounting** for **plant & machinery** from the **lessee** perspective.  
It computes the lease liability, right-of-use (ROU) asset, depreciation, and a full amortisation schedule.  
It also generates journal entries suitable for study or classroom demonstration.  

**Default example:** 4-year lease • £25 000 annually (arrears) • 5 % discount rate • 4-year useful life.
"""
)

# ─────────────────────────────────────────────
# Sidebar Inputs
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Inputs")
    lease_term = st.number_input("Lease term (years)", 1, 50, value=4, step=1)
    annual_payment = st.number_input("Periodic lease payment (£)", 0.0, 1_000_000.0, value=25_000.0, step=1_000.0)
    rate_pct = st.number_input("Discount rate (%)", 0.0, 100.0, value=5.0, step=0.25)
    pay_in_advance = st.selectbox("Payment timing", ["Arrears (end of period)", "Advance (start of period)"])
    useful_life = st.number_input("Useful life of asset (years)", 1, 50, value=4, step=1)
    initial_direct_costs = st.number_input("Initial direct costs (£)", 0.0, 1_000_000.0, value=0.0, step=500.0)
    prepaid_lease = st.number_input("Prepaid lease payments (£)", 0.0, 1_000_000.0, value=0.0, step=500.0)
    lease_incentives = st.number_input("Lease incentives received (£)", 0.0, 1_000_000.0, value=0.0, step=500.0)
    st.caption("ROU asset = Lease liability + direct costs + prepayments − incentives")
    run = st.button("Calculate")

# ─────────────────────────────────────────────
# Core calculation functions
# ─────────────────────────────────────────────
def pv_ordinary_annuity(pmt, r, n):
    if r == 0:
        return pmt * n
    return pmt * (1 - (1 + r) ** -n) / r

def compute_lease(lease_term, annual_payment, rate, pay_in_advance, idc, prepaid, incentives, useful_life):
    r = rate
    n = lease_term
    pmt = annual_payment

    if pay_in_advance:
        pv = pmt + pv_ordinary_annuity(pmt, r, n - 1)
    else:
        pv = pv_ordinary_annuity(pmt, r, n)

    lease_liability_initial = pv
    rou_initial = lease_liability_initial + idc + prepaid - incentives

    rows = []
    opening = lease_liability_initial

    if pay_in_advance:
        principal = min(pmt, opening)
        closing = opening - principal
        rows.append(dict(Period=0, Opening=opening, Interest=0.0, Payment=pmt,
                         Principal=principal, Closing=closing))
        opening = closing

    for t in range(1, n + 1):
        interest = opening * r
        principal = pmt - interest
        if t == n:
            principal = opening
            payment = interest + principal
        else:
            payment = pmt
        closing = opening - principal
        rows.append(dict(Period=t, Opening=opening, Interest=interest,
                         Payment=payment, Principal=principal, Closing=closing))
        opening = closing

    schedule = pd.DataFrame(rows)
    dep_years = min(lease_term, useful_life)
    annual_dep = rou_initial / dep_years

    return {
        "lease_liability_initial": lease_liability_initial,
        "rou_initial": rou_initial,
        "annual_dep": annual_dep,
        "dep_years": dep_years,
        "schedule": schedule,
    }

def fmt(x): return f"£{x:,.2f}"

# ─────────────────────────────────────────────
# Run model
# ─────────────────────────────────────────────
if run:
    result = compute_lease(
        lease_term, annual_payment, rate_pct / 100,
        pay_in_advance.startswith("Advance"),
        initial_direct_costs, prepaid_lease, lease_incentives, useful_life
    )
    s = result["schedule"]

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Initial Lease Liability", fmt(result["lease_liability_initial"]))
    c2.metric("ROU Asset (initial)", fmt(result["rou_initial"]))
    c3.metric("Annual Depreciation", fmt(result["annual_dep"]))

    # Amortisation schedule
    st.subheader("📈 Lease Liability Amortisation Schedule")
    s_display = s.rename(columns={
        "Opening": "Opening Liability",
        "Principal": "Principal Reduction",
        "Closing": "Closing Liability"
    })
    st.dataframe(s_display.style.format("{:,.2f}"), use_container_width=True)

    # Journal Entries
    st.subheader("📒 Journal Entries — Example (Year 1)")
    y1 = s[s["Period"] == (1 if not pay_in_advance.startswith("Advance") else 1)].iloc[0]
    st.code(
f"""At commencement:
  Dr Right-of-Use Asset .......... {fmt(result['rou_initial'])}
      Cr Lease Liability .............. {fmt(result['lease_liability_initial'])}

End of Year 1:
  Dr Interest Expense ............. {fmt(y1['Interest'])}
  Dr Lease Liability .............. {fmt(y1['Principal'])}
      Cr Cash .......................... {fmt(y1['Payment'])}
  Dr Depreciation Expense ........ {fmt(result['annual_dep'])}
      Cr Accumulated Depreciation {fmt(result['annual_dep'])}""",
        language="text"
    )

    # Extracts
    st.subheader("🧾 Financial Statement Extracts (End of Year 1)")
    rou_nbv = result["rou_initial"] - result["annual_dep"]
    st.markdown(f"- **SOFP:** ROU asset ≈ {fmt(rou_nbv)}, Lease liability ≈ {fmt(y1['Closing'])}")
    st.markdown(f"- **SPL:** Depreciation {fmt(result['annual_dep'])}, Interest {fmt(y1['Interest'])}")

    # Downloads
    csv = s.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download schedule (CSV)", csv, "lease_schedule.csv", "text/csv")
else:
    st.info("Use the sidebar to set inputs, then click **Calculate**.  "
            "The defaults reproduce the 4-year × £25 000 × 5 % example.")
