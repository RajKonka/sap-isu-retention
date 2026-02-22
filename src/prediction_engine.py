"""
Prediction Engine Module
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
    """Churn prediction and risk analysis engine."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.metadata = None
        self.merged_data = None
        self.feature_data = None
        self._load_artifacts()

    def _load_artifacts(self):
        """Load trained model, scaler, and metadata."""
        try:
            self.model = joblib.load(os.path.join(MODEL_DIR, "best_model.pkl"))
            self.scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
            self.metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.pkl"))
            self.merged_data = pd.read_csv(MERGED_DATA_FILE)
            self.feature_data = pd.read_csv(FINAL_FEATURES_FILE)
            print(f"Loaded model: {self.metadata['best_model_name']}")
            print(f"Loaded {len(self.merged_data)} customer records")
        except Exception as e:
            print(f"Warning: Could not load all artifacts: {e}")

    def _prepare_features(self, df_row):
        """Prepare features for prediction, encoding categoricals."""
        trained_feature_names = self.metadata.get("feature_names", [])
        feature_cols = [c for c in trained_feature_names if c in df_row.columns and c != TARGET_COLUMN]
        X = df_row[feature_cols].copy()

        # Encode any string columns using the saved label encoders
        label_encoders = self.metadata.get("label_encoders", {})
        for col in X.columns:
            if X[col].dtype == object or str(X[col].dtype) == "string":
                if col in label_encoders:
                    le = label_encoders[col]
                    classes_set = set(le.classes_)
                    X[col] = X[col].astype(str).apply(
                        lambda v: le.transform([v])[0] if v in classes_set else 0
                    )
                else:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

        return X.fillna(0).apply(pd.to_numeric, errors="coerce").fillna(0)

    def _prepare_bulk_features(self):
        """Prepare all features for bulk prediction."""
        trained_feature_names = self.metadata.get("feature_names", [])
        feature_cols = [c for c in trained_feature_names if c in self.feature_data.columns and c != TARGET_COLUMN]
        X = self.feature_data[feature_cols].copy()

        label_encoders = self.metadata.get("label_encoders", {})
        for col in X.columns:
            if X[col].dtype == object or str(X[col].dtype) == "string":
                if col in label_encoders:
                    le = label_encoders[col]
                    classes_set = set(le.classes_)
                    X[col] = X[col].astype(str).apply(
                        lambda v: le.transform([v])[0] if v in classes_set else 0
                    )
                else:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

        return X.fillna(0).apply(pd.to_numeric, errors="coerce").fillna(0)

    def predict_customer(self, customer_id):
        """Get churn prediction for a specific customer."""
        if self.merged_data is None:
            return {"error": "Data not loaded"}

        customer = self.merged_data[self.merged_data["customer_id"] == customer_id]
        if customer.empty:
            return {"error": f"Customer {customer_id} not found"}

        # Get features
        features = self.feature_data[self.feature_data["customer_id"] == customer_id]
        X = self._prepare_features(features)

        # Scale and predict
        X_scaled = self.scaler.transform(X)
        prob = self.model.predict_proba(X_scaled)[0]
        prediction = self.model.predict(X_scaled)[0]

        # Risk level
        churn_prob = prob[1]
        if churn_prob >= 0.7:
            risk_level = "HIGH"
        elif churn_prob >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Customer details
        cust_info = customer.iloc[0].to_dict()

        return {
            "customer_id": customer_id,
            "churn_probability": round(float(churn_prob), 4),
            "prediction": "Will Churn" if prediction == 1 else "Will Stay",
            "risk_level": risk_level,
            "customer_info": {
                "name": cust_info.get("customer_name", "N/A"),
                "region": cust_info.get("region", "N/A"),
                "tenure_months": cust_info.get("account_tenure_months", 0),
                "service_type": cust_info.get("service_type", "N/A"),
                "contract_type": cust_info.get("contract_type", "N/A"),
                "avg_monthly_bill": round(cust_info.get("avg_monthly_bill", 0), 2),
                "complaint_count": int(cust_info.get("complaint_count", 0)),
                "satisfaction_score": round(cust_info.get("avg_satisfaction_score", 0), 2),
                "negative_sentiment_ratio": round(cust_info.get("negative_sentiment_ratio", 0), 3),
            },
        }

    def get_top_risk_customers(self, n=20):
        """Get top N customers at risk of churning."""
        if self.feature_data is None:
            return []

        X = self._prepare_bulk_features()
        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)[:, 1]

        risk_df = self.merged_data[["customer_id", "customer_name", "region",
                                     "account_tenure_months", "service_type"]].copy()
        risk_df["churn_probability"] = probs
        risk_df["risk_level"] = pd.cut(probs, bins=[0, 0.4, 0.7, 1.0],
                                        labels=["LOW", "MEDIUM", "HIGH"])

        return risk_df.nlargest(n, "churn_probability").to_dict("records")

    def get_segment_analysis(self):
        """Analyze churn risk by customer segments."""
        if self.merged_data is None:
            return {}

        X = self._prepare_bulk_features()
        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)[:, 1]

        analysis_df = self.merged_data.copy()
        analysis_df["churn_probability"] = probs

        segments = {}

        # By Region
        segments["by_region"] = analysis_df.groupby("region").agg(
            avg_churn_prob=("churn_probability", "mean"),
            customer_count=("customer_id", "count"),
            high_risk_count=("churn_probability", lambda x: (x > 0.7).sum()),
        ).round(4).to_dict("index")

        # By Contract Type
        segments["by_contract_type"] = analysis_df.groupby("contract_type").agg(
            avg_churn_prob=("churn_probability", "mean"),
            customer_count=("customer_id", "count"),
        ).round(4).to_dict("index")

        # By Service Type
        segments["by_service_type"] = analysis_df.groupby("service_type").agg(
            avg_churn_prob=("churn_probability", "mean"),
            customer_count=("customer_id", "count"),
        ).round(4).to_dict("index")

        # Overall stats
        segments["overall"] = {
            "total_customers": len(analysis_df),
            "avg_churn_prob": round(probs.mean(), 4),
            "high_risk_count": int((probs > 0.7).sum()),
            "medium_risk_count": int(((probs > 0.4) & (probs <= 0.7)).sum()),
            "low_risk_count": int((probs <= 0.4).sum()),
        }

        return segments

    def get_retention_recommendations(self, customer_id):
        """Generate retention recommendations for a customer."""
        prediction = self.predict_customer(customer_id)
        if "error" in prediction:
            return prediction

        recommendations = []
        info = prediction["customer_info"]

        if info["complaint_count"] > 3:
            recommendations.append({
                "priority": "HIGH",
                "action": "Proactive Complaint Resolution",
                "detail": f"Customer has {info['complaint_count']} complaints. Assign dedicated service rep for immediate follow-up."
            })

        if info["satisfaction_score"] < 2.5:
            recommendations.append({
                "priority": "HIGH",
                "action": "Customer Recovery Program",
                "detail": f"Satisfaction score is {info['satisfaction_score']}/5. Initiate satisfaction recovery outreach."
            })

        if info["negative_sentiment_ratio"] > 0.5:
            recommendations.append({
                "priority": "HIGH",
                "action": "Sentiment Intervention",
                "detail": "High negative sentiment detected. Schedule personal call from account manager."
            })

        if info["tenure_months"] < 12:
            recommendations.append({
                "priority": "MEDIUM",
                "action": "New Customer Nurture",
                "detail": "Customer is relatively new. Enroll in welcome program and ensure smooth onboarding."
            })

        if prediction["churn_probability"] > 0.6:
            recommendations.append({
                "priority": "HIGH",
                "action": "Loyalty Offer",
                "detail": "High churn risk. Consider offering rate discount, reward points, or service upgrade."
            })

        if not recommendations:
            recommendations.append({
                "priority": "LOW",
                "action": "Routine Engagement",
                "detail": "Customer appears stable. Maintain regular communication and satisfaction monitoring."
            })

        prediction["recommendations"] = recommendations
        return prediction

    def get_data_summary(self):
        """Get a summary of the loaded data for the chatbot context."""
        if self.merged_data is None:
            return "No data loaded."

        df = self.merged_data
        summary = {
            "total_customers": len(df),
            "churn_rate": f"{df['churned'].mean():.2%}" if 'churned' in df.columns else "N/A",
            "regions": df["region"].unique().tolist() if "region" in df.columns else [],
            "service_types": df["service_type"].unique().tolist() if "service_type" in df.columns else [],
            "avg_tenure_months": round(df["account_tenure_months"].mean(), 1) if "account_tenure_months" in df.columns else 0,
            "avg_monthly_bill": round(df["avg_monthly_bill"].mean(), 2) if "avg_monthly_bill" in df.columns else 0,
            "avg_satisfaction": round(df["avg_satisfaction_score"].mean(), 2) if "avg_satisfaction_score" in df.columns else 0,
        }
        return summary
