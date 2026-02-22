"""
Feature Engineering Module
Creates advanced features for the churn prediction model.
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


def create_engagement_score(df):
    """Create a composite customer engagement score."""
    df = df.copy()

    # Normalize relevant columns to 0-1 scale
    def normalize(series):
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:
            return pd.Series(0.5, index=series.index)
        return (series - min_val) / (max_val - min_val)

    score = pd.Series(0.0, index=df.index)

    # Higher satisfaction → higher engagement
    if "avg_satisfaction_score" in df.columns:
        score += normalize(df["avg_satisfaction_score"]) * 0.25

    # More interactions (moderate) → engagement
    if "total_interactions" in df.columns:
        score += normalize(df["total_interactions"].clip(upper=df["total_interactions"].quantile(0.95))) * 0.15

    # Autopay → engaged
    if "has_autopay" in df.columns:
        score += df["has_autopay"] * 0.15

    # Paperless billing → digital engagement
    if "paperless_billing" in df.columns:
        score += df["paperless_billing"] * 0.10

    # Low complaint severity → engaged
    if "avg_complaint_severity" in df.columns:
        score += (1 - normalize(df["avg_complaint_severity"])) * 0.15

    # Longer tenure → engaged
    if "account_tenure_months" in df.columns:
        score += normalize(df["account_tenure_months"].clip(upper=240)) * 0.10

    # Channel diversity → engaged
    if "channel_diversity" in df.columns:
        score += normalize(df["channel_diversity"]) * 0.10

    df["engagement_score"] = score.clip(0, 1)
    return df


def create_risk_indicators(df):
    """Create churn risk indicator features."""
    df = df.copy()

    # Payment risk
    df["payment_risk_flag"] = (
        (df.get("late_payments_count", 0) > 3) |
        (df.get("payment_delay_avg_days", 0) > 15)
    ).astype(int)

    # Complaint risk
    df["complaint_risk_flag"] = (
        (df.get("complaint_count", 0) > 3) |
        (df.get("avg_complaint_severity", 0) > 3.5)
    ).astype(int)

    # Satisfaction risk
    df["low_satisfaction_flag"] = (
        df.get("avg_satisfaction_score", 3) < 2.5
    ).astype(int)

    # High negative sentiment (NLP-derived)
    df["high_negative_sentiment_flag"] = (
        df.get("negative_sentiment_ratio", 0) > 0.5
    ).astype(int)

    # Very negative average sentiment score (VADER compound)
    df["very_negative_sentiment_flag"] = (
        df.get("avg_sentiment_score", 0) < -0.3
    ).astype(int)

    # Sentiment volatility — customer with mixed feelings
    df["sentiment_volatile_flag"] = (
        df.get("sentiment_std", 0) > 0.5
    ).astype(int)

    # New customer risk (< 6 months)
    df["new_customer_flag"] = (
        df.get("account_tenure_months", 0) < 6
    ).astype(int)

    # Consumption drop
    df["consumption_declining_flag"] = (
        df.get("consumption_trend", 0) < -0.1
    ).astype(int)

    # Composite risk score
    risk_cols = [
        "payment_risk_flag", "complaint_risk_flag", "low_satisfaction_flag",
        "high_negative_sentiment_flag", "very_negative_sentiment_flag",
        "sentiment_volatile_flag", "new_customer_flag", "consumption_declining_flag"
    ]
    df["composite_risk_score"] = df[risk_cols].sum(axis=1)

    return df


def create_behavioral_features(df):
    """Create behavioral pattern features."""
    df = df.copy()

    # Bill-to-income ratio proxy
    if "avg_monthly_bill" in df.columns and "census_median_income" in df.columns:
        monthly_income = df["census_median_income"] / 12
        df["bill_to_income_ratio"] = (df["avg_monthly_bill"] / monthly_income.clip(lower=1)).clip(0, 1)

    # Complaint rate (complaints per month of tenure)
    if "complaint_count" in df.columns and "account_tenure_months" in df.columns:
        df["complaint_rate_per_month"] = df["complaint_count"] / df["account_tenure_months"].clip(lower=1)

    # Interaction frequency
    if "total_interactions" in df.columns and "account_tenure_months" in df.columns:
        df["interaction_rate_per_month"] = df["total_interactions"] / df["account_tenure_months"].clip(lower=1)

    # Resolution efficiency
    if "unresolved_count" in df.columns and "total_interactions" in df.columns:
        df["unresolved_ratio"] = df["unresolved_count"] / df["total_interactions"].clip(lower=1)

    # Escalation tendency
    if "escalation_count" in df.columns and "complaint_count" in df.columns:
        df["escalation_ratio"] = df["escalation_count"] / df["complaint_count"].clip(lower=1)

    # Payment consistency
    if "reversed_payments" in df.columns and "num_payments" in df.columns:
        df["payment_reversal_ratio"] = df["reversed_payments"] / df["num_payments"].clip(lower=1)

    # Competition exposure
    if "num_competitors_in_area" in df.columns:
        df["high_competition_flag"] = (df["num_competitors_in_area"] >= 2).astype(int)

    return df


def create_tenure_segments(df):
    """Create customer tenure segments."""
    df = df.copy()
    if "account_tenure_months" in df.columns:
        bins = [0, 6, 12, 24, 60, 120, 999]
        labels = ["0-6mo", "6-12mo", "1-2yr", "2-5yr", "5-10yr", "10yr+"]
        df["tenure_segment"] = pd.cut(
            df["account_tenure_months"], bins=bins, labels=labels, include_lowest=True
        ).astype(str)
    return df


def engineer_features(df):
    """Run the complete feature engineering pipeline."""
    print("=" * 60)
    print("FEATURE ENGINEERING")
    print("=" * 60)

    initial_cols = df.shape[1]

    df = create_engagement_score(df)
    print(f"  [+] Engagement score created")

    df = create_risk_indicators(df)
    print(f"  [+] Risk indicators created")

    df = create_behavioral_features(df)
    print(f"  [+] Behavioral features created")

    df = create_tenure_segments(df)
    print(f"  [+] Tenure segments created")

    new_cols = df.shape[1] - initial_cols
    print(f"\n  New features added: {new_cols}")
    print(f"  Total features: {df.shape[1]}")
    print("=" * 60)

    return df


if __name__ == "__main__":
    merged = pd.read_csv(MERGED_DATA_FILE)
    engineered = engineer_features(merged)
    engineered.to_csv(FINAL_FEATURES_FILE, index=False)
    print(f"Saved to {FINAL_FEATURES_FILE}")
