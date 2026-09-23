"""Surface-defect detection on real factory images (KolektorSDD: 399 commutator photos, 52 with cracks).

Two detectors, both CPU-only:

1. classical  - OpenCV: contrast normalisation (CLAHE) + black-hat morphology with a VERTICAL kernel, which
                lights up thin HORIZONTAL dark lines (cracks), then averaging along the horizontal so random
                surface grain cancels out. Bright artefacts at the left/right edges are masked out.
                Parameters were tuned on training products only (see docs/decision_log.md).
2. patch_bank - the PatchCore idea (Roth et al., 2022), implemented from scratch with handcrafted
                features instead of a pretrained CNN: describe every patch of GOOD images (HOG + intensity
                statistics), shrink that memory bank with greedy k-center coreset selection, then score a
                new patch by its distance to the nearest normal patch. Trained on defect-free images only.

Evaluation splits by product folder (parts of one commutator never appear in both train and test).
Metrics: image-level ROC-AUC / average precision, and localisation "pointing" accuracy: is the
most anomalous spot inside the true (slightly dilated) defect mask?

    python -m vision.defects
"""

from pathlib import Path

import cv2
import numpy as np
from skimage.feature import hog
from sklearn.decomposition import PCA
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.neighbors import NearestNeighbors

from ml import tracking

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "ksdd"
SIZE = (256, 640)  # (width, height) after resizing; images are tall and thin
PATCH, STRIDE = 32, 16
EDGE_MARGIN = 0.08  # fraction of width ignored on each side (bright edge strips are normal, not defects)
CRACK_KERNEL_H = 11  # vertical structuring element: fills dark lines thinner than this
CRACK_BLUR_W = 41  # horizontal averaging length: cracks are long and horizontal, grain is random


# ---------------- data ----------------
def load_dataset() -> list[dict]:
    items = []
    for img_path in sorted(DATA.glob("kos*/Part*.jpg")):
        img = cv2.resize(cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE), SIZE, interpolation=cv2.INTER_AREA)
        mask = cv2.resize(cv2.imread(str(img_path).replace(".jpg", "_label.bmp"), cv2.IMREAD_GRAYSCALE), SIZE,
                          interpolation=cv2.INTER_NEAREST) > 0
        items.append({"product": img_path.parent.name, "name": img_path.stem, "image": img, "mask": mask,
                      "defective": bool(mask.any())})
    return items


def split_by_product(items: list[dict], test_every: int = 3) -> tuple[list[dict], list[dict]]:
    products = sorted({i["product"] for i in items})
    test_products = set(products[::test_every])
    return [i for i in items if i["product"] not in test_products], [i for i in items if i["product"] in test_products]


# ---------------- detector 1: classical ----------------
def mask_edges(amap: np.ndarray) -> np.ndarray:
    m = int(amap.shape[1] * EDGE_MARGIN)
    out = np.zeros_like(amap)
    out[:, m:amap.shape[1] - m] = amap[:, m:amap.shape[1] - m]
    return out


def classical_map(img: np.ndarray) -> np.ndarray:
    norm = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, CRACK_KERNEL_H))
    blackhat = cv2.morphologyEx(norm, cv2.MORPH_BLACKHAT, kernel).astype(np.float32)
    return mask_edges(cv2.blur(blackhat, (CRACK_BLUR_W, 3)))


