"""
Prediction Engine — V3
Provides churn predictions and risk analysis for individual customers or segments.
"""
import pandas as pd
import numpy as np
import joblib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


class ChurnPredictor:
    def __init__(self, dirs=None):
        d = dirs or {}
        self._model_dir       = d.get("model_dir",          MODEL_DIR)
        self._merged_data_file = d.get("merged_data_file",  MERGED_DATA_FILE)
        self._features_file    = d.get("final_features_file", FINAL_FEATURES_FILE)
        self.model = None
        self.scaler = None
        self.metadata = None
        self.merged_data = None
        self.feature_data = None
        self._test_indices = None  # set after demo retrain to prevent leakage
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            self.model = joblib.load(os.path.join(self._model_dir, "best_model.pkl"))
            self.scaler = joblib.load(os.path.join(self._model_dir, "scaler.pkl"))
            self.metadata = joblib.load(os.path.join(self._model_dir, "model_metadata.pkl"))
            self.merged_data = pd.read_csv(self._merged_data_file)
            self.feature_data = pd.read_csv(self._features_file)
            print(f"Loaded model: {self.metadata['best_model_name']}")
        except Exception as e:
            print(f"Warning: Could not load artifacts: {e}")

    def _prepare_features(self, df_row):
        trained = self.metadata.get("feature_names", [])
        X = df_row.copy()
        le_dict = self.metadata.get("label_encoders", {})
        for col in X.columns:
            if X[col].dtype == object:
                if col in le_dict:
                    le = le_dict[col]
                    cs = set(le.classes_)
                    X[col] = X[col].astype(str).apply(lambda v: le.transform([v])[0] if v in cs else 0)
                else:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
        multipliers = self.metadata.get("feature_multipliers", {})
        for col, m in multipliers.items():
            if col in X.columns:
                X[col] = X[col] * m
        X = X.fillna(0).apply(pd.to_numeric, errors="coerce").fillna(0)
        # Pad any features the model expects but this data doesn't have
        for col in trained:
            if col not in X.columns:
                X[col] = 0
        return X[[c for c in trained if c in X.columns]]

    def _prepare_bulk_features(self):
        trained = self.metadata.get("feature_names", [])
        X = self.feature_data.copy()
        le_dict = self.metadata.get("label_encoders", {})
        for col in X.columns:
            if X[col].dtype == object:
                if col in le_dict:
                    le = le_dict[col]
                    cs = set(le.classes_)
                    X[col] = X[col].astype(str).apply(lambda v: le.transform([v])[0] if v in cs else 0)
                else:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
        multipliers = self.metadata.get("feature_multipliers", {})
        for col, m in multipliers.items():
            if col in X.columns:
                X[col] = X[col] * m
        X = X.fillna(0).apply(pd.to_numeric, errors="coerce").fillna(0)
        # Pad any features the model expects but this data doesn't have
        for col in trained:
            if col not in X.columns:
                X[col] = 0
        return X[[c for c in trained if c in X.columns]]

    def predict_customer(self, customer_id):
        if self.merged_data is None:
            return {"error": "Data not loaded"}
        customer = self.merged_data[self.merged_data["customer_id"] == customer_id]
        if customer.empty:
            return {"error": f"Customer {customer_id} not found"}
        features = self.feature_data[self.feature_data["customer_id"] == customer_id]
        if features.empty:
            return {"error": f"Feature data not available for {customer_id}. Try re-uploading your data."}
        X = self._prepare_features(features)
        X_scaled = self.scaler.transform(X)
        prob = self.model.predict_proba(X_scaled)[0]
        prediction = self.model.predict(X_scaled)[0]
        churn_prob = prob[1]
        risk_level = "HIGH" if churn_prob >= 0.7 else ("MEDIUM" if churn_prob >= 0.4 else "LOW")
        info = customer.iloc[0].to_dict()
        return {
            "customer_id": customer_id,
            "churn_probability": round(float(churn_prob), 4),
            "prediction": "Will Churn" if prediction == 1 else "Will Stay",
            "risk_level": risk_level,
            "customer_info": {
                "name": info.get("customer_name", "N/A"),
                "region": info.get("region", "N/A"),
                "tenure_months": info.get("account_tenure_months", 0),
                "service_type": info.get("service_type", "N/A"),
                "contract_type": info.get("contract_type", "N/A"),
                "complaint_count": int(info.get("complaint_count", 0)),
                "avg_sentiment_score": round(info.get("avg_sentiment_score", 0), 3),
                "satisfaction_score": round(info.get("avg_satisfaction_score", 0), 2),
                "negative_sentiment_ratio": round(info.get("negative_sentiment_ratio", 0), 3),
                "composite_risk_score": int(info.get("composite_risk_score", 0)),
            },
        }

    def get_top_risk_customers(self, n=20):
        if self.feature_data is None:
            return []
        X = self._prepare_bulk_features()

        # In demo retrain mode, restrict to test-set rows only to prevent leakage
        if self._test_indices is not None:
            valid = [i for i in self._test_indices if i in X.index]
            X = X.loc[valid]
            merged_subset = self.merged_data.loc[self.merged_data.index.isin(valid)].copy()
        else:
            merged_subset = self.merged_data.copy()

        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)[:, 1]
        cols_to_show = ["customer_id", "customer_name", "region", "account_tenure_months", "service_type"]
        cols_available = [c for c in cols_to_show if c in merged_subset.columns]
        risk_df = merged_subset[cols_available].copy()
        risk_df["churn_probability"] = probs
        risk_df["risk_level"] = pd.cut(probs, bins=[0, 0.4, 0.7, 1.0], labels=["LOW", "MEDIUM", "HIGH"])
        return risk_df.nlargest(n, "churn_probability").to_dict("records")

    def get_segment_analysis(self):
        if self.merged_data is None:
            return {}
        X = self._prepare_bulk_features()
        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)[:, 1]
        adf = self.merged_data.copy()
        adf["churn_probability"] = probs
        segments = {}
        for col in ["region", "contract_type", "service_type"]:
            if col in adf.columns:
                segments[f"by_{col}"] = adf.groupby(col).agg(
                    avg_churn_prob=("churn_probability", "mean"),
                    customer_count=("customer_id", "count"),
                ).round(4).to_dict("index")
        segments["overall"] = {
            "total_customers": len(adf),
            "avg_churn_prob": round(probs.mean(), 4),
            "high_risk_count": int((probs > 0.7).sum()),
            "medium_risk_count": int(((probs > 0.4) & (probs <= 0.7)).sum()),
            "low_risk_count": int((probs <= 0.4).sum()),
        }
        return segments

    def get_retention_recommendations(self, customer_id):
        pred = self.predict_customer(customer_id)
        if "error" in pred:
            return pred
        recs = []
        info = pred["customer_info"]
        if info["complaint_count"] > 3:
            recs.append({"priority": "HIGH", "action": "Proactive Complaint Resolution", "detail": f"Customer has {info['complaint_count']} complaints. Assign dedicated service rep."})
        if info["satisfaction_score"] < 2.5:
            recs.append({"priority": "HIGH", "action": "Customer Recovery Program", "detail": f"Satisfaction score is {info['satisfaction_score']}/5. Initiate recovery outreach."})
        if info["negative_sentiment_ratio"] > 0.5:
            recs.append({"priority": "HIGH", "action": "Sentiment Intervention", "detail": "High negative sentiment detected in comments. Schedule personal call from account manager."})
        if info["tenure_months"] < 12:
            recs.append({"priority": "MEDIUM", "action": "New Customer Nurture", "detail": "Customer under 12 months. Enroll in welcome program."})
        if pred["churn_probability"] > 0.6:
            recs.append({"priority": "HIGH", "action": "Loyalty Offer", "detail": "High churn risk. Consider rate discount or service upgrade."})
        if not recs:
            recs.append({"priority": "LOW", "action": "Routine Engagement", "detail": "Customer appears stable. Maintain regular monitoring."})
        pred["recommendations"] = recs
        return pred

    def get_data_summary(self):
        if self.merged_data is None:
            return "No data loaded."
        df = self.merged_data
        return {
            "total_customers": len(df),
            "churn_rate": f"{df['churned'].mean():.2%}" if "churned" in df.columns else "N/A",
            "regions": df["region"].unique().tolist() if "region" in df.columns else [],
            "service_types": df["service_type"].unique().tolist() if "service_type" in df.columns else [],
            "avg_tenure_months": round(df["account_tenure_months"].mean(), 1) if "account_tenure_months" in df.columns else 0,
            "avg_satisfaction": round(df["avg_satisfaction_score"].mean(), 2) if "avg_satisfaction_score" in df.columns else 0,
        }
