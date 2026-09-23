"""PatchCore (CNN features) on synthetic images: random weights, no dataset, runs in CI in seconds."""

import numpy as np
import torch

from vision.patchcore import FeatureExtractor, PatchCore, greedy_coreset


def _surface(crack: bool, seed: int) -> torch.Tensor:
    rng = np.random.default_rng(seed)
    img = np.full((320, 128), 150.0) + rng.normal(0, 4, (320, 128)) + 20 * np.sin(np.arange(128) / 6)[None, :]
    if crack:
        img[150:185, 60:63] -= 70
    img = np.clip(img, 0, 255) / 255.0
    return torch.from_numpy(np.stack([img] * 3)).float()


def test_greedy_coreset_covers_all_clusters():
    g = torch.Generator().manual_seed(0)
    clusters = [torch.randn(300, 8, generator=g) * 0.1 + c for c in (0.0, 5.0, -5.0, 10.0)]
    chosen = greedy_coreset(torch.cat(clusters), 4, proj_dim=8)
    assert sorted(round(float(v)) for v in chosen.mean(dim=1)) == [-5, 0, 5, 10]


def test_patchcore_scores_defect_higher_and_returns_heatmap():
    torch.manual_seed(0)
    good = torch.stack([_surface(False, s) for s in range(4)])
    test = torch.stack([_surface(False, 99), _surface(True, 98)])
    model = PatchCore(FeatureExtractor(pretrained=False), coreset_size=300).fit(good)
    scores, heat = model.score(test)
    assert scores[1] > scores[0]
    assert heat.shape == (2, 40, 16)
