"""
Exploratory Data Analysis (EDA) Module
Generates visualizations and statistical summaries for the customer retention dataset.
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

sns.set_theme(style="whitegrid", palette="husl")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 100


def generate_eda_report(merged_df):
    """Generate comprehensive EDA visualizations and statistics."""
    print("=" * 60)
    print("EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_stats = {}

    # ── 1. Dataset Overview ──
    print("\n[1] Dataset Overview")
    print(f"  Shape: {merged_df.shape}")
    print(f"  Churn Rate: {merged_df['churned'].mean():.2%}")
    report_stats["total_customers"] = len(merged_df)
    report_stats["churn_rate"] = merged_df["churned"].mean()
    report_stats["num_features"] = merged_df.shape[1]

    # Missing values
    missing = merged_df.isnull().sum()
    missing_pct = (missing / len(merged_df) * 100).round(2)
    missing_report = pd.DataFrame({"missing_count": missing, "missing_pct": missing_pct})
    missing_report = missing_report[missing_report["missing_count"] > 0].sort_values("missing_pct", ascending=False)
    if not missing_report.empty:
        print(f"  Columns with missing values: {len(missing_report)}")
    else:
        print("  No missing values found!")

    # ── 2. Churn Distribution ──
    print("\n[2] Generating Churn Distribution Plot...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Pie chart
    churn_counts = merged_df["churned"].value_counts()
    axes[0].pie(churn_counts, labels=["Retained", "Churned"],
                autopct="%1.1f%%", colors=["#2ecc71", "#e74c3c"],
                explode=[0, 0.05], shadow=True, startangle=90)
    axes[0].set_title("Customer Churn Distribution", fontsize=14, fontweight="bold")

    # Bar chart by region
    churn_by_region = merged_df.groupby("region")["churned"].mean().sort_values(ascending=False)
    churn_by_region.plot(kind="bar", ax=axes[1], color="#3498db", edgecolor="white")
    axes[1].set_title("Churn Rate by Region", fontsize=14, fontweight="bold")
    axes[1].set_ylabel("Churn Rate")
    axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=45, ha="right")
    axes[1].axhline(y=merged_df["churned"].mean(), color="red", linestyle="--", label="Overall")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "01_churn_distribution.png"), bbox_inches="tight")
    plt.close()

    # ── 3. Demographics Analysis ──
    print("[3] Generating Demographics Analysis...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Age distribution by churn
    for label, color in [(0, "#2ecc71"), (1, "#e74c3c")]:
        subset = merged_df[merged_df["churned"] == label]["age"]
        axes[0, 0].hist(subset, bins=30, alpha=0.6, color=color,
                        label="Retained" if label == 0 else "Churned", edgecolor="white")
    axes[0, 0].set_title("Age Distribution by Churn Status", fontweight="bold")
    axes[0, 0].set_xlabel("Age")
    axes[0, 0].legend()

    # Tenure distribution
    for label, color in [(0, "#2ecc71"), (1, "#e74c3c")]:
        subset = merged_df[merged_df["churned"] == label]["account_tenure_months"]
        axes[0, 1].hist(subset, bins=30, alpha=0.6, color=color,
                        label="Retained" if label == 0 else "Churned", edgecolor="white")
    axes[0, 1].set_title("Tenure Distribution by Churn Status", fontweight="bold")
    axes[0, 1].set_xlabel("Months")
    axes[0, 1].legend()

    # Churn by contract type
    ct = merged_df.groupby("contract_type")["churned"].mean().sort_values(ascending=False)
    ct.plot(kind="bar", ax=axes[1, 0], color=["#e74c3c", "#f39c12", "#2ecc71"], edgecolor="white")
    axes[1, 0].set_title("Churn Rate by Contract Type", fontweight="bold")
    axes[1, 0].set_ylabel("Churn Rate")
    axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=0)

    # Churn by income bracket
    ib = merged_df.groupby("income_bracket")["churned"].mean().sort_values(ascending=False)
    ib.plot(kind="bar", ax=axes[1, 1], color="#9b59b6", edgecolor="white")
    axes[1, 1].set_title("Churn Rate by Income Bracket", fontweight="bold")
    axes[1, 1].set_ylabel("Churn Rate")
    axes[1, 1].set_xticklabels(axes[1, 1].get_xticklabels(), rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "02_demographics_analysis.png"), bbox_inches="tight")
    plt.close()

    # ── 4. Billing & Payment Analysis ──
    print("[4] Generating Billing & Payment Analysis...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Avg bill by churn
    for i, (col, title) in enumerate([
        ("avg_monthly_bill", "Avg Monthly Bill"),
        ("payment_delay_avg_days", "Avg Payment Delay (Days)"),
        ("late_payments_count", "Late Payments Count"),
        ("billing_disputes_count", "Billing Disputes Count"),
    ]):
        ax = axes[i // 2, i % 2]
        if col in merged_df.columns:
            merged_df.boxplot(column=col, by="churned", ax=ax)
            ax.set_title(f"{title} by Churn Status", fontweight="bold")
            ax.set_xlabel("Churned (0=No, 1=Yes)")
            ax.set_ylabel(title)
        plt.suptitle("")

    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "03_billing_analysis.png"), bbox_inches="tight")
    plt.close()

    # ── 5. Interaction & Complaint Analysis ──
    print("[5] Generating Interaction & Complaint Analysis...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    for i, (col, title) in enumerate([
        ("complaint_count", "Number of Complaints"),
        ("avg_complaint_severity", "Avg Complaint Severity"),
        ("avg_satisfaction_score", "Avg Satisfaction Score"),
        ("negative_sentiment_ratio", "Negative Sentiment Ratio"),
    ]):
        ax = axes[i // 2, i % 2]
        if col in merged_df.columns:
            merged_df.boxplot(column=col, by="churned", ax=ax)
            ax.set_title(f"{title} by Churn Status", fontweight="bold")
            ax.set_xlabel("Churned (0=No, 1=Yes)")
            ax.set_ylabel(title)
        plt.suptitle("")

    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "04_interaction_analysis.png"), bbox_inches="tight")
    plt.close()

    # ── 6. Correlation Heatmap ──
    print("[6] Generating Correlation Heatmap...")
    numeric_df = merged_df.select_dtypes(include=[np.number])
    # Select top correlated features with churn
    if "churned" in numeric_df.columns:
        corr_with_churn = numeric_df.corr()["churned"].abs().sort_values(ascending=False)
        top_features = corr_with_churn.head(20).index.tolist()
        corr_matrix = numeric_df[top_features].corr()

        fig, ax = plt.subplots(figsize=(16, 14))
        sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="RdYlBu_r",
                    center=0, square=True, ax=ax, cbar_kws={"shrink": 0.8})
        ax.set_title("Top 20 Feature Correlations with Churn", fontsize=16, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "05_correlation_heatmap.png"), bbox_inches="tight")
        plt.close()

    # ── 7. Key Statistics Summary ──
    print("[7] Computing Key Statistics...")
    if "churned" in merged_df.columns:
        churned = merged_df[merged_df["churned"] == 1]
        retained = merged_df[merged_df["churned"] == 0]

        key_cols = [
            "avg_monthly_bill", "complaint_count", "avg_satisfaction_score",
            "account_tenure_months", "payment_delay_avg_days", "negative_sentiment_ratio"
        ]
        stats_comparison = pd.DataFrame()
        for col in key_cols:
            if col in merged_df.columns:
                stats_comparison.loc[col, "Churned_Mean"] = churned[col].mean()
                stats_comparison.loc[col, "Retained_Mean"] = retained[col].mean()
                stats_comparison.loc[col, "Difference"] = churned[col].mean() - retained[col].mean()
                stats_comparison.loc[col, "Pct_Diff"] = (
                    (churned[col].mean() - retained[col].mean()) /
                    retained[col].mean() * 100 if retained[col].mean() != 0 else 0
                )

        stats_comparison.to_csv(os.path.join(REPORT_DIR, "eda_statistics.csv"))
        report_stats["key_differences"] = stats_comparison.to_dict()
        print("\n  Key Differences (Churned vs Retained):")
        print(stats_comparison.round(3).to_string())

    print(f"\n  All EDA plots saved to: {REPORT_DIR}")
    print("=" * 60)

    return report_stats


if __name__ == "__main__":
    merged = pd.read_csv(MERGED_DATA_FILE)
    generate_eda_report(merged)
