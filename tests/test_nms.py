import numpy as np
import pytest

from vision.nms import C_AVAILABLE, nms_c, nms_numpy, random_boxes


def test_numpy_nms_removes_overlapping_lower_score_box():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=np.float32)
    scores = np.array([0.9, 0.8, 0.7], dtype=np.float32)
    assert list(nms_numpy(boxes, scores, 0.5)) == [0, 2]


@pytest.mark.skipif(not C_AVAILABLE, reason="C library not built (CI builds it with gcc)")
def test_c_nms_matches_numpy():
    boxes, scores = random_boxes(2000, seed=3)
    assert np.array_equal(nms_c(boxes, scores, 0.5), nms_numpy(boxes, scores, 0.5))
