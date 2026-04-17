"""
Feature Engineering Module — V3
Creates derived features from merged data with full explanations.
Supports optional weight multipliers from user configuration.
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


# ─── Feature Explanations (displayed in the app) ──────────
FEATURE_EXPLANATIONS = {
    "engagement_score": {
        "what": "Combined score (0-100) measuring how actively the customer interacts with you.",
        "how": "Weighted sum of: total interactions (40%), satisfaction score (30%), autopay enrollment (15%), paperless billing (15%).",
        "why": "Highly engaged customers are invested in the relationship. Low engagement often precedes churn — the customer has mentally checked out.",
    },
    "composite_risk_score": {
        "what": "Single number (0-10) summarizing overall churn risk from all behavioral flags.",
        "how": "Sum of all risk flags (each 0 or 1): complaint risk + low satisfaction + negative sentiment + volatile sentiment + new customer + frequent caller + unresolved issues.",
        "why": "Individual flags tell one story, but a customer with 5+ flags simultaneously is in serious danger. This aggregates risk signals into one actionable number.",
    },
    "complaint_risk_flag": {
        "what": "Binary flag (0/1) — does this customer have an abnormally high complaint rate?",
        "how": "Set to 1 if complaint_count > 3 OR avg_complaint_severity > 3.5.",
        "why": "More than 3 complaints signals persistent dissatisfaction. High average severity means the issues aren't minor.",
    },
    "low_satisfaction_flag": {
        "what": "Binary flag (0/1) — is this customer consistently unsatisfied with service?",
        "how": "Set to 1 if avg_satisfaction_score < 2.5 out of 5.",
        "why": "A satisfaction score below 2.5 means more than half their interactions were rated poorly. This is a strong churn predictor.",
    },
    "high_negative_sentiment_flag": {
        "what": "Binary flag (0/1) — are most of this customer's comments negative?",
        "how": "Set to 1 if negative_sentiment_ratio > 0.5 (more than half their comments scored negative by VADER).",
        "why": "When the majority of what a customer writes is negative, they're expressing sustained frustration, not a one-off bad day.",
    },
    "very_negative_sentiment_flag": {
        "what": "Binary flag (0/1) — is this customer's average sentiment deeply negative?",
        "how": "Set to 1 if avg_sentiment_score < -0.3 on the -1 to +1 scale.",
        "why": "An average below -0.3 means even their neutral-seeming complaints carry negative undertones. This captures 'politely furious' customers.",
    },
    "sentiment_volatile_flag": {
        "what": "Binary flag (0/1) — does this customer swing between positive and negative?",
        "how": "Set to 1 if sentiment_std > 0.5 (high standard deviation in sentiment scores across comments).",
        "why": "Volatile customers are unpredictable — sometimes happy, sometimes furious. They're 'on the fence' and a single bad experience could tip them.",
    },
    "new_customer_flag": {
        "what": "Binary flag (0/1) — is this customer in the critical first-year window?",
        "how": "Set to 1 if account_tenure_months < 12.",
        "why": "New customers haven't built loyalty yet. They churn at 2-3× the rate of established customers. The first year is the retention danger zone.",
    },
    "frequent_caller_flag": {
        "what": "Binary flag (0/1) — is this customer contacting you excessively?",
        "how": "Set to 1 if interactions_per_month > 2.",
        "why": "Calling more than twice a month means something isn't being resolved. Each unnecessary contact erodes goodwill.",
    },
    "unresolved_issues_flag": {
        "what": "Binary flag (0/1) — does this customer have open unresolved complaints?",
        "how": "Set to 1 if unresolved_complaints > 0 OR unresolved_count > 1.",
        "why": "Every unresolved issue is an open wound. Customers with unresolved complaints are actively unhappy.",
    },
}


def engineer_features(df, feature_multipliers=None, dirs=None):
    """
    Create engineered features from merged data.
    Optionally applies weight multipliers from user configuration.
    """
    print("=" * 60)
    print("FEATURE ENGINEERING (V3)")
    print("=" * 60)

    df = df.copy()

    # ── Engagement Score ──
    print("  Creating engagement_score...")
    interactions_norm = np.clip(df.get("total_interactions", 0) / 15, 0, 1)
    satisfaction_norm = np.clip(df.get("avg_satisfaction_score", 3) / 5, 0, 1)
    autopay_norm = df.get("has_autopay", 0).astype(float)
    paperless_norm = df.get("paperless_billing", 0).astype(float)
    df["engagement_score"] = (interactions_norm * 40 + satisfaction_norm * 30 + autopay_norm * 15 + paperless_norm * 15).round(2)

    # ── Risk Flags ──
    print("  Creating risk flags...")
    df["complaint_risk_flag"] = ((df.get("complaint_count", 0) > 3) | (df.get("avg_complaint_severity", 0) > 3.5)).astype(int)
    df["low_satisfaction_flag"] = (df.get("avg_satisfaction_score", 3) < 2.5).astype(int)
    df["high_negative_sentiment_flag"] = (df.get("negative_sentiment_ratio", 0) > 0.5).astype(int)
    df["very_negative_sentiment_flag"] = (df.get("avg_sentiment_score", 0) < -0.3).astype(int)
    df["sentiment_volatile_flag"] = (df.get("sentiment_std", 0) > 0.5).astype(int)
    df["new_customer_flag"] = (df.get("account_tenure_months", 12) < 12).astype(int)
    df["frequent_caller_flag"] = (df.get("interactions_per_month", 0) > 2).astype(int)
    df["unresolved_issues_flag"] = ((df.get("unresolved_complaints", 0) > 0) | (df.get("unresolved_count", 0) > 1)).astype(int)

    # ── Composite Risk Score ──
    print("  Creating composite_risk_score...")
    risk_flags = [
        "complaint_risk_flag", "low_satisfaction_flag",
        "high_negative_sentiment_flag", "very_negative_sentiment_flag",
        "sentiment_volatile_flag", "new_customer_flag",
        "frequent_caller_flag", "unresolved_issues_flag",
    ]
    df["composite_risk_score"] = df[risk_flags].sum(axis=1)

    # ── Apply weight multipliers if provided ──
    if feature_multipliers:
        print(f"  Applying {len(feature_multipliers)} weight multipliers...")
        for col, multiplier in feature_multipliers.items():
            if col in df.columns and col != TARGET_COLUMN and col not in ["customer_id", "customer_name"]:
                if df[col].dtype in [np.float64, np.int64, np.float32, np.int32, float, int]:
                    df[col] = df[col] * multiplier

    # ── Summary ──
    total_features = len([c for c in df.columns if c not in ["customer_id", "customer_name", "account_start_date"]])
    print(f"\n  Total features: {total_features}")
    print(f"  Risk flag distribution:")
    for flag in risk_flags:
        pct = df[flag].mean()
        print(f"    {flag}: {pct:.1%} of customers flagged")

    # Save
    d = dirs or {}
    _data_dir = d.get("data_dir", DATA_DIR)
    _final_features = d.get("final_features_file", FINAL_FEATURES_FILE)
    os.makedirs(_data_dir, exist_ok=True)
    df.to_csv(_final_features, index=False)
    print(f"  Saved to: {_final_features}")

    return df


if __name__ == "__main__":
    df = pd.read_csv(MERGED_DATA_FILE)
    engineer_features(df)
