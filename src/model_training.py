"""
Model Training Module
Trains multiple ML models for churn prediction:
- Logistic Regression
- Random Forest
- Gradient Boosting (XGBoost)
- LightGBM
- Ensemble (Voting/Stacking)

Includes cross-validation, hyperparameter tuning, and model evaluation.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    VotingClassifier, StackingClassifier
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, precision_recall_curve
)
import joblib
import warnings
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

warnings.filterwarnings("ignore")


def prepare_data(df):
    """Prepare features and target for model training."""
    print("Preparing data for training...")

    # Drop non-feature columns
    drop_cols = ["customer_id", "customer_name", "account_start_date"]
    df_ml = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    # Encode categoricals
    cat_cols = df_ml.select_dtypes(include=["object", "category"]).columns.tolist()
    if TARGET_COLUMN in cat_cols:
        cat_cols.remove(TARGET_COLUMN)

    label_encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df_ml[col] = le.fit_transform(df_ml[col].astype(str))
        label_encoders[col] = le

    # Fill NaN
    df_ml = df_ml.fillna(0)

    # Split features and target
    X = df_ml.drop(columns=[TARGET_COLUMN])
    y = df_ml[TARGET_COLUMN]

    print(f"  Features: {X.shape[1]}, Samples: {X.shape[0]}")
    print(f"  Target distribution: {y.value_counts().to_dict()}")
    print(f"  Churn rate: {y.mean():.2%}")

    return X, y, label_encoders


def train_models(X_train, y_train, X_test, y_test):
    """Train multiple models and evaluate them."""
    print("\n" + "=" * 60)
    print("MODEL TRAINING")
    print("=" * 60)

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE, C=0.5
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_split=10,
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            subsample=0.8, random_state=RANDOM_STATE
        ),
    }

    # Try to use LightGBM if available
    try:
        import lightgbm as lgb
        models["LightGBM"] = lgb.LGBMClassifier(
            n_estimators=200, max_depth=8, learning_rate=0.1,
            class_weight="balanced", random_state=RANDOM_STATE,
            verbose=-1, n_jobs=-1
        )
    except ImportError:
        print("  LightGBM not available, skipping...")

    results = {}
    trained_models = {}

    for name, model in models.items():
        print(f"\n  Training {name}...")

        # Train
        model.fit(X_train, y_train)
        trained_models[name] = model

        # Predict
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")

        # Metrics
        results[name] = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_prob),
            "cv_auc_mean": cv_scores.mean(),
            "cv_auc_std": cv_scores.std(),
        }

        print(f"    Accuracy: {results[name]['accuracy']:.4f}")
        print(f"    F1 Score: {results[name]['f1']:.4f}")
        print(f"    ROC AUC:  {results[name]['roc_auc']:.4f}")
        print(f"    CV AUC:   {results[name]['cv_auc_mean']:.4f} ± {results[name]['cv_auc_std']:.4f}")

    # ── Ensemble Model ──
    print(f"\n  Training Ensemble (Soft Voting)...")
    ensemble_estimators = [(name, model) for name, model in trained_models.items()]
    ensemble = VotingClassifier(estimators=ensemble_estimators, voting="soft")
    ensemble.fit(X_train, y_train)

    y_pred_ens = ensemble.predict(X_test)
    y_prob_ens = ensemble.predict_proba(X_test)[:, 1]

    results["Ensemble (Voting)"] = {
        "accuracy": accuracy_score(y_test, y_pred_ens),
        "precision": precision_score(y_test, y_pred_ens, zero_division=0),
        "recall": recall_score(y_test, y_pred_ens, zero_division=0),
        "f1": f1_score(y_test, y_pred_ens, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob_ens),
        "cv_auc_mean": 0,
        "cv_auc_std": 0,
    }
    trained_models["Ensemble (Voting)"] = ensemble

    print(f"    Accuracy: {results['Ensemble (Voting)']['accuracy']:.4f}")
    print(f"    F1 Score: {results['Ensemble (Voting)']['f1']:.4f}")
    print(f"    ROC AUC:  {results['Ensemble (Voting)']['roc_auc']:.4f}")

    return results, trained_models


def get_best_model(results, trained_models):
    """Select best model based on ROC AUC."""
    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    print(f"\n  Best Model: {best_name} (ROC AUC: {results[best_name]['roc_auc']:.4f})")
    return best_name, trained_models[best_name]


def plot_model_comparison(results, X_test, y_test, trained_models):
    """Generate model comparison visualizations."""
    print("\nGenerating model comparison plots...")
    os.makedirs(REPORT_DIR, exist_ok=True)

    # ── 1. Metrics Comparison Bar Chart ──
    metrics_df = pd.DataFrame(results).T
    fig, ax = plt.subplots(figsize=(14, 6))
    metrics_df[["accuracy", "precision", "recall", "f1", "roc_auc"]].plot(
        kind="bar", ax=ax, edgecolor="white", width=0.8
    )
    ax.set_title("Model Performance Comparison", fontsize=16, fontweight="bold")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="lower right")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "06_model_comparison.png"), bbox_inches="tight")
    plt.close()

    # ── 2. ROC Curves ──
    fig, ax = plt.subplots(figsize=(10, 8))
    for name, model in trained_models.items():
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test)[:, 1]
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            auc = roc_auc_score(y_test, y_prob)
            ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})", linewidth=2)

    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title("ROC Curves - All Models", fontsize=16, fontweight="bold")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "07_roc_curves.png"), bbox_inches="tight")
    plt.close()

    # ── 3. Best Model - Confusion Matrix ──
    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best_model = trained_models[best_name]
    y_pred = best_model.predict(X_test)

    fig, ax = plt.subplots(figsize=(8, 6))
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["Retained", "Churned"],
                yticklabels=["Retained", "Churned"])
    ax.set_title(f"Confusion Matrix - {best_name}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "08_confusion_matrix.png"), bbox_inches="tight")
    plt.close()

    # ── 4. Feature Importance ──
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
    elif best_name == "Ensemble (Voting)":
        # Get from best non-ensemble model
        for n, m in trained_models.items():
            if n != "Ensemble (Voting)" and hasattr(m, "feature_importances_"):
                importances = m.feature_importances_
                break
    else:
        importances = None

    if importances is not None:
        feat_imp = pd.Series(importances, index=X_test.columns).sort_values(ascending=True)
        top_20 = feat_imp.tail(20)

        fig, ax = plt.subplots(figsize=(12, 8))
        top_20.plot(kind="barh", ax=ax, color="#3498db", edgecolor="white")
        ax.set_title("Top 20 Feature Importances", fontsize=16, fontweight="bold")
        ax.set_xlabel("Importance")
        plt.tight_layout()
        plt.savefig(os.path.join(REPORT_DIR, "09_feature_importance.png"), bbox_inches="tight")
        plt.close()

    return metrics_df


def save_models(trained_models, best_name, label_encoders, feature_names):
    """Save trained models and metadata."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    for name, model in trained_models.items():
        safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        joblib.dump(model, os.path.join(MODEL_DIR, f"{safe_name}.pkl"))

    # Save best model separately
    joblib.dump(trained_models[best_name], os.path.join(MODEL_DIR, "best_model.pkl"))

    # Save metadata
    metadata = {
        "best_model_name": best_name,
        "feature_names": list(feature_names),
        "label_encoders": label_encoders,
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, "model_metadata.pkl"))

    print(f"\n  Models saved to: {MODEL_DIR}")
    print(f"  Best model: {best_name}")


def training_pipeline(df):
    """Run the complete model training pipeline."""
    print("=" * 60)
    print("ML TRAINING PIPELINE")
    print("=" * 60)

    # Prepare data
    X, y, label_encoders = prepare_data(df)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\n  Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)

    # Save scaler
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))

    # Train models
    results, trained_models = train_models(X_train_scaled, y_train, X_test_scaled, y_test)

    # Get best model
    best_name, best_model = get_best_model(results, trained_models)

    # Plot comparisons
    metrics_df = plot_model_comparison(results, X_test_scaled, y_test, trained_models)

    # Save models
    save_models(trained_models, best_name, label_encoders, X.columns)

    # Save results
    metrics_df.to_csv(os.path.join(REPORT_DIR, "model_results.csv"))

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)

    return results, trained_models, best_name, scaler


if __name__ == "__main__":
    df = pd.read_csv(FINAL_FEATURES_FILE)
    training_pipeline(df)
