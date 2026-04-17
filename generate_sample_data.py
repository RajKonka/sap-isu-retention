"""
Generate 3 sets of sample input data (1000 customers each) for testing uploads.

Set 1 — perfect column names, all fields present
Set 2 — all fields present but column names are slightly different (fuzzy-match test)
Set 3 — correct column names but many columns missing (sparse data test)
"""
import os
import random
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
random.seed(42)

N_CUSTOMERS = 1000
OUT_BASE = os.path.join(os.path.dirname(__file__), "data")

# ── Customer pool ──────────────────────────────────────────────────────────────
FIRST_NAMES = ["Alice","Bob","Carol","David","Emma","Frank","Grace","Henry",
               "Iris","James","Karen","Liam","Mia","Noah","Olivia","Paul",
               "Quinn","Rachel","Sam","Tina","Uma","Victor","Wendy","Xander",
               "Yara","Zach","Adrian","Beth","Cole","Diana","Ethan","Fiona"]
LAST_NAMES  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
               "Davis","Wilson","Moore","Taylor","Anderson","Thomas","Jackson",
               "White","Harris","Martin","Thompson","Robinson","Lewis","Clark"]
REGIONS     = ["North","South","East","West","Central"]
CONTRACTS   = ["Monthly","Annual","2-Year"]
SERVICES    = ["Electricity","Gas","Electricity + Gas","Water","Electricity + Water"]
DWELLINGS   = ["House","Apartment","Townhouse","Condo","Mobile Home"]
INCOME_BKTS = ["Low","Medium","High"]
CHANNELS    = ["Phone","Email","Web Chat"]
COMP_CATS   = ["Billing","Technical","Service Quality","Outage","Meter Reading","Account Management"]

POS_COMMENTS = [
    "Very happy with the service, everything works great.",
    "The support team was extremely helpful and resolved my issue quickly.",
    "Excellent response time, I am very satisfied.",
    "Great experience, the technician was professional and efficient.",
    "My billing issue was resolved within hours. Highly recommend.",
    "Love the online portal, makes managing my account super easy.",
    "Quick and helpful customer service, thank you!",
    "The new meter reading service is fantastic.",
    "Very pleased with the resolution. Great team.",
    "Outstanding service quality, no issues whatsoever.",
]
NEG_COMMENTS = [
    "I am absolutely furious — my bill doubled for no reason and no one can explain it.",
    "Terrible service, waited 3 weeks for someone to show up. Completely unacceptable.",
    "This is the worst experience I have ever had. Planning to switch provider immediately.",
    "My outage has been going on for 5 days and no one cares. Disgusting.",
    "I have called 7 times and nobody fixes the problem. I want to cancel my account.",
    "Billing errors again! Third month in a row. Completely incompetent.",
    "The technician never showed up. I took a day off work for nothing.",
    "My service was cut off without warning. I demand an explanation.",
    "Unresponsive support and endless hold times. Absolutely awful.",
    "I am done. Switching to a competitor as soon as possible. Nightmare.",
]
NEUT_COMMENTS = [
    "The outage was resolved. It would have been nice to get a notification.",
    "Service is generally okay. Had a minor billing discrepancy last month.",
    "Technician arrived on time but the fix took longer than expected.",
    "Nothing special to report. Service has been average.",
    "Billing seems correct this month. Last month there was a small issue.",
    "The support person was polite but couldn't fully resolve my issue.",
    "Service interruption was brief. Would like better communication next time.",
    "Account change was processed but took a few extra days.",
    "Had to follow up twice to get my meter reading corrected.",
    "No major problems but the website is a bit slow.",
]


def make_customer_ids(n):
    return [f"C{str(i+1).zfill(5)}" for i in range(n)]


