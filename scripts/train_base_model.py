"""
Base Model Training Script
Generates 15,000 high-quality synthetic utility customers and trains the
permanent baseline model saved to models/base/.

This model is what Predict Only mode uses when a user uploads data without
historical churn labels. Run this once; commit the artifacts.

Usage:
    venv/bin/python scripts/train_base_model.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BASE_MODEL_DIR  = os.path.join(ROOT, "models", "base")
BASE_DATA_DIR   = os.path.join(ROOT, "data",   "base_training")
BASE_REPORT_DIR = os.path.join(ROOT, "data",   "base_training", "reports")

BASE_DIRS = {
    "data_dir":              BASE_DATA_DIR,
    "model_dir":             BASE_MODEL_DIR,
    "report_dir":            BASE_REPORT_DIR,
    "customer_master_file":  os.path.join(BASE_DATA_DIR, "customer_master.csv"),
    "complaint_data_file":   os.path.join(BASE_DATA_DIR, "complaint_data.csv"),
    "interaction_data_file": os.path.join(BASE_DATA_DIR, "interaction_data.csv"),
    "merged_data_file":      os.path.join(BASE_DATA_DIR, "merged_customer_data.csv"),
    "final_features_file":   os.path.join(BASE_DATA_DIR, "final_features.csv"),
}

N_TRAINING = 15_000


def main():
    os.makedirs(BASE_MODEL_DIR,  exist_ok=True)
    os.makedirs(BASE_DATA_DIR,   exist_ok=True)
    os.makedirs(BASE_REPORT_DIR, exist_ok=True)

    print("=" * 65)
    print("BASE MODEL TRAINING")
    print(f"  Customers : {N_TRAINING:,}")
    print(f"  Output    : {BASE_MODEL_DIR}")
    print("=" * 65)

    # ── Step 1: Generate high-quality synthetic training data ──────
    print("\n[1/4] Generating training data...")
    from src.data_generator import (
        generate_customer_master,
        generate_complaint_data,
        generate_interaction_data,
        generate_churn_labels,
    )

    master       = generate_customer_master(n=N_TRAINING)
    complaints   = generate_complaint_data(master["customer_id"].tolist())
    interactions = generate_interaction_data(master["customer_id"].tolist())
    master["churned"] = generate_churn_labels(master, complaints, interactions)

    churn_rate = master["churned"].mean()
    print(f"  Churn rate: {churn_rate:.1%}  ({master['churned'].sum():,} churned / {N_TRAINING:,} total)")

    if not (0.10 <= churn_rate <= 0.45):
        print(f"  WARNING: Churn rate {churn_rate:.1%} is outside the expected 10–45% range.")
        print("  Check generate_churn_labels() in data_generator.py.")

    master.to_csv(BASE_DIRS["customer_master_file"],  index=False)
    complaints.to_csv(BASE_DIRS["complaint_data_file"],   index=False)
    interactions.to_csv(BASE_DIRS["interaction_data_file"], index=False)

    # ── Step 2: Preprocessing + feature engineering ────────────────
    print("\n[2/4] Preprocessing and feature engineering...")
    from src.data_preprocessing import preprocess_pipeline
    from src.feature_engineering import engineer_features

    merged, features, ids, _ = preprocess_pipeline(dirs=BASE_DIRS)
    engineered = engineer_features(merged, dirs=BASE_DIRS)
    print(f"  Feature matrix: {engineered.shape[0]:,} rows × {engineered.shape[1]} columns")

    # ── Step 3: Train models ────────────────────────────────────────
    print("\n[3/4] Training models...")
    from src.model_training import training_pipeline

    results, trained_models, best_name, scaler = training_pipeline(
        engineered, dirs=BASE_DIRS
    )

    # ── Step 4: Report ──────────────────────────────────────────────
    print("\n[4/4] Results")
    print("-" * 55)
    print(f"{'Model':<28} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}")
    print("-" * 55)
    for name, m in results.items():
        marker = " ✓" if name == best_name else ""
        print(
            f"{name:<28} {m['accuracy']:>6.1%} {m['precision']:>6.1%} "
            f"{m['recall']:>6.1%} {m['f1']:>6.1%} {m['roc_auc']:>6.3f}{marker}"
        )
    print("-" * 55)
    print(f"\nBest model : {best_name}")
    print(f"Artifacts  : {BASE_MODEL_DIR}")
    print("\nBase model training complete.")
    print("Commit models/base/ to include it in the repository.")


if __name__ == "__main__":
    main()
