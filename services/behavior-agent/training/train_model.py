"""Train Isolation Forest model on synthetic or real behavioral data."""

import json
import os
import pickle
import time
from datetime import datetime

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        precision_recall_fscore_support,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
except ImportError:
    print("scikit-learn not installed. Run: pip install scikit-learn")
    exit(1)


FEATURE_COLUMNS = [
    "hour_of_day", "day_of_week", "session_duration_s",
    "req_per_min", "req_burst_ratio", "endpoint_diversity",
    "geo_distance_km", "country_change", "asn_change",
    "fp_change_count", "ua_anomaly_score", "is_headless",
    "path_entropy", "api_ratio", "sensitive_endpoint_freq",
    "token_age_s", "token_reuse_count", "clock_skew_ms",
    "ja3_stability", "tls_version_change", "ip_reputation_score",
]


def train_model(
    data_path: str = "./training_data.json",
    output_path: str = "../models/isolation_forest.pkl",
    n_estimators: int = 200,
    contamination: float = 0.05,
    test_size: float = 0.2,
) -> dict:
    """
    Train Isolation Forest and save model checkpoint.
    
    Returns evaluation metrics.
    """
    print("=" * 60)
    print("CIVA Behavior Agent — Model Training Pipeline")
    print("=" * 60)

    # ---- Load Data ----
    print(f"\n📂 Loading data from {data_path}...")
    with open(data_path) as f:
        raw_data = json.load(f)

    print(f"   Total samples: {len(raw_data)}")

    # ---- Extract Feature Matrix ----
    X = []
    y = []
    for sample in raw_data:
        features = [sample.get(col, 0.0) for col in FEATURE_COLUMNS]
        X.append(features)
        y.append(sample.get("label", 0))

    X = np.array(X)
    y = np.array(y)

    n_normal = (y == 0).sum()
    n_attack = (y == 1).sum()
    print(f"   Normal:  {n_normal} ({n_normal/len(y)*100:.1f}%)")
    print(f"   Attack:  {n_attack} ({n_attack/len(y)*100:.1f}%)")
    print(f"   Features: {X.shape[1]}")

    # ---- Train/Test Split ----
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"\n📊 Train: {len(X_train)}, Test: {len(X_test)}")

    # ---- Train Model ----
    print(f"\n🧠 Training Isolation Forest (n_estimators={n_estimators})...")
    start_time = time.time()

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        max_features=0.8,
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )

    # Train on ALL data (Isolation Forest is unsupervised)
    model.fit(X_train)

    training_time = time.time() - start_time
    print(f"   Training time: {training_time:.2f}s")

    # ---- Evaluate ----
    print("\n📈 Evaluating model...")

    # Get raw scores
    train_scores = model.score_samples(X_train)
    test_scores = model.score_samples(X_test)

    # Predict anomalies (-1 = anomaly, 1 = normal)
    y_pred = model.predict(X_test)
    y_pred_binary = (y_pred == -1).astype(int)  # Convert to 0/1

    # Metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred_binary, average="binary"
    )

    try:
        auc = roc_auc_score(y_test, -test_scores)  # Negate: more negative = more anomalous
    except ValueError:
        auc = 0.0

    print(f"\n   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   AUC-ROC:   {auc:.4f}")

    print(f"\n   Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred_binary)
    print(f"   TN={cm[0][0]:5d}  FP={cm[0][1]:5d}")
    print(f"   FN={cm[1][0]:5d}  TP={cm[1][1]:5d}")

    print(f"\n   Classification Report:")
    print(classification_report(y_test, y_pred_binary, target_names=["Normal", "Attack"]))

    # ---- Inference Latency Test ----
    print("⏱  Inference latency test (1000 samples)...")
    latencies = []
    for i in range(1000):
        sample = X_test[i % len(X_test)].reshape(1, -1)
        start = time.perf_counter()
        model.score_samples(sample)
        latencies.append((time.perf_counter() - start) * 1000)

    latencies = np.array(latencies)
    print(f"   p50: {np.percentile(latencies, 50):.3f} ms")
    print(f"   p95: {np.percentile(latencies, 95):.3f} ms")
    print(f"   p99: {np.percentile(latencies, 99):.3f} ms")
    print(f"   max: {np.max(latencies):.3f} ms")

    # ---- Save Model ----
    print(f"\n💾 Saving model to {output_path}...")
    checkpoint = {
        "model": model,
        "version": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "feature_means": X_train.mean(axis=0),
        "feature_stds": X_train.std(axis=0),
        "feature_columns": FEATURE_COLUMNS,
        "confidence": f1,
        "metrics": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "auc_roc": auc,
            "training_time_s": training_time,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "latency_p50_ms": float(np.percentile(latencies, 50)),
            "latency_p99_ms": float(np.percentile(latencies, 99)),
        },
        "trained_at": datetime.now().isoformat(),
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(checkpoint, f)

    print(f"\n✅ Model saved successfully!")
    print("=" * 60)

    return checkpoint["metrics"]


if __name__ == "__main__":
    train_model()