def make_customer_master(cids):
    n = len(cids)
    tenures = rng.integers(1, 120, size=n)
    ages    = rng.integers(22, 78, size=n)
    contracts = rng.choice(CONTRACTS, size=n, p=[0.45, 0.40, 0.15])
    services  = rng.choice(SERVICES,  size=n)
    dwellings = rng.choice(DWELLINGS, size=n, p=[0.30, 0.35, 0.15, 0.15, 0.05])
    regions   = rng.choice(REGIONS,   size=n)
    income    = rng.choice(INCOME_BKTS, size=n, p=[0.25, 0.50, 0.25])
    gender    = rng.choice(["Male","Female","Non-binary"], size=n, p=[0.48, 0.48, 0.04])
    ownership = rng.choice(["Own","Rent"], size=n, p=[0.55, 0.45])

    autopay   = (rng.random(n) < 0.60).astype(int)
    paperless = (rng.random(n) < 0.55).astype(int)
    family_sz = rng.integers(1, 6, size=n)

    # Churn probability influenced by tenure, contract, satisfaction proxy
    churn_logit = (
        -1.0
        - 0.012 * tenures
        + (contracts == "Monthly") * 0.9
        + (income == "Low") * 0.6
        - autopay * 0.5
        + rng.normal(0, 0.6, n)
    )
    churn_prob = 1 / (1 + np.exp(-churn_logit))
    churned = (rng.random(n) < churn_prob).astype(int)

    names = [f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}" for _ in range(n)]
    # Generate plausible account start dates based on tenure
    start_years  = 2024 - (tenures // 12)
    start_months = rng.integers(1, 13, size=n)
    start_days   = rng.integers(1, 29, size=n)
    start_dates  = [f"{y}-{m:02d}-{d:02d}" for y, m, d in zip(start_years, start_months, start_days)]

    return pd.DataFrame({
        "customer_id":            cids,
        "customer_name":          names,
        "age":                    ages,
        "account_tenure_months":  tenures,
        "account_start_date":     start_dates,
        "contract_type":          contracts,
        "service_type":           services,
        "dwelling_type":          dwellings,
        "has_autopay":            autopay,
        "paperless_billing":      paperless,
        "family_size":            family_sz,
        "income_bracket":         income,
        "home_ownership":         ownership,
        "region":                 regions,
        "gender":                 gender,
        "churned":                churned,
    })


def make_complaint_data(cids, master_df):
    """Generate complaint rows — high-risk customers get more / nastier complaints."""
    rows = []
    churned_map = dict(zip(master_df["customer_id"], master_df["churned"]))
    tenure_map  = dict(zip(master_df["customer_id"], master_df["account_tenure_months"]))

    for cid in cids:
        is_churner = churned_map.get(cid, 0)
        # Churners average 3-5 complaints, stayers 0-2
        n_comp = rng.integers(3, 7) if is_churner else rng.integers(0, 3)
        for _ in range(n_comp):
            if is_churner:
                comment = random.choice(NEG_COMMENTS if rng.random() < 0.7 else NEUT_COMMENTS)
                severity = int(rng.integers(3, 6))
                escalated = int(rng.random() < 0.4)
                resolved  = int(rng.random() < 0.5)
                res_days  = int(rng.integers(5, 30))
            else:
                comment = random.choice(
                    POS_COMMENTS if rng.random() < 0.5 else
                    (NEUT_COMMENTS if rng.random() < 0.7 else NEG_COMMENTS)
                )
                severity = int(rng.integers(1, 4))
                escalated = int(rng.random() < 0.1)
                resolved  = int(rng.random() < 0.9)
                res_days  = int(rng.integers(0, 8))

            tenure = tenure_map.get(cid, 12)
            comp_year = 2024 - rng.integers(0, min(tenure // 12 + 1, 3))
            comp_month = rng.integers(1, 13)
            comp_day   = rng.integers(1, 29)
            comp_date  = f"{comp_year}-{comp_month:02d}-{comp_day:02d}"

            rows.append({
                "customer_id":          cid,
                "complaint_date":       comp_date,
                "complaint_category":   random.choice(COMP_CATS),
                "comment":              comment,
                "severity":             severity,
                "resolution_time_days": res_days,
                "escalated":            escalated,
                "resolved":             resolved,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "customer_id","complaint_date","complaint_category","comment",
        "severity","resolution_time_days","escalated","resolved"
    ])


def make_interaction_data(cids, master_df):
    """Generate interaction rows — 2-8 per customer."""
    rows = []
    churned_map = dict(zip(master_df["customer_id"], master_df["churned"]))

    for cid in cids:
        is_churner = churned_map.get(cid, 0)
        n_int = int(rng.integers(4, 10) if is_churner else rng.integers(1, 6))
        for _ in range(n_int):
            channel = random.choice(CHANNELS)
            sat = int(rng.integers(1, 4) if is_churner else rng.integers(3, 6))
            sat = min(max(sat, 1), 5)
            dur = int(rng.integers(20, 90) if channel == "Phone" else rng.integers(5, 30))
            resolved = int(rng.random() < (0.5 if is_churner else 0.9))

            yr  = rng.integers(2023, 2025)
            mo  = rng.integers(1, 13)
            day = rng.integers(1, 29)
            rows.append({
                "customer_id":        cid,
                "interaction_date":   f"{yr}-{mo:02d}-{day:02d}",
                "channel":            channel,
                "satisfaction_score": sat,
                "duration_minutes":   dur,
                "resolved":           resolved,
            })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SET 1 — Perfect column names
# ══════════════════════════════════════════════════════════════════════════════
def generate_set_1(out_dir):
    print("Generating Set 1 (perfect column names)...")
    cids = make_customer_ids(N_CUSTOMERS)
    master = make_customer_master(cids)
    complaints = make_complaint_data(cids, master)
    interactions = make_interaction_data(cids, master)

    os.makedirs(out_dir, exist_ok=True)
    master.to_csv(os.path.join(out_dir, "customer_master.csv"), index=False)
    complaints.to_csv(os.path.join(out_dir, "complaint_data.csv"), index=False)
    interactions.to_csv(os.path.join(out_dir, "interaction_data.csv"), index=False)
    print(f"  Customers: {len(master):,}  Complaints: {len(complaints):,}  Interactions: {len(interactions):,}")
    print(f"  Churn rate: {master['churned'].mean():.1%}")
    print(f"  Saved to: {out_dir}")


# ══════════════════════════════════════════════════════════════════════════════
# SET 2 — Slightly different column names (fuzzy-match test)
# ══════════════════════════════════════════════════════════════════════════════
# These are close enough that a fuzzy matcher with threshold ~0.75 will catch them.
CUSTOMER_MASTER_RENAME_2 = {
    "customer_id":           "cust_id",
    "customer_name":         "client_name",
    "age":                   "customer_age",
    "account_tenure_months": "tenure_months",
    "account_start_date":    "start_date",
    "contract_type":         "contract",
    "service_type":          "service",
    "dwelling_type":         "property_type",
    "has_autopay":           "auto_pay",
    "paperless_billing":     "paperless",
    "family_size":           "household_size",
    "income_bracket":        "income_level",
    "home_ownership":        "ownership_type",
    "region":                "geographic_region",
    "gender":                "sex",
    "churned":               "churn_flag",
}
COMPLAINT_RENAME_2 = {
    "customer_id":          "cust_id",
    "complaint_date":       "date_of_complaint",
    "complaint_category":   "issue_type",
    "comment":              "feedback_text",
    "severity":             "priority_level",
    "resolution_time_days": "days_to_resolve",
    "escalated":            "is_escalated",
    "resolved":             "is_resolved",
}
INTERACTION_RENAME_2 = {
    "customer_id":        "cust_id",
    "interaction_date":   "contact_date",
    "channel":            "contact_channel",
    "satisfaction_score": "sat_score",
    "duration_minutes":   "call_duration_mins",
    "resolved":           "issue_resolved",
}

def generate_set_2(out_dir):
    print("Generating Set 2 (fuzzy column names)...")
    cids = make_customer_ids(N_CUSTOMERS)
    master = make_customer_master(cids).rename(columns=CUSTOMER_MASTER_RENAME_2)
    complaints_raw = make_complaint_data(cids, make_customer_master(cids))
    interactions_raw = make_interaction_data(cids, make_customer_master(cids))
    complaints = complaints_raw.rename(columns=COMPLAINT_RENAME_2)
    interactions = interactions_raw.rename(columns=INTERACTION_RENAME_2)

    os.makedirs(out_dir, exist_ok=True)
    master.to_csv(os.path.join(out_dir, "customer_master.csv"), index=False)
    complaints.to_csv(os.path.join(out_dir, "complaint_data.csv"), index=False)
    interactions.to_csv(os.path.join(out_dir, "interaction_data.csv"), index=False)
    print(f"  Customers: {len(master):,}  Complaints: {len(complaints):,}  Interactions: {len(interactions):,}")
    print(f"  Sample master columns: {list(master.columns)}")
    print(f"  Saved to: {out_dir}")


# ══════════════════════════════════════════════════════════════════════════════
# SET 3 — Correct column names but sparse (many columns missing)
# ══════════════════════════════════════════════════════════════════════════════
# customer_master: only customer_id, customer_name, region, contract_type, service_type, churned
# complaint_data:  only customer_id, comment, severity
# interaction_data: only customer_id, channel, satisfaction_score

def generate_set_3(out_dir):
    print("Generating Set 3 (sparse columns — only essentials present)...")
    cids = make_customer_ids(N_CUSTOMERS)
    full_master = make_customer_master(cids)
    full_complaints = make_complaint_data(cids, full_master)
    full_interactions = make_interaction_data(cids, full_master)

    # Keep only a small subset of columns
    sparse_master = full_master[[
        "customer_id",
        "customer_name",
        "region",
        "contract_type",
        "service_type",
        "churned",
    ]]

    sparse_complaints = full_complaints[[
        "customer_id",
        "comment",
        "severity",
    ]]

    sparse_interactions = full_interactions[[
        "customer_id",
        "channel",
        "satisfaction_score",
    ]]

    os.makedirs(out_dir, exist_ok=True)
    sparse_master.to_csv(os.path.join(out_dir, "customer_master.csv"), index=False)
    sparse_complaints.to_csv(os.path.join(out_dir, "complaint_data.csv"), index=False)
    sparse_interactions.to_csv(os.path.join(out_dir, "interaction_data.csv"), index=False)

    print(f"  Customers: {len(sparse_master):,}  Complaints: {len(sparse_complaints):,}  Interactions: {len(sparse_interactions):,}")
    print(f"  Master columns ({len(sparse_master.columns)}): {list(sparse_master.columns)}")
    print(f"  Complaints columns ({len(sparse_complaints.columns)}): {list(sparse_complaints.columns)}")
    print(f"  Interactions columns ({len(sparse_interactions.columns)}): {list(sparse_interactions.columns)}")
    print(f"  Saved to: {out_dir}")


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "data")
    generate_set_1(os.path.join(base, "sample_set_1"))
    print()
    generate_set_2(os.path.join(base, "sample_set_2"))
    print()
    generate_set_3(os.path.join(base, "sample_set_3"))
    print("\nAll 3 sample datasets generated successfully.")
