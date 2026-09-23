"""PatchCore (Roth et al., "Towards Total Recall in Industrial Anomaly Detection", CVPR 2022), from the paper.

Idea: learn what GOOD looks like, patch by patch, and flag anything far from it. No defect examples needed.
  1. A pretrained CNN (ResNet-18, ImageNet) turns every image into a grid of local patch features
     (layer2 + upsampled layer3, averaged over a 3x3 neighbourhood for context).
  2. Memory bank = patch features of all GOOD training images, reduced with greedy k-center
     "coreset" sampling so it stays small but still covers every kind of normal patch.
  3. Anomaly score of a test patch = distance to its nearest neighbour in the memory bank.
     Image score = the highest patch score. The per-patch scores form a defect heatmap.

    python -m vision.patchcore      (needs data/raw/kolektor and the ResNet-18 ImageNet weights)
"""

import numpy as np
import torch
import torch.nn.functional as F
import torchvision
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from ml import tracking
from vision.kolektor import load_pairs

IMG_SIZE = (320, 128)  # (height, width): KolektorSDD images are tall and narrow
MEAN, STD = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1), torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


class FeatureExtractor(torch.nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = torchvision.models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        net = torchvision.models.resnet18(weights=weights).eval()
        self.stem = torch.nn.Sequential(net.conv1, net.bn1, net.relu, net.maxpool, net.layer1)
        self.layer2, self.layer3 = net.layer2, net.layer3

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(N,3,H,W) -> (N, H/8 * W/8, 384) patch features."""
        f2 = self.layer2(self.stem(x))
        f3 = self.layer3(f2)
        f3 = F.interpolate(f3, size=f2.shape[-2:], mode="bilinear", align_corners=False)
        feats = torch.cat([F.avg_pool2d(f2, 3, 1, 1), F.avg_pool2d(f3, 3, 1, 1)], dim=1)
        return feats.permute(0, 2, 3, 1).reshape(x.shape[0], -1, feats.shape[1])


def greedy_coreset(features: torch.Tensor, n: int, proj_dim: int = 128, seed: int = 0) -> torch.Tensor:
    """k-center greedy: repeatedly add the point farthest from everything chosen so far.

    Distances are computed in a random low-dimensional projection (as in the paper) to keep it fast.
    """
    if n >= len(features):
        return features
    g = torch.Generator().manual_seed(seed)
    proj = features @ torch.randn(features.shape[1], proj_dim, generator=g) / proj_dim ** 0.5
    chosen = [int(torch.randint(len(features), (1,), generator=g))]
    min_dist = torch.cdist(proj, proj[chosen]).squeeze(1)
    for _ in range(n - 1):
        idx = int(torch.argmax(min_dist))
        chosen.append(idx)
        min_dist = torch.minimum(min_dist, torch.cdist(proj, proj[idx:idx + 1]).squeeze(1))
    return features[chosen]


def nearest_distance(queries: torch.Tensor, bank: torch.Tensor, chunk: int = 4096) -> torch.Tensor:
    return torch.cat([torch.cdist(q, bank).min(dim=1).values for q in queries.split(chunk)])


class PatchCore:
    def __init__(self, extractor: FeatureExtractor, coreset_size: int = 4000, seed: int = 0):
        self.extractor, self.coreset_size, self.seed = extractor, coreset_size, seed
        self.bank: torch.Tensor | None = None
        self.grid: tuple[int, int] = (IMG_SIZE[0] // 8, IMG_SIZE[1] // 8)

    def _embed(self, images: torch.Tensor) -> torch.Tensor:
        return self.extractor((images - MEAN) / STD)

    def fit(self, good_images: torch.Tensor, batch: int = 16) -> "PatchCore":
        feats = torch.cat([self._embed(b).reshape(-1, 384) for b in good_images.split(batch)])
        g = torch.Generator().manual_seed(self.seed)
        pool = feats[torch.randperm(len(feats), generator=g)[:60_000]]  # random pre-subsample, then coreset
        self.bank = greedy_coreset(pool, self.coreset_size, seed=self.seed)
        return self

    def score(self, images: torch.Tensor, batch: int = 16) -> tuple[np.ndarray, np.ndarray]:
        """Returns (image scores, patch heatmaps of shape (N, H/8, W/8))."""
        maps = []
        for b in images.split(batch):
            f = self._embed(b)
            d = nearest_distance(f.reshape(-1, 384), self.bank).reshape(len(b), *self.grid)
            maps.append(d)
        heat = torch.cat(maps).numpy()
        return heat.reshape(len(heat), -1).max(axis=1), heat


def load_tensors() -> tuple[torch.Tensor, np.ndarray, np.ndarray]:
    import cv2

    imgs, labels, parts = [], [], []
    for img_path, mask_path, part in load_pairs():
        img = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, IMG_SIZE[::-1], interpolation=cv2.INTER_AREA)
        imgs.append(torch.from_numpy(img).permute(2, 0, 1).float() / 255.0)
        labels.append(int(cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE).max() > 0))
        parts.append(part)
    return torch.stack(imgs), np.array(labels), np.array(parts)


def evaluate(splits: int = 5) -> dict:
    images, labels, parts = load_tensors()
    extractor = FeatureExtractor(pretrained=True)
    scores = {"roc_auc": [], "average_precision": [], "recall_at_5pct_false_reject": []}
    for seed in range(splits):
        tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed).split(images, groups=parts))
        good_train = tr[labels[tr] == 0]  # PatchCore only ever sees good parts
        model = PatchCore(extractor, seed=seed).fit(images[good_train])
        s, _ = model.score(images[te])
        y = labels[te]
        if len(set(y)) < 2:
            continue
        scores["roc_auc"].append(roc_auc_score(y, s))
        scores["average_precision"].append(average_precision_score(y, s))
        threshold = np.quantile(s[y == 0], 0.95)
        scores["recall_at_5pct_false_reject"].append(float((s[y == 1] > threshold).mean()))
        print(f"split {seed}: AUROC {scores['roc_auc'][-1]:.3f}  AP {scores['average_precision'][-1]:.3f}")
    return {k: {"mean": round(float(np.mean(v)), 3), "std": round(float(np.std(v)), 3), "runs": len(v)} for k, v in scores.items()}


def main() -> None:
    report = {"dataset": "KolektorSDD", "method": "PatchCore (ResNet-18 layer2+3, greedy coreset 4000, kNN distance)",
              "image_size": IMG_SIZE, "trained_on": "good images only", "image_level": evaluate()}
    with tracking.start("kolektor_patchcore"):
        import mlflow

        for k, v in report["image_level"].items():
            mlflow.log_metric(k, v["mean"])
    print(tracking.save_report("vision_kolektor_patchcore", report))
    for k, v in report["image_level"].items():
        print(f"{k:<30} {v['mean']:.3f} +/- {v['std']:.3f}")


if __name__ == "__main__":
    main()