# ---------------- detector 2: patch memory bank ----------------
def patch_grid(img: np.ndarray) -> tuple[np.ndarray, list[tuple[int, int]]]:
    feats, centers = [], []
    h, w = img.shape
    for y in range(0, h - PATCH + 1, STRIDE):
        for x in range(0, w - PATCH + 1, STRIDE):
            p = img[y:y + PATCH, x:x + PATCH]
            h_feat = hog(p, orientations=9, pixels_per_cell=(8, 8), cells_per_block=(2, 2), feature_vector=True)
            feats.append(np.concatenate([h_feat, [p.mean() / 255, p.std() / 255, np.percentile(p, 5) / 255]]))
            centers.append((y + PATCH // 2, x + PATCH // 2))
    return np.asarray(feats, dtype=np.float32), centers


def greedy_coreset(features: np.ndarray, size: int, seed: int = 0) -> np.ndarray:
    """k-center greedy: repeatedly add the point farthest from everything chosen so far (keeps rare normal patterns)."""
    rng = np.random.default_rng(seed)
    chosen = [int(rng.integers(len(features)))]
    min_dist = np.linalg.norm(features - features[chosen[0]], axis=1)
    for _ in range(size - 1):
        nxt = int(np.argmax(min_dist))
        chosen.append(nxt)
        min_dist = np.minimum(min_dist, np.linalg.norm(features - features[nxt], axis=1))
    return features[chosen]


class PatchBank:
    def __init__(self, coreset_size: int = 4000, pca_dims: int = 48):
        self.coreset_size, self.pca_dims = coreset_size, pca_dims

    def fit(self, good_images: list[np.ndarray]) -> "PatchBank":
        feats = np.vstack([patch_grid(cv2.createCLAHE(2.0, (8, 8)).apply(i))[0] for i in good_images])
        self.pca = PCA(self.pca_dims, random_state=0).fit(feats)
        reduced = self.pca.transform(feats)
        bank = greedy_coreset(reduced, min(self.coreset_size, len(reduced)))
        self.nn = NearestNeighbors(n_neighbors=1).fit(bank)
        return self

    def anomaly_map(self, img: np.ndarray) -> np.ndarray:
        feats, centers = patch_grid(cv2.createCLAHE(2.0, (8, 8)).apply(img))
        dist = self.nn.kneighbors(self.pca.transform(feats))[0][:, 0]
        amap = np.zeros(img.shape, dtype=np.float32)
        for d, (cy, cx) in zip(dist, centers):
            amap[cy - STRIDE // 2: cy + STRIDE // 2, cx - STRIDE // 2: cx + STRIDE // 2] = d
        return mask_edges(cv2.GaussianBlur(amap, (31, 31), 0))


# ---------------- evaluation ----------------
def pointing_hit(amap: np.ndarray, mask: np.ndarray, tolerance_px: int = 16) -> bool:
    y, x = np.unravel_index(int(np.argmax(amap)), amap.shape)
    grown = cv2.dilate(mask.astype(np.uint8), np.ones((2 * tolerance_px + 1,) * 2, np.uint8)) > 0
    return bool(grown[y, x])


def score(test: list[dict], maps: list[np.ndarray]) -> dict:
    y = np.array([t["defective"] for t in test])
    s = np.array([m.max() for m in maps])
    hits = [pointing_hit(m, t["mask"]) for m, t in zip(maps, test) if t["defective"]]
    return {"image_roc_auc": round(float(roc_auc_score(y, s)), 4), "image_avg_precision": round(float(average_precision_score(y, s)), 4),
            "localisation_pointing_acc": round(float(np.mean(hits)), 4) if hits else None}


def main() -> None:
    items = load_dataset()
    train, test = split_by_product(items)
    good_train = [i["image"] for i in train if not i["defective"]]
    results = {"classical": score(test, [classical_map(t["image"]) for t in test])}
    bank = PatchBank().fit(good_train)
    results["patch_bank"] = score(test, [bank.anomaly_map(t["image"]) for t in test])
    report = {"dataset": "KolektorSDD", "train_good_images": len(good_train), "test_images": len(test),
              "test_defective": int(sum(t["defective"] for t in test)), "split": "by product folder (every 3rd folder is test)",
              "results": results}
    with tracking.start("surface_defects"):
        import mlflow

        for model, m in results.items():
            for k, v in m.items():
                if v is not None:
                    mlflow.log_metric(f"{model}_{k}", v)
    print(tracking.save_report("surface_defects", report))
    for model, m in results.items():
        print(model, m)


if __name__ == "__main__":
    main()
