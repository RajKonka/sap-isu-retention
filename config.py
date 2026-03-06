"""
SAP IS-U Customer Retention Prediction System — V3 Configuration
Lean version: Only Customer Master + Complaints + Interactions
"""
import os

# ─── Directories ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# ─── Data Files (3 inputs only) ───────────────────────────
CUSTOMER_MASTER_FILE = os.path.join(DATA_DIR, "customer_master.csv")
COMPLAINT_DATA_FILE = os.path.join(DATA_DIR, "complaint_data.csv")
INTERACTION_DATA_FILE = os.path.join(DATA_DIR, "interaction_data.csv")

# ─── Derived Files ────────────────────────────────────────
MERGED_DATA_FILE = os.path.join(DATA_DIR, "merged_customer_data.csv")
FINAL_FEATURES_FILE = os.path.join(DATA_DIR, "final_features.csv")

# ─── Model Settings ───────────────────────────────────────
TARGET_COLUMN = "churned"
TEST_SIZE = 0.2
RANDOM_STATE = 42
NUM_CUSTOMERS = 5000

# ─── SAP IS-U Table Mapping (for documentation) ──────────
SAP_TABLE_MAP = {
    "customer_master": {
        "sap_tables": "BUT000 (Business Partner), FKKVKP (Contract Account), EVER (Installation)",
        "transaction": "SE16N, BP, ES32",
        "description": "Core customer identity — who they are, how long they've been with you, what contract they have",
    },
    "complaint_data": {
        "sap_tables": "CRM_ORDERADM_H (Service Orders), CRMD_ORDERADM_H, Custom Z-tables",
        "transaction": "CRM_ORDER, IW51 (Notification)",
        "description": "Customer complaints with free-text comments — the raw voice of the customer",
    },
    "interaction_data": {
        "sap_tables": "CRM_ORDERADM_H (Interaction Records), SCMG_T_CASE_ATTR",
        "transaction": "CRM_ORDER, IC_INBOX",
        "description": "Every touchpoint — calls, emails, web chats, in-person visits and their outcomes",
    },
}

# ─── Feature Groups ───────────────────────────────────────
CUSTOMER_FEATURES = [
    "account_tenure_months", "age", "contract_type", "service_type",
    "dwelling_type", "has_autopay", "paperless_billing", "family_size",
    "income_bracket", "home_ownership", "region", "gender",
]

COMPLAINT_FEATURES = [
    "complaint_count", "avg_complaint_severity", "max_complaint_severity",
    "avg_resolution_time_days", "escalation_count", "escalation_rate",
    "unresolved_complaints", "complaint_rate_per_month",
    "most_common_complaint_category",
]

SENTIMENT_FEATURES = [
    "avg_sentiment_score", "min_sentiment_score", "max_sentiment_score",
    "sentiment_std", "avg_sentiment_pos", "avg_sentiment_neg",
    "negative_sentiment_ratio", "positive_sentiment_ratio",
]

INTERACTION_FEATURES = [
    "total_interactions", "avg_satisfaction_score", "min_satisfaction_score",
    "avg_interaction_duration", "unresolved_count", "unresolved_ratio",
    "channel_phone_ratio", "channel_email_ratio", "channel_web_ratio",
    "interactions_per_month",
]

ENGINEERED_FEATURES = [
    "engagement_score", "composite_risk_score",
    "complaint_risk_flag", "low_satisfaction_flag",
    "high_negative_sentiment_flag", "very_negative_sentiment_flag",
    "sentiment_volatile_flag", "new_customer_flag",
    "frequent_caller_flag", "unresolved_issues_flag",
]
