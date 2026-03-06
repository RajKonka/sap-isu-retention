"""
Data Preprocessing Module — V3
Merges Customer Master + Complaints + Interactions
Runs VADER NLP sentiment analysis on complaint comments
Provides explanation strings for each step (used by app.py)
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


# ─── Step Explanations (displayed in the app) ─────────────
STEP_EXPLANATIONS = {
    "load": {
        "title": "Loading Raw Data",
        "what": "Reading the 3 CSV files exported from SAP IS-U into memory.",
        "why": "These are the raw inputs — unprocessed, uncleaned, exactly as they come from SAP.",
    },
    "clean_master": {
        "title": "Cleaning Customer Master",
        "what": "Removing duplicates, filling missing values, standardizing data types, capping outliers.",
        "why": "SAP data often has duplicates from batch loads, missing fields from incomplete registrations, "
               "and outlier values from data entry errors. If we don't clean this, the ML model learns from noise.",
        "details": [
            "Drop duplicate customer_id rows (keep first)",
            "Fill missing age with median (45) — SAP BUT000 often has blank DOB",
            "Fill missing tenure with 12 months (conservative estimate)",
            "Cap age at 18-90 range (remove data entry errors)",
            "Standardize region/contract/service type strings",
        ],
    },
    "clean_complaints": {
        "title": "Cleaning Complaint Data",
        "what": "Removing empty comments, standardizing dates, validating severity ranges.",
        "why": "Empty comments give VADER nothing to analyze. Invalid severity codes would skew risk calculations. "
               "Standardized dates let us calculate resolution times accurately.",
        "details": [
            "Remove rows with empty/null comment text (VADER needs text)",
            "Validate severity is 1-5 (replace out-of-range with median 3)",
            "Ensure resolution_time_days is non-negative",
            "Drop complaints with no customer_id link",
        ],
    },
    "clean_interactions": {
        "title": "Cleaning Interaction Data",
        "what": "Standardizing satisfaction scores, removing ghost records, validating channels.",
        "why": "SAP CRM can have ghost records from cancelled interactions, null satisfaction scores "
               "that would break averages, and inconsistent channel naming.",
        "details": [
            "Fill missing satisfaction_score with 3 (neutral — don't assume good or bad)",
            "Cap duration_minutes at 0-120 (remove unrealistic values)",
            "Validate satisfaction_score is 1-5",
            "Drop rows with no customer_id",
        ],
    },
    "sentiment": {
        "title": "NLP Sentiment Analysis (VADER)",
        "what": "Reading every complaint comment and scoring it from -1.0 (very negative) to +1.0 (very positive). "
                "Then aggregating per customer: average score, worst score, volatility, and positive/negative ratios.",
        "why": "A severity code of '4' tells you the complaint is serious, but it doesn't tell you the customer "
               "said 'I want to cancel immediately, this is a nightmare.' NLP captures the emotional intensity "
               "that structured data misses. Customers who use very negative language churn at 2-3× the average rate.",
        "how": "VADER (Valence Aware Dictionary and sEntiment Reasoner) has 7,500+ words rated by human linguists. "
               "It handles intensifiers ('very frustrated' scores worse than 'frustrated'), negations ('not happy' "
               "flips positive to negative), and produces a compound score normalized to -1.0 to +1.0.",
    },
    "aggregate": {
        "title": "Aggregating Per Customer",
        "what": "Converting multiple complaint/interaction records into a single row per customer with summary statistics.",
        "why": "The ML model needs one row per customer. Customer CUST0000042 might have 7 complaints — we need "
               "to summarize those into: count (7), avg severity (3.8), worst sentiment (-0.87), etc.",
    },
    "merge": {
        "title": "Merging All Data Sources",
        "what": "Joining customer master + aggregated complaints + aggregated interactions on customer_id.",
        "why": "This creates the complete customer profile: who they are (master) + what they said (complaints + NLP) "
               "+ how they interacted (interactions). This is the foundation the ML model trains on.",
    },
}


def analyze_sentiment_vader(comments_series):
    """Run VADER sentiment analysis on a series of comment texts."""
    import nltk
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)

    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()

    results = []
    for comment in comments_series:
        if pd.isna(comment) or str(comment).strip() == "":
            results.append({"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0, "label": "Neutral"})
            continue
        scores = sia.polarity_scores(str(comment))
        label = "Positive" if scores["compound"] >= 0.05 else ("Negative" if scores["compound"] <= -0.05 else "Neutral")
        results.append({
            "compound": scores["compound"],
            "pos": scores["pos"],
            "neu": scores["neu"],
            "neg": scores["neg"],
            "label": label,
        })

    return pd.DataFrame(results)


def clean_customer_master(df):
    """Clean customer master data."""
    print("  Cleaning customer master...")
    initial = len(df)
    df = df.drop_duplicates(subset=["customer_id"], keep="first")
    df["age"] = df["age"].fillna(45).clip(18, 90).astype(int)
    df["account_tenure_months"] = df["account_tenure_months"].fillna(12).clip(1, 300).astype(int)
    df["family_size"] = df["family_size"].fillna(2).astype(int)
    df["has_autopay"] = df["has_autopay"].fillna(0).astype(int)
    df["paperless_billing"] = df["paperless_billing"].fillna(0).astype(int)
    for col in ["region", "service_type", "contract_type", "dwelling_type", "income_bracket", "home_ownership", "gender"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()
    dropped = initial - len(df)
    print(f"    Rows: {initial} → {len(df)} (dropped {dropped} duplicates)")
    return df


def clean_complaint_data(df):
    """Clean complaint data."""
    print("  Cleaning complaint data...")
    initial = len(df)
    df = df.dropna(subset=["customer_id"])
    df = df[df["comment"].notna() & (df["comment"].str.strip() != "")]
    df["severity"] = df["severity"].fillna(3).clip(1, 5).astype(int)
    df["resolution_time_days"] = df["resolution_time_days"].fillna(0).clip(0, 90).astype(int)
    df["escalated"] = df["escalated"].fillna(0).astype(int)
    df["resolved"] = df["resolved"].fillna(1).astype(int)
    dropped = initial - len(df)
    print(f"    Rows: {initial} → {len(df)} (dropped {dropped} empty/invalid)")
    return df


def clean_interaction_data(df):
    """Clean interaction data."""
    print("  Cleaning interaction data...")
    initial = len(df)
    df = df.dropna(subset=["customer_id"])
    df["satisfaction_score"] = df["satisfaction_score"].fillna(3).clip(1, 5).astype(int)
    df["duration_minutes"] = df["duration_minutes"].fillna(0).clip(0, 120).astype(int)
    df["resolved"] = df["resolved"].fillna(1).astype(int)
    dropped = initial - len(df)
    print(f"    Rows: {initial} → {len(df)} (dropped {dropped} invalid)")
    return df


def aggregate_complaints(df, customer_ids):
    """Aggregate complaint data per customer including NLP sentiment."""
    print("  Aggregating complaints + running NLP sentiment...")

    # Run VADER on all comments
    sentiment_df = analyze_sentiment_vader(df["comment"])
    df = pd.concat([df.reset_index(drop=True), sentiment_df], axis=1)

    # Print sentiment distribution
    dist = df["label"].value_counts()
    print(f"    Sentiment distribution: {dist.to_dict()}")

    # Aggregate per customer
    agg = df.groupby("customer_id").agg(
        complaint_count=("severity", "count"),
        avg_complaint_severity=("severity", "mean"),
        max_complaint_severity=("severity", "max"),
        avg_resolution_time_days=("resolution_time_days", "mean"),
        escalation_count=("escalated", "sum"),
        unresolved_complaints=("resolved", lambda x: (x == 0).sum()),
        # Sentiment aggregates
        avg_sentiment_score=("compound", "mean"),
        min_sentiment_score=("compound", "min"),
        max_sentiment_score=("compound", "max"),
        sentiment_std=("compound", "std"),
        avg_sentiment_pos=("pos", "mean"),
        avg_sentiment_neg=("neg", "mean"),
        negative_sentiment_ratio=("label", lambda x: (x == "Negative").mean()),
        positive_sentiment_ratio=("label", lambda x: (x == "Positive").mean()),
        most_common_complaint_category=("complaint_category", lambda x: x.mode().iloc[0] if len(x) > 0 else "None"),
    ).reindex(customer_ids).fillna(0)

    agg["sentiment_std"] = agg["sentiment_std"].fillna(0)
    agg["escalation_rate"] = np.where(agg["complaint_count"] > 0, agg["escalation_count"] / agg["complaint_count"], 0)

    return agg


def aggregate_interactions(df, customer_ids):
    """Aggregate interaction data per customer."""
    print("  Aggregating interactions...")

    # Channel dummies for ratio calculation
    channel_dummies = pd.get_dummies(df["channel"], prefix="channel")
    df = pd.concat([df, channel_dummies], axis=1)

    agg = df.groupby("customer_id").agg(
        total_interactions=("satisfaction_score", "count"),
        avg_satisfaction_score=("satisfaction_score", "mean"),
        min_satisfaction_score=("satisfaction_score", "min"),
        avg_interaction_duration=("duration_minutes", "mean"),
        unresolved_count=("resolved", lambda x: (x == 0).sum()),
    ).reindex(customer_ids).fillna(0)

    # Channel ratios
    for ch in ["Phone", "Email", "Web Chat"]:
        col = f"channel_{ch}"
        if col in df.columns:
            ch_ratio = df.groupby("customer_id")[col].mean().reindex(customer_ids).fillna(0)
            safe_name = ch.lower().replace(" ", "_")
            agg[f"channel_{safe_name}_ratio"] = ch_ratio

    agg["unresolved_ratio"] = np.where(agg["total_interactions"] > 0, agg["unresolved_count"] / agg["total_interactions"], 0)
    agg["avg_satisfaction_score"] = agg["avg_satisfaction_score"].replace(0, 3.0)

    return agg


def preprocess_pipeline():
    """Run the complete preprocessing pipeline."""
    print("=" * 60)
    print("DATA PREPROCESSING PIPELINE (V3 — Lean)")
    print("=" * 60)

    # Load
    print("\n[Step 1] Loading raw data...")
    master = pd.read_csv(CUSTOMER_MASTER_FILE)
    complaints = pd.read_csv(COMPLAINT_DATA_FILE)
    interactions = pd.read_csv(INTERACTION_DATA_FILE)
    print(f"  Customer Master: {len(master):,} rows")
    print(f"  Complaints: {len(complaints):,} rows")
    print(f"  Interactions: {len(interactions):,} rows")

    # Clean
    print("\n[Step 2] Cleaning data...")
    master = clean_customer_master(master)
    complaints = clean_complaint_data(complaints)
    interactions = clean_interaction_data(interactions)

    customer_ids = master["customer_id"]

    # Aggregate with NLP
    print("\n[Step 3] Aggregating & running NLP...")
    comp_agg = aggregate_complaints(complaints, customer_ids)
    int_agg = aggregate_interactions(interactions, customer_ids)

    # Compute per-month rates using tenure
    tenure = master.set_index("customer_id")["account_tenure_months"].reindex(customer_ids)
    comp_agg["complaint_rate_per_month"] = np.where(tenure.values > 0, comp_agg["complaint_count"].values / tenure.values, 0)
    int_agg["interactions_per_month"] = np.where(tenure.values > 0, int_agg["total_interactions"].values / tenure.values, 0)

    # Merge
    print("\n[Step 4] Merging all data sources...")
    merged = master.copy()
    merged = merged.merge(comp_agg, left_on="customer_id", right_index=True, how="left")
    merged = merged.merge(int_agg, left_on="customer_id", right_index=True, how="left")
    merged = merged.fillna(0)

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)
    merged.to_csv(MERGED_DATA_FILE, index=False)
    print(f"\n  Merged dataset: {merged.shape[0]:,} customers × {merged.shape[1]} columns")
    print(f"  Saved to: {MERGED_DATA_FILE}")

    # Extract feature names and label encoders for downstream
    feature_cols = [c for c in merged.columns if c not in ["customer_id", "customer_name", "account_start_date", TARGET_COLUMN]]
    ids = merged["customer_id"]

    return merged, feature_cols, ids, {}


if __name__ == "__main__":
    preprocess_pipeline()
