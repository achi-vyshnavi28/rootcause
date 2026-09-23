"""Surface-defect detection on KolektorSDD (real factory images of electrical commutators).

Classical pipeline (runs on a laptop CPU, no deep learning):
  1. anomaly map: black-hat morphology highlights thin DARK structures (cracks) that are smaller
     than the structuring element, after removing slow lighting changes
  2. features: how strong and how large the strongest anomalies are (quantiles, blob area, elongation)
  3. classifier: gradient boosting says "defective or not" for the whole image

Evaluation is split BY PART (each part was photographed 8 times), so the model is never tested on
a part it has already seen. 5 different part-level splits, mean +/- std reported.

    python -m vision.kolektor      (needs data/raw/kolektor; see README)
"""

from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from ml import tracking

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "kolektor"
SCALE = 0.5


def load_pairs() -> list[tuple[Path, Path, str]]:
    pairs = []
    for img in sorted(DATA.glob("kos*/Part*.jpg")):
        mask = img.with_name(img.stem + "_label.bmp")
        if mask.exists():
            pairs.append((img, mask, img.parent.name))
    return pairs


def read_gray(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    return cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)


def anomaly_map(gray: np.ndarray) -> np.ndarray:
    """0..1 map where high values mark thin dark marks (candidate cracks)."""
    g = cv2.GaussianBlur(gray, (3, 3), 0).astype(np.float32)
    flat = g - cv2.GaussianBlur(g, (0, 0), 25) + 128  # remove slow illumination changes
    flat = np.clip(flat, 0, 255).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    blackhat = cv2.morphologyEx(flat, cv2.MORPH_BLACKHAT, kernel).astype(np.float32)
    return blackhat / 255.0


def features(amap: np.ndarray) -> dict:
    q = np.quantile(amap, [0.99, 0.999, 0.9999])
    binary = (amap > max(q[2], 0.08)).astype(np.uint8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA] if n > 1 else np.array([0])
    biggest = int(np.argmax(areas)) + 1 if n > 1 else None
    elongation = 0.0
    if biggest is not None:
        w, h = stats[biggest, cv2.CC_STAT_WIDTH], stats[biggest, cv2.CC_STAT_HEIGHT]
        elongation = max(w, h) / max(1, min(w, h))
    return {"q99": q[0], "q999": q[1], "q9999": q[2], "max": float(amap.max()), "mean": float(amap.mean()),
            "n_blobs": int(n - 1), "largest_blob": int(areas.max()), "elongation": float(elongation),
            "strong_pixels": int((amap > 0.15).sum())}


def build_table() -> pd.DataFrame:
    rows = []
    for img, mask, part in load_pairs():
        amap = anomaly_map(read_gray(img))
        m = cv2.resize(cv2.imread(str(mask), cv2.IMREAD_GRAYSCALE), amap.shape[::-1], interpolation=cv2.INTER_NEAREST)
        defect = m > 0
        # pixel-level check: is the anomaly map higher on true defect pixels?
        rows.append({"image": f"{part}/{img.name}", "part": part, "defective": int(defect.any()),
                     "map_inside_defect": float(amap[defect].mean()) if defect.any() else np.nan,
                     "map_outside_defect": float(amap[~defect].mean()), **features(amap)})
    return pd.DataFrame(rows)


FEATURES = ["q99", "q999", "q9999", "max", "mean", "n_blobs", "largest_blob", "elongation", "strong_pixels"]


def evaluate(df: pd.DataFrame, splits: int = 5) -> dict:
    scores = {"roc_auc": [], "average_precision": [], "recall_at_5pct_false_reject": []}
    for seed in range(splits):
        tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed).split(df, groups=df["part"]))
        train, test = df.iloc[tr], df.iloc[te]
        if test["defective"].nunique() < 2:
            continue
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, class_weight="balanced", random_state=seed)
        clf.fit(train[FEATURES], train["defective"])
        p = clf.predict_proba(test[FEATURES])[:, 1]
        scores["roc_auc"].append(roc_auc_score(test["defective"], p))
        scores["average_precision"].append(average_precision_score(test["defective"], p))
        # operating point: reject at most 5% of GOOD parts; how many defective parts do we catch?
        threshold = np.quantile(p[test["defective"].to_numpy() == 0], 0.95)
        scores["recall_at_5pct_false_reject"].append(float((p[test["defective"].to_numpy() == 1] > threshold).mean()))
    return {k: {"mean": round(float(np.mean(v)), 3), "std": round(float(np.std(v)), 3), "runs": len(v)} for k, v in scores.items()}


def main() -> None:
    df = build_table()
    defective = df[df["defective"] == 1]
    report = {
        "dataset": "KolektorSDD", "images": len(df), "defective": int(df["defective"].sum()), "parts": int(df["part"].nunique()),
        "pixel_check": {"mean_map_on_defect_pixels": round(float(defective["map_inside_defect"].mean()), 4),
                        "mean_map_elsewhere": round(float(df["map_outside_defect"].mean()), 4)},
        "image_level": evaluate(df),
        "method": "classical: illumination flattening + black-hat morphology + blob features + gradient boosting",
    }
    with tracking.start("kolektor_classical"):
        import mlflow

        for k, v in report["image_level"].items():
            mlflow.log_metric(k, v["mean"])
    print(tracking.save_report("vision_kolektor_classical", report))
    print(report["pixel_check"])
    for k, v in report["image_level"].items():
        print(f"{k:<30} {v['mean']:.3f} +/- {v['std']:.3f}")


if __name__ == "__main__":
    main()
