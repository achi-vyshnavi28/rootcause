/*
 * Non-maximum suppression in C. Detectors (YOLO etc.) output many overlapping boxes per object;
 * NMS keeps the highest-scoring box and removes boxes that overlap it by more than `iou_threshold`.
 *
 * Build (Linux / CI):  gcc -O3 -shared -fPIC -o vision/libnms.so vision/nms.c
 * Build (Windows):     cl /O2 /LD vision\nms.c /Fe:vision\nms.dll     (needs Visual Studio Build Tools)
 */
#include <stdlib.h>

typedef struct { float score; int index; } Scored;

static int by_score_desc(const void *a, const void *b) {
    float sa = ((const Scored *)a)->score, sb = ((const Scored *)b)->score;
    return (sa < sb) - (sa > sb);
}

static float iou(const float *a, const float *b) {
    float x1 = a[0] > b[0] ? a[0] : b[0], y1 = a[1] > b[1] ? a[1] : b[1];
    float x2 = a[2] < b[2] ? a[2] : b[2], y2 = a[3] < b[3] ? a[3] : b[3];
    float w = x2 - x1, h = y2 - y1;
    if (w <= 0 || h <= 0) return 0.0f;
    float inter = w * h;
    float area_a = (a[2] - a[0]) * (a[3] - a[1]), area_b = (b[2] - b[0]) * (b[3] - b[1]);
    return inter / (area_a + area_b - inter);
}

/* boxes: n x 4 (x1, y1, x2, y2), scores: n. Writes kept indices to `keep`, returns how many. */
#ifdef _WIN32
__declspec(dllexport)
#endif
int nms(const float *boxes, const float *scores, int n, float iou_threshold, int *keep) {
    Scored *order = malloc(sizeof(Scored) * n);
    char *removed = calloc(n, 1);
    int kept = 0;
    for (int i = 0; i < n; i++) { order[i].score = scores[i]; order[i].index = i; }
    qsort(order, n, sizeof(Scored), by_score_desc);
    for (int i = 0; i < n; i++) {
        int bi = order[i].index;
        if (removed[bi]) continue;
        keep[kept++] = bi;
        for (int j = i + 1; j < n; j++) {
            int bj = order[j].index;
            if (!removed[bj] && iou(&boxes[4 * bi], &boxes[4 * bj]) > iou_threshold) removed[bj] = 1;
        }
    }
    free(order);
    free(removed);
    return kept;
}
