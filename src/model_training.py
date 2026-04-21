"""
Model Training Module — V3 (Weighted Features)
Trains ML models with optional user-configurable feature weights.
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
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, roc_curve
import joblib
import warnings
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
warnings.filterwarnings("ignore")

# ─── Training Explanations (displayed in app) ─────────────
TRAINING_EXPLANATIONS = {
    "logistic_regression": {
        "what": "A statistical model that finds the best linear boundary between churned and retained customers.",
        "why": "Fast, interpretable, and gives probability scores. Good baseline — if this does well, the data has clear patterns.",
        "strength": "Tells you exactly which features matter most (positive/negative coefficients).",
        "weakness": "Struggles with complex non-linear relationships between features.",
    },
    "random_forest": {
        "what": "200 decision trees that each vote on whether a customer will churn. Majority wins.",
        "why": "Handles messy data well, doesn't need perfect feature scaling, and captures complex interactions.",
        "strength": "Feature importance ranking shows which inputs drive predictions.",
        "weakness": "Can overfit on small datasets. Slower to train than logistic regression.",
    },
    "gradient_boosting": {
        "what": "Builds trees one at a time, where each new tree fixes the mistakes of the previous ones.",
        "why": "Often the most accurate model for tabular data. Learns incrementally from errors.",
        "strength": "Very high accuracy. Good at finding subtle patterns.",
        "weakness": "Slower to train. More complex to tune.",
    },
    "lightgbm": {
        "what": "Microsoft's optimized gradient boosting. Same concept but much faster.",
        "why": "Production-grade speed with gradient boosting accuracy. Industry standard for churn prediction.",
        "strength": "Fast training, handles categorical features natively, memory efficient.",
        "weakness": "Requires an extra package install.",
    },
    "ensemble": {
        "what": "All 4 models vote together. The combined prediction is more stable than any single model.",
        "why": "Reduces the risk of any single model being wrong. Like getting a second (and third) opinion.",
        "strength": "Most robust predictions. Smooths out individual model quirks.",
        "weakness": "Slower at prediction time (runs all models). Harder to explain to stakeholders.",
    },
    "metrics": {
        "accuracy": "% of all predictions that were correct. Can be misleading if churn rate is very low/high.",
        "precision": "Of customers we flagged as 'will churn', what % actually churned. High precision = fewer false alarms.",
        "recall": "Of customers who actually churned, what % did we catch? High recall = fewer missed churners.",
        "f1": "Balance between precision and recall. Best single metric for churn prediction.",
        "roc_auc": "How well the model separates churners from stayers across all thresholds. 1.0 = perfect, 0.5 = random.",
    },
}


def prepare_data(df, feature_multipliers=None):
    """Prepare features and target, optionally applying weight multipliers."""
    print("Preparing data for training...")
    drop_cols = ["customer_id", "customer_name", "account_start_date", "most_common_complaint_category"]
    df_ml = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    cat_cols = df_ml.select_dtypes(include=["object", "category"]).columns.tolist()
    if TARGET_COLUMN in cat_cols:
        cat_cols.remove(TARGET_COLUMN)

    label_encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df_ml[col] = le.fit_transform(df_ml[col].astype(str))
        label_encoders[col] = le

    df_ml = df_ml.fillna(0)
    X = df_ml.drop(columns=[TARGET_COLUMN])
    y = df_ml[TARGET_COLUMN]

    if feature_multipliers:
        applied = 0
        for col in X.columns:
            if col in feature_multipliers:
                X[col] = X[col] * feature_multipliers[col]
                applied += 1
        print(f"  Applied weight multipliers to {applied}/{len(X.columns)} features")

    print(f"  Features: {X.shape[1]}, Samples: {X.shape[0]}")
    print(f"  Churn rate: {y.mean():.2%}")
    return X, y, label_encoders


def train_models(X_train, y_train, X_test, y_test):
    """Train multiple models and evaluate."""
    print("\n" + "=" * 60)
    print("MODEL TRAINING")
    print("=" * 60)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE, C=0.5),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_split=10, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, subsample=0.8, random_state=RANDOM_STATE),
    }

    try:
        import lightgbm as lgb
        models["LightGBM"] = lgb.LGBMClassifier(n_estimators=200, max_depth=8, learning_rate=0.1, class_weight="balanced", random_state=RANDOM_STATE, verbose=-1, n_jobs=-1)
    except ImportError:
        print("  LightGBM not available, skipping...")

    results = {}
    trained_models = {}
    for name, model in models.items():
        print(f"\n  Training {name}...")
        model.fit(X_train, y_train)
        trained_models[name] = model
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        try:
            cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")
        except Exception:
            cv_scores = np.array([0.5])
        results[name] = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_prob),
            "cv_auc_mean": cv_scores.mean(),
            "cv_auc_std": cv_scores.std(),
        }
        print(f"    F1: {results[name]['f1']:.4f} | ROC AUC: {results[name]['roc_auc']:.4f}")

    # Ensemble
    print(f"\n  Training Ensemble (Soft Voting)...")
    ensemble = VotingClassifier(estimators=[(n, m) for n, m in trained_models.items()], voting="soft")
    ensemble.fit(X_train, y_train)
    y_pred_ens = ensemble.predict(X_test)
    y_prob_ens = ensemble.predict_proba(X_test)[:, 1]
    results["Ensemble (Voting)"] = {
        "accuracy": accuracy_score(y_test, y_pred_ens),
        "precision": precision_score(y_test, y_pred_ens, zero_division=0),
        "recall": recall_score(y_test, y_pred_ens, zero_division=0),
        "f1": f1_score(y_test, y_pred_ens, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob_ens),
        "cv_auc_mean": 0, "cv_auc_std": 0,
    }
    trained_models["Ensemble (Voting)"] = ensemble
    return results, trained_models


def get_best_model(results, trained_models):
    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    print(f"\n  Best Model: {best_name} (ROC AUC: {results[best_name]['roc_auc']:.4f})")
    return best_name, trained_models[best_name]


def plot_model_comparison(results, X_test, y_test, trained_models, dirs=None):
    _report_dir = (dirs or {}).get("report_dir", REPORT_DIR)
    os.makedirs(_report_dir, exist_ok=True)
    metrics_df = pd.DataFrame(results).T

    fig, ax = plt.subplots(figsize=(14, 6))
    metrics_df[["accuracy", "precision", "recall", "f1", "roc_auc"]].plot(kind="bar", ax=ax, edgecolor="white", width=0.8)
    ax.set_title("Model Performance Comparison", fontsize=16, fontweight="bold")
    ax.set_ylabel("Score"); ax.set_ylim(0, 1.05); ax.legend(loc="lower right")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout(); plt.savefig(os.path.join(_report_dir, "06_model_comparison.png"), bbox_inches="tight"); plt.close()

    fig, ax = plt.subplots(figsize=(10, 8))
    for name, model in trained_models.items():
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test)[:, 1]
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            auc = roc_auc_score(y_test, y_prob)
            ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})", linewidth=2)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves", fontsize=16, fontweight="bold"); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(os.path.join(_report_dir, "07_roc_curves.png"), bbox_inches="tight"); plt.close()

    best_name = max(results, key=lambda k: results[k]["roc_auc"])
    best_model = trained_models[best_name]; y_pred = best_model.predict(X_test)
    fig, ax = plt.subplots(figsize=(8, 6))
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax, xticklabels=["Retained", "Churned"], yticklabels=["Retained", "Churned"])
    ax.set_title(f"Confusion Matrix - {best_name}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    plt.tight_layout(); plt.savefig(os.path.join(_report_dir, "08_confusion_matrix.png"), bbox_inches="tight"); plt.close()

    importances = None
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
    elif best_name == "Ensemble (Voting)":
        for n, m in trained_models.items():
            if n != "Ensemble (Voting)" and hasattr(m, "feature_importances_"):
                importances = m.feature_importances_; break
    if importances is not None:
        feat_imp = pd.Series(importances, index=X_test.columns).sort_values(ascending=True).tail(20)
        fig, ax = plt.subplots(figsize=(12, 8))
        feat_imp.plot(kind="barh", ax=ax, color="#667eea", edgecolor="white")
        ax.set_title("Top 20 Feature Importances", fontsize=16, fontweight="bold"); ax.set_xlabel("Importance")
        plt.tight_layout(); plt.savefig(os.path.join(_report_dir, "09_feature_importance.png"), bbox_inches="tight"); plt.close()

    return metrics_df


def save_models(trained_models, best_name, label_encoders, feature_names, feature_multipliers=None, dirs=None):
    _model_dir = (dirs or {}).get("model_dir", MODEL_DIR)
    os.makedirs(_model_dir, exist_ok=True)
    for name, model in trained_models.items():
        safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        joblib.dump(model, os.path.join(_model_dir, f"{safe_name}.pkl"))
    joblib.dump(trained_models[best_name], os.path.join(_model_dir, "best_model.pkl"))
    metadata = {
        "best_model_name": best_name,
        "feature_names": list(feature_names),
        "label_encoders": label_encoders,
        "feature_multipliers": feature_multipliers or {},
    }
    joblib.dump(metadata, os.path.join(_model_dir, "model_metadata.pkl"))
    print(f"\n  Models saved to: {_model_dir}")


def training_pipeline(df, feature_multipliers=None, dirs=None):
    """Run training pipeline with optional feature weights and session isolation."""
    d = dirs or {}
    _model_dir  = d.get("model_dir",  MODEL_DIR)
    _report_dir = d.get("report_dir", REPORT_DIR)

    print("=" * 60)
    print("ML TRAINING PIPELINE (V3)")
    print("=" * 60)
    X, y, label_encoders = prepare_data(df, feature_multipliers)

    if len(X) < 50:
        raise ValueError(f"Dataset too small ({len(X)} rows). Need at least 50 customers to train a model.")
    if y.nunique() < 2:
        raise ValueError(
            "All customers in your data have the same churn label — the model needs both churned "
            "and retained customers to learn from. Check your 'churned' column or use Predict Only mode."
        )

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
    print(f"\n  Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)
    os.makedirs(_model_dir, exist_ok=True)
    joblib.dump(scaler, os.path.join(_model_dir, "scaler.pkl"))
    results, trained_models = train_models(X_train_scaled, y_train, X_test_scaled, y_test)
    best_name, _ = get_best_model(results, trained_models)
    metrics_df = plot_model_comparison(results, X_test_scaled, y_test, trained_models, dirs=dirs)
    save_models(trained_models, best_name, label_encoders, X.columns, feature_multipliers, dirs=dirs)
    metrics_df.to_csv(os.path.join(_report_dir, "model_results.csv"))
    print("\nTRAINING COMPLETE")
    return results, trained_models, best_name, scaler, list(X_test.index)
