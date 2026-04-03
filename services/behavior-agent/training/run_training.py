"""Quick training runner that saves model to the correct path."""

import json
import os
import pickle
import time
import numpy as np
from datetime import datetime

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

FEATURE_COLUMNS = [
    "hour_of_day", "day_of_week", "session_duration_s",
    "req_per_min", "req_burst_ratio", "endpoint_diversity",
    "geo_distance_km", "country_change", "asn_change",
    "fp_change_count", "ua_anomaly_score", "is_headless",
    "path_entropy", "api_ratio", "sensitive_endpoint_freq",
    "token_age_s", "token_reuse_count", "clock_skew_ms",
    "ja3_stability", "tls_version_change", "ip_reputation_score",
]

# Resolve paths relative to behavior-agent root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(SERVICE_DIR, "training_data.json")
OUTPUT_PATH = os.path.join(SERVICE_DIR, "models", "isolation_forest.pkl")


def main():
    print("=" * 60)
    print("CIVA Behavior Agent — Model Training Pipeline")
    print("=" * 60)

    # Load Data
    print(f"\nLoading data from {DATA_PATH}...")
    with open(DATA_PATH) as f:
        raw_data = json.load(f)
    print(f"  Total samples: {len(raw_data)}")

    # Extract Feature Matrix
    X = np.array([[s.get(c, 0.0) for c in FEATURE_COLUMNS] for s in raw_data])
    y = np.array([s.get("label", 0) for s in raw_data])
    print(f"  Normal:  {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")
    print(f"  Attack:  {(y == 1).sum()} ({(y == 1).sum() / len(y) * 100:.1f}%)")
    print(f"  Features: {X.shape[1]}")

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train: {len(X_train)}, Test: {len(X_test)}")

    # Train Model
    print(f"\n  Training Isolation Forest (n_estimators=200)...")
    t0 = time.time()
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        max_features=0.8,
        bootstrap=True,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train)
    train_time = time.time() - t0
    print(f"  Training time: {train_time:.2f}s")

    # Evaluate
    print("\n  Evaluating model...")
    test_scores = model.score_samples(X_test)
    y_pred = (model.predict(X_test) == -1).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary"
    )
    auc = roc_auc_score(y_test, -test_scores)
    cm = confusion_matrix(y_test, y_pred)

    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  AUC-ROC:   {auc:.4f}")
    print(f"\n  Confusion Matrix:")
    print(f"  TN={cm[0][0]:5d}  FP={cm[0][1]:5d}")
    print(f"  FN={cm[1][0]:5d}  TP={cm[1][1]:5d}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Normal', 'Attack'])}")

    # Latency Test
    print("  Inference latency test (1000 samples)...")
    latencies = []
    for i in range(1000):
        s = X_test[i % len(X_test)].reshape(1, -1)
        t = time.perf_counter()
        model.score_samples(s)
        latencies.append((time.perf_counter() - t) * 1000)
    latencies = np.array(latencies)
    print(f"  p50: {np.percentile(latencies, 50):.3f}ms")
    print(f"  p95: {np.percentile(latencies, 95):.3f}ms")
    print(f"  p99: {np.percentile(latencies, 99):.3f}ms")
    print(f"  max: {np.max(latencies):.3f}ms")

    # Save Model
    print(f"\n  Saving model to {OUTPUT_PATH}...")
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
            "training_time_s": train_time,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "latency_p50_ms": float(np.percentile(latencies, 50)),
            "latency_p99_ms": float(np.percentile(latencies, 99)),
        },
        "trained_at": datetime.now().isoformat(),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(checkpoint, f)

    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"  Model saved ({size_mb:.1f} MB)")
    print("\n" + "=" * 60)
    print("  Model training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
