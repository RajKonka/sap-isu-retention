"""
EDA Module — V3
Generates visual analysis reports with explanations.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


def generate_eda_report(df):
    """Generate EDA visualizations from merged data."""
    print("Generating EDA report...")
    os.makedirs(REPORT_DIR, exist_ok=True)

    # 1. Churn distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    if TARGET_COLUMN in df.columns:
        counts = df[TARGET_COLUMN].value_counts()
        colors = ["#27ae60", "#e74c3c"]
        ax.bar(["Retained", "Churned"], [counts.get(0, 0), counts.get(1, 0)], color=colors, edgecolor="white")
        ax.set_title("Churn Distribution", fontsize=14, fontweight="bold")
        ax.set_ylabel("Count")
        for i, v in enumerate([counts.get(0, 0), counts.get(1, 0)]):
            ax.text(i, v + 20, f"{v:,}", ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "01_churn_distribution.png"), bbox_inches="tight")
    plt.close()

    # 2. Tenure vs Churn
    if "account_tenure_months" in df.columns and TARGET_COLUMN in df.columns:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, group in df.groupby(TARGET_COLUMN):
            name = "Churned" if label == 1 else "Retained"
            color = "#e74c3c" if label == 1 else "#27ae60"
            ax.hist(group["account_tenure_months"], bins=30, alpha=0.6, label=name, color=color)
        ax.set_title("Account Tenure Distribution by Churn Status", fontsize=14, fontweight="bold")
        ax.set_xlabel("Tenure (months)")
        ax.set_ylabel("Count")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "02_tenure_vs_churn.png"), bbox_inches="tight")
        plt.close()

    # 3. Complaint count vs Churn
    if "complaint_count" in df.columns and TARGET_COLUMN in df.columns:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, group in df.groupby(TARGET_COLUMN):
            name = "Churned" if label == 1 else "Retained"
            color = "#e74c3c" if label == 1 else "#27ae60"
            ax.hist(group["complaint_count"], bins=20, alpha=0.6, label=name, color=color)
        ax.set_title("Complaint Count Distribution by Churn Status", fontsize=14, fontweight="bold")
        ax.set_xlabel("Number of Complaints")
        ax.set_ylabel("Count")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "03_complaints_vs_churn.png"), bbox_inches="tight")
        plt.close()

    # 4. Sentiment Score vs Churn
    if "avg_sentiment_score" in df.columns and TARGET_COLUMN in df.columns:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, group in df.groupby(TARGET_COLUMN):
            name = "Churned" if label == 1 else "Retained"
            color = "#e74c3c" if label == 1 else "#27ae60"
            ax.hist(group["avg_sentiment_score"], bins=30, alpha=0.6, label=name, color=color)
        ax.set_title("NLP Sentiment Score Distribution by Churn Status", fontsize=14, fontweight="bold")
        ax.set_xlabel("Average Sentiment Score (-1 to +1)")
        ax.set_ylabel("Count")
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "04_sentiment_vs_churn.png"), bbox_inches="tight")
        plt.close()

    # 5. Satisfaction vs Churn
    if "avg_satisfaction_score" in df.columns and TARGET_COLUMN in df.columns:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, group in df.groupby(TARGET_COLUMN):
            name = "Churned" if label == 1 else "Retained"
            color = "#e74c3c" if label == 1 else "#27ae60"
            ax.hist(group["avg_satisfaction_score"], bins=20, alpha=0.6, label=name, color=color)
        ax.set_title("Satisfaction Score Distribution by Churn Status", fontsize=14, fontweight="bold")
        ax.set_xlabel("Average Satisfaction (1-5)")
        ax.set_ylabel("Count")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "05_satisfaction_vs_churn.png"), bbox_inches="tight")
        plt.close()

    # Save statistics
    if TARGET_COLUMN in df.columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if TARGET_COLUMN in numeric_cols:
            numeric_cols.remove(TARGET_COLUMN)
        stats = df.groupby(TARGET_COLUMN)[numeric_cols].mean()
        stats.to_csv(os.path.join(REPORT_DIR, "eda_statistics.csv"))

    print(f"  EDA report saved to {REPORT_DIR}/")
