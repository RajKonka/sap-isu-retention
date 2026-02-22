"""
Configuration file for SAP IS-U Customer Retention Prediction System
"""
import os

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# ─── Data Files ──────────────────────────────────────────
CUSTOMER_MASTER_FILE = os.path.join(DATA_DIR, "customer_master.csv")
BILLING_DATA_FILE = os.path.join(DATA_DIR, "billing_data.csv")
INTERACTION_DATA_FILE = os.path.join(DATA_DIR, "interaction_data.csv")
COMPLAINT_DATA_FILE = os.path.join(DATA_DIR, "complaint_data.csv")
CONSUMPTION_DATA_FILE = os.path.join(DATA_DIR, "consumption_data.csv")
PAYMENT_DATA_FILE = os.path.join(DATA_DIR, "payment_data.csv")
DEMOGRAPHICS_EXTERNAL_FILE = os.path.join(DATA_DIR, "external_demographics.csv")
MERGED_DATA_FILE = os.path.join(DATA_DIR, "merged_customer_data.csv")
FINAL_FEATURES_FILE = os.path.join(DATA_DIR, "final_features.csv")

# ─── Model Config ────────────────────────────────────────
TARGET_COLUMN = "churned"
CUSTOMER_ID_COL = "customer_id"
TEST_SIZE = 0.2
RANDOM_STATE = 42

# ─── Synthetic Data Config ───────────────────────────────
NUM_CUSTOMERS = 5000
CHURN_RATE = 0.18  # ~18% churn rate typical for utilities

# ─── Anthropic API ───────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ─── Feature Groups ─────────────────────────────────────
DEMOGRAPHIC_FEATURES = [
    "age", "gender", "region", "account_tenure_months",
    "family_size", "income_bracket", "home_ownership",
    "dwelling_type"
]

BILLING_FEATURES = [
    "avg_monthly_bill", "bill_std", "payment_delay_avg_days",
    "late_payments_count", "total_revenue", "billing_disputes_count"
]

INTERACTION_FEATURES = [
    "total_interactions", "complaint_count", "avg_complaint_severity",
    "avg_resolution_time_days", "avg_satisfaction_score",
    "negative_sentiment_ratio", "positive_sentiment_ratio",
    "avg_sentiment_score", "min_sentiment_score", "sentiment_std",
    "avg_sentiment_pos", "avg_sentiment_neg", "channel_diversity"
]

CONSUMPTION_FEATURES = [
    "avg_monthly_consumption", "consumption_trend",
    "consumption_volatility", "peak_to_avg_ratio"
]

SERVICE_FEATURES = [
    "service_type", "contract_type", "has_autopay",
    "paperless_billing", "num_service_changes",
    "outage_count_experienced"
]
