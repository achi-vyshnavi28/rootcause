import numpy as np

from vision.defects import classical_map, greedy_coreset, pointing_hit


def _surface(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(150, 18, (640, 256)), 0, 255).astype(np.uint8)


def test_classical_detector_scores_a_crack_higher_and_points_at_it():
    clean = _surface()
    cracked = clean.copy()
    cracked[300:303, 90:170] = 70  # thin dark horizontal crack
    mask = np.zeros_like(cracked, dtype=bool)
    mask[300:303, 90:170] = True
    amap = classical_map(cracked)
    assert amap.max() > classical_map(clean).max() * 1.3
    assert pointing_hit(amap, mask)


def test_edge_artefacts_are_ignored():
    img = _surface()
    img[:, :8] = 20  # dark strip at the very edge
    assert classical_map(img)[:, :10].max() == 0


def test_greedy_coreset_keeps_rare_points():
    common = np.zeros((500, 2))
    rare = np.array([[10.0, 10.0]])
    bank = greedy_coreset(np.vstack([common, rare]), size=2)
    assert any(np.allclose(p, rare[0]) for p in bank)
