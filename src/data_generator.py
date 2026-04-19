"""
SAP IS-U Synthetic Data Generator — V3
Generates only the 3 core datasets needed for retention prediction:
1. Customer Master (BUT000/FKKVKP/EVER)
2. Complaint/Ticket Data (CRM) with rich comment text
3. Interaction Data (CRM_ORDERADM_H)
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

np.random.seed(RANDOM_STATE)


# ─── Comment Templates (60+ realistic) ───────────────────
COMMENT_TEMPLATES = {
    "very_negative": [
        "I want to cancel my account immediately. This is the worst service I have ever experienced.",
        "Absolutely unacceptable. Nobody has called me back in over two weeks about my issue.",
        "I am filing a formal complaint. This level of service is completely unacceptable.",
        "Worst customer experience I have ever had. I will be switching providers.",
        "I have been overcharged for the third time this year. I want a full refund and I want out.",
        "Your company is a disgrace. I have been without power for 48 hours and nobody cares.",
        "I am contacting the regulator. This is negligent and dangerous.",
        "Disgusting service. My elderly mother was left without heating because of your incompetence.",
        "I want to speak to a manager immediately. This agent was rude and unhelpful.",
        "Cancel everything. I am done with this company. Moving to the competition.",
        "Three technicians, three no-shows. I have taken time off work for nothing.",
        "My complaint from last month is still unresolved. I have called five times now.",
        "I cannot believe you are charging me for a service that was never delivered.",
        "Your automated system is a joke. I have been on hold for two hours.",
        "I am beyond frustrated. Every single bill has errors and nobody fixes them.",
    ],
    "negative": [
        "I am not happy with the service. My issue has been going on for too long.",
        "The bill seems higher than expected and I am not sure why. Quite frustrated.",
        "I called last week and was promised a callback that never came.",
        "The wait times are really bad. I do not feel valued as a customer.",
        "My meter reading was wrong again and my bill is inflated because of it.",
        "I have been a customer for years but the service quality has declined.",
        "The technician was supposed to come between 8 and 12 but never showed up.",
        "I am disappointed with how my complaint was handled last time.",
        "The new rate increase is excessive and was not communicated properly.",
        "Your website is difficult to use and I cannot find my account information.",
        "I feel like new customers get better deals while loyal customers are ignored.",
        "The power outage last week lasted much longer than what was communicated.",
        "My direct debit was taken twice this month and nobody has fixed it yet.",
        "I tried the online chat but the bot could not understand my question.",
        "Still waiting for the credit that was promised to me three weeks ago.",
    ],
    "neutral": [
        "I am calling to inquire about my current bill and payment options.",
        "I would like to update my contact details and mailing address please.",
        "Can you explain the different tariff plans available to me?",
        "I need to schedule a meter reading appointment for next week.",
        "I am moving to a new address and need to transfer my account.",
        "I would like to set up a direct debit for my monthly payments.",
        "Can someone explain the charges on my latest statement?",
        "I need a copy of my bill from last month for my records.",
        "What is the process for switching to a smart meter?",
        "I want to check if there are any maintenance works planned in my area.",
        "I received a letter about a rate change and want to understand it.",
        "Can you confirm my current contract end date please?",
        "I would like to know my current energy consumption for this quarter.",
        "Please update my email address on file.",
        "I need to report a street light that is not working near my property.",
    ],
    "positive": [
        "Thank you for resolving my issue so quickly. The agent was very professional.",
        "Great experience with customer service today. Very helpful staff.",
        "I appreciate the quick response to my query. Everything was sorted out.",
        "The technician who came to my house was excellent. Very knowledgeable.",
        "I want to compliment your team. My problem was fixed within 24 hours.",
        "Very happy with the new smart meter installation process. Smooth and easy.",
        "The new online portal is much better than the old one. Well done.",
        "Thank you for the proactive communication about the planned outage.",
        "Impressed with how quickly the power was restored after the storm.",
        "Your agent went above and beyond to help me today. Thank you.",
        "I have been with you for 10 years and the service keeps getting better.",
        "The payment plan you arranged has really helped me manage my bills.",
        "Fast, friendly service. I will recommend you to my neighbours.",
        "Thank you for the courtesy credit on my account. Much appreciated.",
        "The energy efficiency advice your team gave me has reduced my bills.",
    ],
}

COMPLAINT_CATEGORIES = [
    "High Bill", "Billing Error", "Service Outage", "Meter Issue",
    "Poor Customer Service", "Contract Dispute", "Payment Problem",
    "Technician No-Show", "Account Error", "Rate Increase",
    "Connection Issue", "Disconnection Threat",
]

INTERACTION_CHANNELS = ["Phone", "Email", "Web Chat", "Mobile App", "In-Person", "SMS"]
INTERACTION_TYPES = [
    "Complaint", "General Inquiry", "Billing Query", "Service Request",
    "Account Change", "Technical Support", "Feedback", "Escalation",
]

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West", "Northwest"]
SERVICE_TYPES = ["Electricity", "Gas", "Water", "Dual Fuel", "Multi-Utility"]
CONTRACT_TYPES = ["Residential", "Small Business", "Commercial", "Prepaid"]
DWELLING_TYPES = ["House", "Apartment", "Condo", "Townhouse", "Mobile Home"]
INCOME_BRACKETS = ["Low", "Medium", "Medium-High", "High"]


def generate_customer_master(n=NUM_CUSTOMERS):
    """Generate customer master data (SAP: BUT000 + FKKVKP + EVER)."""
    print(f"[1/3] Generating Customer Master Data ({n} customers)...")

    customers = pd.DataFrame({
        "customer_id": [f"CUST{i:07d}" for i in range(1, n + 1)],
        "customer_name": [f"Customer_{i}" for i in range(1, n + 1)],
        "age": np.random.normal(45, 15, n).clip(18, 85).astype(int),
        "gender": np.random.choice(["Male", "Female", "Other"], n, p=[0.48, 0.48, 0.04]),
        "region": np.random.choice(REGIONS, n),
        "service_type": np.random.choice(SERVICE_TYPES, n, p=[0.40, 0.25, 0.15, 0.12, 0.08]),
        "contract_type": np.random.choice(CONTRACT_TYPES, n, p=[0.55, 0.25, 0.15, 0.05]),
        "dwelling_type": np.random.choice(DWELLING_TYPES, n, p=[0.35, 0.25, 0.15, 0.15, 0.10]),
        "account_tenure_months": np.random.exponential(36, n).clip(1, 240).astype(int),
        "has_autopay": np.random.choice([0, 1], n, p=[0.4, 0.6]),
        "paperless_billing": np.random.choice([0, 1], n, p=[0.35, 0.65]),
        "family_size": np.random.choice([1, 2, 3, 4, 5, 6], n, p=[0.15, 0.25, 0.25, 0.20, 0.10, 0.05]),
        "income_bracket": np.random.choice(INCOME_BRACKETS, n, p=[0.20, 0.35, 0.30, 0.15]),
        "home_ownership": np.random.choice(["Own", "Rent", "Other"], n, p=[0.55, 0.40, 0.05]),
    })

    return customers


def generate_complaint_data(customer_ids):
    """Generate complaint/ticket data with rich comment text (SAP: CRM Service Orders)."""
    n_customers = len(customer_ids)
    print(f"[2/3] Generating Complaint Data with NLP-ready comments...")

    records = []
    for cid in customer_ids:
        # Most customers have 0-3 complaints, some have many more
        n_complaints = np.random.choice(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 15],
            p=[0.15, 0.20, 0.20, 0.15, 0.10, 0.08, 0.05, 0.03, 0.02, 0.01, 0.01]
        )
        for _ in range(n_complaints):
            # Sentiment category determines comment and severity
            sentiment_cat = np.random.choice(
                ["very_negative", "negative", "neutral", "positive"],
                p=[0.15, 0.30, 0.35, 0.20]
            )
            comment = np.random.choice(COMMENT_TEMPLATES[sentiment_cat])

            severity_map = {"very_negative": (4, 5), "negative": (3, 4), "neutral": (1, 3), "positive": (1, 2)}
            sev_range = severity_map[sentiment_cat]
            severity = np.random.randint(sev_range[0], sev_range[1] + 1)

            escalated = 1 if (severity >= 4 and np.random.random() < 0.6) else (1 if np.random.random() < 0.1 else 0)
            resolved = 0 if (severity >= 4 and np.random.random() < 0.35) else 1
            resolution_days = int(min(max(np.random.exponential(5), 0), 45)) if resolved else 0

            month = np.random.randint(1, 13)
            day = np.random.randint(1, 29)
            records.append({
                "customer_id": cid,
                "complaint_date": f"2024-{month:02d}-{day:02d}",
                "complaint_category": np.random.choice(COMPLAINT_CATEGORIES),
                "severity": severity,
                "comment": comment,
                "escalated": escalated,
                "resolved": resolved,
                "resolution_time_days": resolution_days,
            })

    df = pd.DataFrame(records)
    print(f"  Generated {len(df):,} complaint records with comments")
    return df


def generate_interaction_data(customer_ids):
    """Generate interaction/touchpoint data (SAP: CRM_ORDERADM_H)."""
    n_customers = len(customer_ids)
    print(f"[3/3] Generating Interaction Data...")

    records = []
    for cid in customer_ids:
        n_interactions = np.random.choice(
            [1, 2, 3, 4, 5, 6, 8, 10, 12, 15],
            p=[0.10, 0.15, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05, 0.03, 0.02]
        )
        for _ in range(n_interactions):
            month = np.random.randint(1, 13)
            day = np.random.randint(1, 29)
            channel = np.random.choice(INTERACTION_CHANNELS, p=[0.35, 0.20, 0.20, 0.10, 0.05, 0.10])
            itype = np.random.choice(INTERACTION_TYPES, p=[0.20, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05, 0.05])
            duration = max(1, int(np.random.exponential(8))) if channel in ["Phone", "In-Person", "Web Chat"] else 0
            resolved = np.random.choice([0, 1], p=[0.15, 0.85])
            satisfaction = np.random.choice([1, 2, 3, 4, 5], p=[0.08, 0.12, 0.30, 0.30, 0.20])

            records.append({
                "customer_id": cid,
                "interaction_date": f"2024-{month:02d}-{day:02d}",
                "interaction_type": itype,
                "channel": channel,
                "duration_minutes": duration,
                "resolved": resolved,
                "satisfaction_score": satisfaction,
            })

    df = pd.DataFrame(records)
    print(f"  Generated {len(df):,} interaction records")
    return df


def generate_churn_labels(master_df, complaint_df, interaction_df):
    """
    Generate churn labels based on behavioral signals.
    This is the KEY logic — churn is driven by complaints + interactions, not random.
    """
    print("[Churn Labels] Inferring churn from behavioral patterns...")

    cid_list = master_df["customer_id"].tolist()
    churn_scores = pd.Series(0.0, index=master_df.index)

    # ── Factor 1: Complaint volume & severity ──
    if len(complaint_df) > 0:
        comp_agg = complaint_df.groupby("customer_id").agg(
            n_complaints=("severity", "count"),
            avg_severity=("severity", "mean"),
            n_escalated=("escalated", "sum"),
            n_unresolved=("resolved", lambda x: (x == 0).sum()),
        ).reindex(cid_list).fillna(0)

        churn_scores += (comp_agg["n_complaints"].values * 0.04).clip(0, 0.25)
        churn_scores += ((comp_agg["avg_severity"].values - 2.5) * 0.08).clip(0, 0.20)
        churn_scores += (comp_agg["n_escalated"].values * 0.06).clip(0, 0.15)
        churn_scores += (comp_agg["n_unresolved"].values * 0.10).clip(0, 0.20)

    # ── Factor 2: Interaction satisfaction ──
    if len(interaction_df) > 0:
        int_agg = interaction_df.groupby("customer_id").agg(
            avg_satisfaction=("satisfaction_score", "mean"),
            n_unresolved=("resolved", lambda x: (x == 0).sum()),
        ).reindex(cid_list).fillna(3)

        churn_scores += ((3.0 - int_agg["avg_satisfaction"].values) * 0.08).clip(0, 0.20)
        churn_scores += (int_agg["n_unresolved"].values * 0.05).clip(0, 0.15)

    # ── Factor 3: Tenure (new customers churn more) ──
    tenure = master_df["account_tenure_months"].values
    churn_scores += np.where(tenure < 6, 0.15, np.where(tenure < 12, 0.08, 0.0))

    # ── Factor 4: Contract type ──
    churn_scores += np.where(master_df["contract_type"] == "Prepaid", 0.10, 0.0)

    # ── Factor 5: Autopay (reduces churn) ──
    if "has_autopay" in master_df.columns:
        churn_scores -= master_df["has_autopay"].values * 0.08

    # Add noise and convert to probability
    # Threshold at 0.45 (was 0.30) to target a realistic 20-25% churn rate
    churn_scores += np.random.normal(0, 0.06, len(master_df))
    churn_prob = 1 / (1 + np.exp(-8 * (churn_scores - 0.45)))

    churned = (np.random.random(len(master_df)) < churn_prob).astype(int)
    print(f"  Churn rate: {churned.mean():.2%} ({churned.sum()}/{len(master_df)})")

    return churned


def generate_all_data(dirs=None):
    """Generate all 3 datasets and save to CSV. Pass dirs from get_session_dirs() for session isolation."""
    d = dirs or {}
    _data_dir          = d.get("data_dir",             DATA_DIR)
    _customer_master   = d.get("customer_master_file",  CUSTOMER_MASTER_FILE)
    _complaint_data    = d.get("complaint_data_file",   COMPLAINT_DATA_FILE)
    _interaction_data  = d.get("interaction_data_file", INTERACTION_DATA_FILE)

    os.makedirs(_data_dir, exist_ok=True)

    master = generate_customer_master()
    complaints = generate_complaint_data(master["customer_id"].tolist())
    interactions = generate_interaction_data(master["customer_id"].tolist())
    master["churned"] = generate_churn_labels(master, complaints, interactions)

    master.to_csv(_customer_master, index=False)
    complaints.to_csv(_complaint_data, index=False)
    interactions.to_csv(_interaction_data, index=False)

    print(f"\nAll data saved to {_data_dir}/")
    return {"master": master, "complaint": complaints, "interaction": interactions}


if __name__ == "__main__":
    generate_all_data()
