"""NMS with a compiled C fast path (vision/nms.c via ctypes) and a pure-numpy fallback.

`nms()` uses the C library when it has been built (CI builds it with gcc), otherwise numpy.
Both give identical results; `python -m vision.nms` benchmarks them.
"""

import ctypes
import sys
import time
from pathlib import Path

import numpy as np

_LIB_NAME = "nms.dll" if sys.platform == "win32" else "libnms.so"
_LIB_PATH = Path(__file__).with_name(_LIB_NAME)
_lib = None
if _LIB_PATH.exists():
    _lib = ctypes.CDLL(str(_LIB_PATH))
    _lib.nms.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                         ctypes.c_float, ctypes.POINTER(ctypes.c_int)]
    _lib.nms.restype = ctypes.c_int

C_AVAILABLE = _lib is not None


def nms_numpy(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = np.argsort(-scores, kind="stable")
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        w = np.clip(np.minimum(x2[i], x2[order[1:]]) - np.maximum(x1[i], x1[order[1:]]), 0, None)
        h = np.clip(np.minimum(y2[i], y2[order[1:]]) - np.maximum(y1[i], y1[order[1:]]), 0, None)
        inter = w * h
        overlap = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[1:][overlap <= iou_threshold]
    return np.array(keep, dtype=np.int64)


def nms_c(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    if _lib is None:
        raise RuntimeError(f"C library not built ({_LIB_PATH.name}); see vision/nms.c for build commands")
    b = np.ascontiguousarray(boxes, dtype=np.float32)
    s = np.ascontiguousarray(scores, dtype=np.float32)
    keep = np.empty(len(s), dtype=np.int32)
    k = _lib.nms(b.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), s.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                 len(s), ctypes.c_float(iou_threshold), keep.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
    return keep[:k].astype(np.int64)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    return nms_c(boxes, scores, iou_threshold) if C_AVAILABLE else nms_numpy(boxes, scores, iou_threshold)


def random_boxes(n: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, 600, (n, 2))
    wh = rng.uniform(10, 80, (n, 2))
    return np.hstack([xy, xy + wh]).astype(np.float32), rng.uniform(0, 1, n).astype(np.float32)


if __name__ == "__main__":
    boxes, scores = random_boxes(5000)
    for name, fn in [("numpy", nms_numpy), ("c", nms_c if C_AVAILABLE else None)]:
        if fn is None:
            print("c: library not built")
            continue
        t = time.perf_counter()
        for _ in range(5):
            kept = fn(boxes, scores, 0.5)
        print(f"{name}: {len(kept)} boxes kept, {(time.perf_counter() - t) / 5 * 1000:.1f} ms per call")
