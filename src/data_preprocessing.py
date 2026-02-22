"""
Data Preprocessing Module
- Loads all CSV files
- Cleans and validates data
- Merges on customer_id
- Handles missing values, outliers, encoding
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import warnings
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

warnings.filterwarnings("ignore")


def load_all_data():
    """Load all CSV files into DataFrames."""
    print("Loading datasets...")
    data = {
        "master": pd.read_csv(CUSTOMER_MASTER_FILE),
        "billing": pd.read_csv(BILLING_DATA_FILE),
        "consumption": pd.read_csv(CONSUMPTION_DATA_FILE),
        "interaction": pd.read_csv(INTERACTION_DATA_FILE),
        "complaint": pd.read_csv(COMPLAINT_DATA_FILE),
        "payment": pd.read_csv(PAYMENT_DATA_FILE),
        "demographics": pd.read_csv(DEMOGRAPHICS_EXTERNAL_FILE),
    }
    for name, df in data.items():
        print(f"  {name}: {df.shape[0]:,} rows x {df.shape[1]} cols")
    return data


def clean_master_data(df):
    """Clean customer master data."""
    df = df.copy()
    df["age"] = df["age"].clip(18, 95)
    df["account_tenure_months"] = df["account_tenure_months"].clip(0, 400)
    df["family_size"] = df["family_size"].clip(1, 10)
    df["account_start_date"] = pd.to_datetime(df["account_start_date"], errors="coerce")
    return df


def aggregate_billing(df):
    """Aggregate billing data per customer."""
    agg = df.groupby("customer_id").agg(
        avg_monthly_bill=("bill_amount", "mean"),
        bill_std=("bill_amount", "std"),
        max_bill=("bill_amount", "max"),
        min_bill=("bill_amount", "min"),
        total_revenue=("bill_amount", "sum"),
        payment_delay_avg_days=("payment_delay_days", "mean"),
        payment_delay_max=("payment_delay_days", "max"),
        late_payments_count=("bill_status", lambda x: ((x == "Paid Late") | (x == "Unpaid")).sum()),
        billing_disputes_count=("bill_status", lambda x: (x == "Disputed").sum()),
        num_bills=("bill_amount", "count"),
    ).reset_index()
    agg["bill_std"] = agg["bill_std"].fillna(0)
    return agg


def aggregate_consumption(df):
    """Aggregate consumption data per customer."""
    # Sort by date for trend calculation
    df = df.copy()
    df["reading_date"] = pd.to_datetime(df["reading_date"])
    df = df.sort_values(["customer_id", "reading_date"])

    agg = df.groupby("customer_id").agg(
        avg_monthly_consumption=("consumption_kwh", "mean"),
        consumption_std=("consumption_kwh", "std"),
        max_consumption=("consumption_kwh", "max"),
        min_consumption=("consumption_kwh", "min"),
        estimated_reading_ratio=("reading_type", lambda x: (x == "Estimated").mean()),
        smart_meter=("meter_type", lambda x: (x == "Smart").any().astype(int)),
    ).reset_index()

    # Consumption trend (slope of last 6 months vs first 6 months)
    def calc_trend(group):
        vals = group["consumption_kwh"].values
        if len(vals) < 4:
            return 0
        mid = len(vals) // 2
        first_half = vals[:mid].mean()
        second_half = vals[mid:].mean()
        if first_half == 0:
            return 0
        return (second_half - first_half) / first_half

    trend = df.groupby("customer_id").apply(calc_trend).reset_index()
    trend.columns = ["customer_id", "consumption_trend"]

    agg = agg.merge(trend, on="customer_id", how="left")
    agg["consumption_std"] = agg["consumption_std"].fillna(0)
    agg["consumption_volatility"] = agg["consumption_std"] / agg["avg_monthly_consumption"].clip(lower=1)
    agg["peak_to_avg_ratio"] = agg["max_consumption"] / agg["avg_monthly_consumption"].clip(lower=1)

    return agg


def aggregate_interactions(df):
    """Aggregate interaction data per customer."""
    if df.empty:
        return pd.DataFrame(columns=["customer_id"])

    agg = df.groupby("customer_id").agg(
        total_interactions=("interaction_type", "count"),
        avg_interaction_duration=("duration_minutes", "mean"),
        unresolved_count=("resolved", lambda x: (x == 0).sum()),
        avg_satisfaction_score=("satisfaction_score", "mean"),
        channel_diversity=("channel", "nunique"),
    ).reset_index()

    # Interaction type breakdown
    type_counts = df.groupby(["customer_id", "interaction_type"]).size().unstack(fill_value=0)
    type_counts.columns = [f"interaction_{c.lower().replace(' ', '_').replace('/', '_')}" for c in type_counts.columns]
    type_counts = type_counts.reset_index()

    agg = agg.merge(type_counts, on="customer_id", how="left")
    return agg


def analyze_sentiment_vader(comments):
    """
    Run VADER sentiment analysis on a Series of comment texts.
    Returns a DataFrame with sentiment_score, sentiment_label, and component scores.
    """
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    # Download VADER lexicon if not present
    import nltk
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)

    sia = SentimentIntensityAnalyzer()

    results = []
    for comment in comments:
        if pd.isna(comment) or str(comment).strip() == "":
            results.append({"compound": 0, "pos": 0, "neu": 1, "neg": 0, "label": "Neutral"})
        else:
            scores = sia.polarity_scores(str(comment))
            compound = scores["compound"]
            if compound >= 0.05:
                label = "Positive"
            elif compound <= -0.05:
                label = "Negative"
            else:
                label = "Neutral"
            results.append({
                "compound": compound,
                "pos": scores["pos"],
                "neu": scores["neu"],
                "neg": scores["neg"],
                "label": label,
            })

    return pd.DataFrame(results)


def aggregate_complaints(df):
    """Aggregate complaint data per customer with NLP-based sentiment analysis."""
    if df.empty:
        return pd.DataFrame(columns=["customer_id"])

    # ── Run VADER sentiment analysis on comment text ──
    print("  Running VADER sentiment analysis on complaint comments...")
    sentiment_df = analyze_sentiment_vader(df["comment"])
    df = df.copy()
    df["sentiment_compound"] = sentiment_df["compound"].values
    df["sentiment_pos"] = sentiment_df["pos"].values
    df["sentiment_neg"] = sentiment_df["neg"].values
    df["sentiment_label"] = sentiment_df["label"].values

    print(f"    Sentiment distribution: {df['sentiment_label'].value_counts().to_dict()}")

    agg = df.groupby("customer_id").agg(
        complaint_count=("severity", "count"),
        avg_complaint_severity=("severity", "mean"),
        max_complaint_severity=("severity", "max"),
        avg_resolution_time_days=("resolution_time_days", "mean"),
        escalation_count=("escalated", "sum"),
    ).reset_index()

    # ── Sentiment aggregation from NLP scores ──
    sent_agg = df.groupby("customer_id").agg(
        avg_sentiment_score=("sentiment_compound", "mean"),
        min_sentiment_score=("sentiment_compound", "min"),
        sentiment_std=("sentiment_compound", "std"),
        avg_sentiment_pos=("sentiment_pos", "mean"),
        avg_sentiment_neg=("sentiment_neg", "mean"),
        negative_sentiment_ratio=("sentiment_label", lambda x: (x == "Negative").mean()),
        positive_sentiment_ratio=("sentiment_label", lambda x: (x == "Positive").mean()),
    ).reset_index()

    sent_agg["sentiment_std"] = sent_agg["sentiment_std"].fillna(0)

    agg = agg.merge(sent_agg, on="customer_id", how="left")
    print(f"    Complaint features created with NLP sentiment for {len(agg)} customers")
    return agg


def aggregate_payments(df):
    """Aggregate payment data per customer."""
    agg = df.groupby("customer_id").agg(
        total_payments=("payment_amount", "sum"),
        avg_payment=("payment_amount", "mean"),
        num_payments=("payment_amount", "count"),
        reversed_payments=("payment_status", lambda x: (x == "Reversed").sum()),
        payment_method_diversity=("payment_method", "nunique"),
    ).reset_index()
    return agg


def merge_all_data(data_dict):
    """Merge all aggregated data on customer_id."""
    print("\nAggregating and merging datasets...")

    master = clean_master_data(data_dict["master"])
    billing_agg = aggregate_billing(data_dict["billing"])
    consumption_agg = aggregate_consumption(data_dict["consumption"])
    interaction_agg = aggregate_interactions(data_dict["interaction"])
    complaint_agg = aggregate_complaints(data_dict["complaint"])
    payment_agg = aggregate_payments(data_dict["payment"])
    demographics = data_dict["demographics"]

    # Merge all on customer_id
    merged = master.copy()
    for agg_df, name in [
        (billing_agg, "billing"),
        (consumption_agg, "consumption"),
        (interaction_agg, "interaction"),
        (complaint_agg, "complaint"),
        (payment_agg, "payment"),
        (demographics, "demographics"),
    ]:
        merged = merged.merge(agg_df, on="customer_id", how="left")
        print(f"  After merging {name}: {merged.shape}")

    # Fill NaN for customers with no complaints/interactions
    fill_zero_cols = [
        "complaint_count", "avg_complaint_severity", "max_complaint_severity",
        "avg_resolution_time_days", "escalation_count", "avg_sentiment_score",
        "min_sentiment_score", "sentiment_std", "avg_sentiment_pos", "avg_sentiment_neg",
        "negative_sentiment_ratio", "positive_sentiment_ratio",
        "total_interactions", "avg_interaction_duration",
        "unresolved_count", "channel_diversity",
    ]
    for col in fill_zero_cols:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    if "avg_satisfaction_score" in merged.columns:
        merged["avg_satisfaction_score"] = merged["avg_satisfaction_score"].fillna(3.0)

    print(f"\nFinal merged dataset: {merged.shape[0]:,} rows x {merged.shape[1]} cols")
    return merged


def encode_features(df):
    """Encode categorical features and prepare for ML."""
    df = df.copy()

    # Drop non-feature columns
    cols_to_drop = ["customer_id", "customer_name", "account_start_date"]
    id_cols = df[["customer_id"]].copy()

    # Label encode categorical columns
    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()
    categorical_cols = [c for c in categorical_cols if c not in cols_to_drop]

    label_encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le

    # Drop ID columns
    df_features = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

    # Fill any remaining NaN
    df_features = df_features.fillna(0)

    print(f"Encoded dataset: {df_features.shape[0]:,} rows x {df_features.shape[1]} cols")
    print(f"Categorical columns encoded: {categorical_cols}")

    return df_features, id_cols, label_encoders


def preprocess_pipeline():
    """Run the complete preprocessing pipeline."""
    print("=" * 60)
    print("DATA PREPROCESSING PIPELINE")
    print("=" * 60)

    # Load
    data = load_all_data()

    # Merge
    merged = merge_all_data(data)

    # Save merged data
    merged.to_csv(MERGED_DATA_FILE, index=False)
    print(f"\nMerged data saved to: {MERGED_DATA_FILE}")

    # Encode
    features, ids, encoders = encode_features(merged)

    # Save final features
    final = pd.concat([ids, features], axis=1)
    final.to_csv(FINAL_FEATURES_FILE, index=False)
    print(f"Final features saved to: {FINAL_FEATURES_FILE}")

    print("=" * 60)
    return merged, features, ids, encoders


if __name__ == "__main__":
    preprocess_pipeline()
