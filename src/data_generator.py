"""
Synthetic SAP IS-U Data Generator
Generates realistic utility customer data mimicking SAP IS-U tables:
- BUT000 / BUT021 (Business Partner Master)
- EVER (Contract Account)
- ERDK (Meter Reading)
- DBERCHZ (Billing Line Items)
- Interaction / CRM records
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


def set_seed(seed=42):
    np.random.seed(seed)


def generate_customer_master(n=NUM_CUSTOMERS):
    """
    Simulates SAP IS-U Business Partner & Contract Account data.
    Tables: BUT000, BUT021, FKKVKP, EVER
    """
    set_seed()

    customer_ids = [f"CUST{str(i).zfill(7)}" for i in range(1, n + 1)]

    regions = ["Northeast", "Southeast", "Midwest", "Southwest", "West", "Gulf Coast"]
    region_weights = [0.18, 0.22, 0.15, 0.12, 0.18, 0.15]

    service_types = ["Electricity", "Gas", "Electricity+Gas", "Water", "Electricity+Water"]
    service_weights = [0.35, 0.15, 0.25, 0.10, 0.15]

    contract_types = ["Residential", "Small Business", "Commercial"]
    contract_weights = [0.65, 0.20, 0.15]

    dwelling_types = ["Single Family", "Apartment", "Townhouse", "Condo", "Mobile Home"]
    dwelling_weights = [0.40, 0.25, 0.15, 0.12, 0.08]

    income_brackets = ["Low", "Medium-Low", "Medium", "Medium-High", "High"]
    income_weights = [0.15, 0.25, 0.30, 0.20, 0.10]

    ages = np.clip(np.random.normal(48, 15, n).astype(int), 18, 90)
    genders = np.random.choice(["Male", "Female", "Other"], n, p=[0.48, 0.48, 0.04])
    tenure_months = np.clip(np.random.exponential(60, n).astype(int), 1, 360)
    family_sizes = np.clip(np.random.poisson(2.5, n), 1, 8)

    # Account creation dates
    base_date = datetime(2024, 12, 31)
    account_start_dates = [
        (base_date - timedelta(days=int(t * 30.44))).strftime("%Y-%m-%d")
        for t in tenure_months
    ]

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "customer_name": [f"Customer_{i}" for i in range(1, n + 1)],
        "age": ages,
        "gender": genders,
        "region": np.random.choice(regions, n, p=region_weights),
        "account_start_date": account_start_dates,
        "account_tenure_months": tenure_months,
        "service_type": np.random.choice(service_types, n, p=service_weights),
        "contract_type": np.random.choice(contract_types, n, p=contract_weights),
        "dwelling_type": np.random.choice(dwelling_types, n, p=dwelling_weights),
        "has_autopay": np.random.choice([0, 1], n, p=[0.45, 0.55]),
        "paperless_billing": np.random.choice([0, 1], n, p=[0.35, 0.65]),
        "family_size": family_sizes,
        "income_bracket": np.random.choice(income_brackets, n, p=income_weights),
        "home_ownership": np.random.choice(
            ["Own", "Rent", "Lease"], n, p=[0.55, 0.35, 0.10]
        ),
    })

    return df


def generate_billing_data(customer_ids, months=24):
    """
    Simulates SAP IS-U Billing data (DBERCHZ / ERCHC).
    Generates monthly billing records.
    """
    set_seed(43)
    records = []

    for cid in customer_ids:
        base_amount = np.random.uniform(50, 350)
        for m in range(months):
            bill_date = (datetime(2023, 1, 1) + timedelta(days=30 * m)).strftime("%Y-%m-%d")
            seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * m / 12)
            amount = max(10, base_amount * seasonal_factor + np.random.normal(0, 20))
            records.append({
                "customer_id": cid,
                "bill_date": bill_date,
                "bill_amount": round(amount, 2),
                "bill_status": np.random.choice(
                    ["Paid", "Paid Late", "Unpaid", "Disputed"],
                    p=[0.70, 0.15, 0.08, 0.07]
                ),
                "payment_delay_days": max(0, int(np.random.exponential(5))),
            })

    return pd.DataFrame(records)


def generate_consumption_data(customer_ids, months=24):
    """
    Simulates SAP IS-U Meter Reading / Consumption data (EABL / ETTIFN).
    """
    set_seed(44)
    records = []

    for cid in customer_ids:
        base_kwh = np.random.uniform(200, 2000)
        for m in range(months):
            reading_date = (datetime(2023, 1, 1) + timedelta(days=30 * m)).strftime("%Y-%m-%d")
            seasonal = 1 + 0.4 * np.sin(2 * np.pi * (m + 6) / 12)  # peak in summer
            kwh = max(50, base_kwh * seasonal + np.random.normal(0, base_kwh * 0.1))
            records.append({
                "customer_id": cid,
                "reading_date": reading_date,
                "consumption_kwh": round(kwh, 2),
                "meter_type": np.random.choice(["Smart", "Digital", "Analog"], p=[0.5, 0.3, 0.2]),
                "reading_type": np.random.choice(["Actual", "Estimated"], p=[0.85, 0.15]),
            })

    return pd.DataFrame(records)


def generate_interaction_data(customer_ids):
    """
    Simulates SAP CRM / IS-U interaction records.
    Includes service requests, inquiries, complaints.
    """
    set_seed(45)
    records = []

    channels = ["Phone", "Email", "Web Portal", "Mobile App", "In-Person", "Chat"]
    channel_weights = [0.30, 0.20, 0.20, 0.15, 0.05, 0.10]

    interaction_types = [
        "Billing Inquiry", "Service Request", "Outage Report",
        "Account Change", "Payment Issue", "General Inquiry",
        "Move In/Out", "Rate Plan Change", "Meter Issue"
    ]

    for cid in customer_ids:
        num_interactions = max(0, int(np.random.exponential(6)))
        for _ in range(num_interactions):
            interaction_date = (
                datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 730))
            ).strftime("%Y-%m-%d")

            records.append({
                "customer_id": cid,
                "interaction_date": interaction_date,
                "interaction_type": np.random.choice(interaction_types),
                "channel": np.random.choice(channels, p=channel_weights),
                "duration_minutes": max(1, int(np.random.exponential(8))),
                "resolved": np.random.choice([1, 0], p=[0.82, 0.18]),
                "satisfaction_score": np.random.choice([1, 2, 3, 4, 5], p=[0.08, 0.12, 0.25, 0.30, 0.25]),
            })

    return pd.DataFrame(records)


def generate_complaint_data(customer_ids):
    """
    Simulates complaint/ticket data with realistic customer comments.
    Sentiment is NOT pre-assigned — it will be derived via NLP in preprocessing.
    """
    set_seed(46)
    records = []

    complaint_categories = [
        "High Bill", "Service Outage", "Poor Customer Service",
        "Billing Error", "Meter Malfunction", "Delayed Response",
        "Rate Increase", "Connection Issue", "Environmental Concern"
    ]

    # Expanded realistic comment templates organized by tone
    # The sentiment will be computed by VADER in preprocessing, not assigned here
    very_negative_comments = [
        "Terrible service, been waiting for weeks with no resolution whatsoever",
        "Outrageous bills with no explanation, I am seriously considering switching providers immediately",
        "Worst customer experience I have ever had in my entire life, absolutely disgusting",
        "Nobody seems to care about resolving my issue, this is unacceptable and pathetic",
        "I am extremely frustrated with the complete lack of communication from your team",
        "This is the third time I've called about the same problem and nothing has been fixed, horrible",
        "Your company is a disaster, I've never dealt with such incompetent service before",
        "I want to cancel my service immediately, this has been an absolute nightmare",
        "Completely fed up with the constant outages and zero accountability from management",
        "I've been overcharged for months and nobody will help me, this is theft and fraud",
        "Disgusting how you treat loyal customers, I'm telling everyone to avoid your company",
        "My power has been out for 3 days and all I get is automated responses, shameful",
        "I regret ever signing up with this company, worst decision I ever made",
        "The incompetence of your billing department is beyond belief, absolutely furious",
        "How dare you raise rates again after providing such terrible unreliable service",
    ]

    negative_comments = [
        "Bill seems higher than expected this month, not very happy about it",
        "Had to call multiple times to get any kind of response, frustrating",
        "Service interruption was really inconvenient and disrupted my work",
        "Not happy with the rate increase, feels unfair to long-term customers",
        "Resolution took much longer than what was originally promised to me",
        "The meter reading seems inaccurate again, this keeps happening",
        "Waited on hold for 45 minutes which is unacceptable in this day and age",
        "The technician didn't show up during the scheduled time window again",
        "My neighbor has the same plan but pays less, something doesn't add up",
        "The online portal is confusing and hard to navigate, needs improvement",
        "I was promised a callback but never received one, disappointed",
        "The billing cycle change caused confusion on my payment schedule",
        "Not satisfied with the response I got from the support agent",
        "Power flickering has been an ongoing issue that nobody seems to fix",
        "I feel like I'm not getting value for what I'm paying every month",
    ]

    neutral_comments = [
        "Called to inquire about my bill details and payment options",
        "Requesting meter check at my property at a convenient time",
        "Need information about available rate plans and any current promotions",
        "Following up on my previous service request submitted last week",
        "General account inquiry about my current balance and due date",
        "I would like to update my contact information on file please",
        "Asking about the process for transferring service to a new address",
        "Looking for details on estimated vs actual meter readings",
        "Want to understand the breakdown of charges on my latest bill",
        "Checking on the status of my refund that was processed recently",
        "Need to schedule a routine maintenance appointment for my meter",
        "Inquiring about payment plan options available for my account",
        "Calling to verify my autopay is set up correctly for next month",
        "Question about the peak and off-peak pricing hours for my plan",
        "Just wanted to confirm receipt of my recent payment submission",
    ]

    positive_comments = [
        "Quick resolution to my billing question, very impressed with the service",
        "Appreciate the prompt service restoration, great job by the crew",
        "Customer service representative was very helpful and knowledgeable",
        "Happy with the new rate plan options, they really fit my needs well",
        "Great experience overall, the agent went above and beyond to help me",
        "Very satisfied with how quickly the outage was resolved in our area",
        "Thank you for the clear explanation of my bill, now I understand it fully",
        "The new smart meter is working perfectly and I love the detailed usage data",
        "Impressed by the professionalism of the technician who visited my home",
        "The online portal improvements are excellent, much easier to use now",
        "Really appreciate the proactive notification about the planned maintenance",
        "Your team handled my move-in process smoothly, very happy with the experience",
        "The autopay setup was easy and the confirmation was immediate, well done",
        "Pleased with the energy savings tips provided during my last call",
        "Excellent response time to my email inquiry, answered within hours",
    ]

    # Combine all comments with associated severity ranges
    comment_pools = [
        (very_negative_comments, "very_negative", [4, 5]),
        (negative_comments, "negative", [3, 4]),
        (neutral_comments, "neutral", [2, 3]),
        (positive_comments, "positive", [1, 2]),
    ]
    pool_weights = [0.25, 0.35, 0.25, 0.15]

    for cid in customer_ids:
        num_complaints = max(0, int(np.random.exponential(3)))
        for _ in range(num_complaints):
            # Pick a comment pool based on weights
            pool_idx = np.random.choice(len(comment_pools), p=pool_weights)
            comments, tone_label, severity_range = comment_pools[pool_idx]
            comment = np.random.choice(comments)

            complaint_date = (
                datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 730))
            ).strftime("%Y-%m-%d")

            severity = np.random.choice(severity_range)

            records.append({
                "customer_id": cid,
                "complaint_date": complaint_date,
                "complaint_category": np.random.choice(complaint_categories),
                "severity": severity,
                "comment": comment,  # Raw text — sentiment derived via NLP in preprocessing
                "resolution_time_days": max(0, int(np.random.exponential(7))),
                "escalated": np.random.choice([0, 1], p=[0.75, 0.25]),
            })

    return pd.DataFrame(records)


def generate_payment_data(customer_ids, months=24):
    """
    Simulates SAP FICA payment records (DFKKOP).
    """
    set_seed(47)
    records = []

    payment_methods = ["Bank Transfer", "Credit Card", "Check", "Auto-Debit", "Cash", "Online"]
    method_weights = [0.20, 0.25, 0.10, 0.25, 0.05, 0.15]

    for cid in customer_ids:
        for m in range(months):
            if np.random.random() > 0.05:  # 5% chance of missing payment
                pay_date = (
                    datetime(2023, 1, 1) + timedelta(days=30 * m + np.random.randint(0, 15))
                ).strftime("%Y-%m-%d")
                amount = round(np.random.uniform(40, 400), 2)
                records.append({
                    "customer_id": cid,
                    "payment_date": pay_date,
                    "payment_amount": amount,
                    "payment_method": np.random.choice(payment_methods, p=method_weights),
                    "payment_status": np.random.choice(
                        ["Completed", "Reversed", "Pending"],
                        p=[0.92, 0.04, 0.04]
                    ),
                })

    return pd.DataFrame(records)


def generate_external_demographics(customer_ids):
    """
    Simulates external demographic/enrichment data (e.g., from census, third-party).
    """
    set_seed(48)
    n = len(customer_ids)

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "census_median_income": np.random.uniform(30000, 120000, n).round(0),
        "neighborhood_crime_index": np.random.uniform(1, 10, n).round(2),
        "area_avg_property_value": np.random.uniform(80000, 600000, n).round(0),
        "distance_to_service_center_miles": np.random.uniform(0.5, 50, n).round(1),
        "num_competitors_in_area": np.random.choice([0, 1, 2, 3, 4], n, p=[0.30, 0.30, 0.20, 0.15, 0.05]),
        "area_satisfaction_index": np.random.uniform(2.0, 5.0, n).round(2),
        "renewable_energy_adoption_pct": np.random.uniform(0, 40, n).round(1),
        "avg_outages_per_year_area": np.random.poisson(3, n),
    })

    return df


def generate_churn_labels(master_df, billing_df, interaction_df, complaint_df):
    """
    Generate realistic churn labels based on customer behavior patterns.
    Churn is influenced by: complaints, payment delays, low satisfaction, short tenure, etc.
    """
    set_seed(49)
    n = len(master_df)

    # Aggregate features for churn probability
    bill_agg = billing_df.groupby("customer_id").agg(
        avg_delay=("payment_delay_days", "mean"),
        unpaid_ratio=("bill_status", lambda x: (x == "Unpaid").mean()),
    ).reindex(master_df["customer_id"]).fillna(0)

    complaint_agg = complaint_df.groupby("customer_id").agg(
        num_complaints=("severity", "count"),
        avg_severity=("severity", "mean"),
    ).reindex(master_df["customer_id"]).fillna(0)

    interaction_agg = interaction_df.groupby("customer_id").agg(
        avg_satisfaction=("satisfaction_score", "mean"),
    ).reindex(master_df["customer_id"]).fillna(3)

    # Churn probability model
    churn_score = np.zeros(n)

    # Higher complaints → higher churn
    churn_score += np.clip(complaint_agg["num_complaints"].values * 0.08, 0, 0.3)
    churn_score += np.clip((complaint_agg["avg_severity"].values - 2.5) * 0.1, 0, 0.2)

    # Payment delays
    churn_score += np.clip(bill_agg["avg_delay"].values * 0.01, 0, 0.15)
    churn_score += bill_agg["unpaid_ratio"].values * 0.3

    # Low satisfaction
    churn_score += np.clip((3.5 - interaction_agg["avg_satisfaction"].values) * 0.1, 0, 0.2)

    # Short tenure (< 12 months)
    churn_score += np.where(master_df["account_tenure_months"].values < 12, 0.1, 0)

    # No autopay
    churn_score += np.where(master_df["has_autopay"].values == 0, 0.05, 0)

    # Renters churn more
    churn_score += np.where(master_df["home_ownership"].values == "Rent", 0.05, 0)

    # Add noise
    churn_score += np.random.normal(0, 0.05, n)

    # Convert to probability and sample
    churn_prob = 1 / (1 + np.exp(-12 * (churn_score - 0.42)))  # sigmoid, tuned for ~20% churn
    churned = (np.random.random(n) < churn_prob).astype(int)

    print(f"  Churn rate: {churned.mean():.2%} ({churned.sum()}/{n})")

    return churned


def generate_all_data():
    """Generate all synthetic datasets and save to CSV."""
    print("=" * 60)
    print("SAP IS-U Synthetic Data Generator")
    print("=" * 60)

    print(f"\nGenerating data for {NUM_CUSTOMERS} customers...\n")

    # 1. Customer Master
    print("[1/8] Generating Customer Master Data...")
    master_df = generate_customer_master()
    customer_ids = master_df["customer_id"].tolist()

    # 2. Billing Data
    print("[2/8] Generating Billing Data...")
    billing_df = generate_billing_data(customer_ids)

    # 3. Consumption Data
    print("[3/8] Generating Consumption Data...")
    consumption_df = generate_consumption_data(customer_ids)

    # 4. Interaction Data
    print("[4/8] Generating Interaction Data...")
    interaction_df = generate_interaction_data(customer_ids)

    # 5. Complaint Data
    print("[5/8] Generating Complaint Data...")
    complaint_df = generate_complaint_data(customer_ids)

    # 6. Payment Data
    print("[6/8] Generating Payment Data...")
    payment_df = generate_payment_data(customer_ids)

    # 7. External Demographics
    print("[7/8] Generating External Demographics...")
    demographics_df = generate_external_demographics(customer_ids)

    # 8. Churn Labels
    print("[8/8] Generating Churn Labels...")
    master_df["churned"] = generate_churn_labels(master_df, billing_df, interaction_df, complaint_df)

    # Save all datasets
    print("\nSaving datasets to CSV...")
    os.makedirs(DATA_DIR, exist_ok=True)

    master_df.to_csv(CUSTOMER_MASTER_FILE, index=False)
    billing_df.to_csv(BILLING_DATA_FILE, index=False)
    consumption_df.to_csv(CONSUMPTION_DATA_FILE, index=False)
    interaction_df.to_csv(INTERACTION_DATA_FILE, index=False)
    complaint_df.to_csv(COMPLAINT_DATA_FILE, index=False)
    payment_df.to_csv(PAYMENT_DATA_FILE, index=False)
    demographics_df.to_csv(DEMOGRAPHICS_EXTERNAL_FILE, index=False)

    print(f"\n{'Dataset':<30} {'Rows':>10} {'Cols':>6}")
    print("-" * 50)
    for name, df in [
        ("Customer Master", master_df),
        ("Billing Data", billing_df),
        ("Consumption Data", consumption_df),
        ("Interaction Data", interaction_df),
        ("Complaint Data", complaint_df),
        ("Payment Data", payment_df),
        ("External Demographics", demographics_df),
    ]:
        print(f"{name:<30} {len(df):>10,} {len(df.columns):>6}")

    print(f"\nAll files saved to: {DATA_DIR}")
    print("=" * 60)

    return {
        "master": master_df,
        "billing": billing_df,
        "consumption": consumption_df,
        "interaction": interaction_df,
        "complaint": complaint_df,
        "payment": payment_df,
        "demographics": demographics_df,
    }


if __name__ == "__main__":
    generate_all_data()
