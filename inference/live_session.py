import time
import threading
from dataclasses import dataclass, field
from collections import Counter
import cv2
from inference.predictor import get_model
from inference.grading import grade_from_counts
from dashboard.camera_hub import get_camera_worker


@dataclass
class FrameStat:
    counts: Counter = field(default_factory=Counter)
    total_conf: float = 0.0
    detections: int = 0

    def score(self) -> float:
        if self.detections <= 0:
            return 0.0
        return self.total_conf


class LiveEvalSession:
    """
    Sesión de evaluación en vivo para 1 cámara:
    - Lee frames desde camera_hub
    - Corre YOLO (sin tracking)
    - Deduplica cajas por solapamiento en cada frame
    - Se queda con el mejor conteo observado durante la sesión
    - Produce frame anotado (para MJPEG)
    """

    def __init__(
        self,
        cam_id: str,
        source_config: dict,
        duration_s: int = 15,
        conf_display: float = 0.22,
        conf_count: float = 0.30,
        tracker_cfg: str = "bytetrack.yaml",  # se deja por compatibilidad, pero no se usa
    ):
        self.cam_id = cam_id
        self.source_config = source_config
        self.duration_s = duration_s
        self.conf_display = conf_display
        self.conf_count = conf_count
        self.tracker_cfg = tracker_cfg

        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_flag = False

        self.state = "idle"
        self.started_at = None
        self.ends_at = None
        self.error = None

        self.latest_jpeg: bytes | None = None
        self.final_payload: dict | None = None

        self._best_frame_stat = FrameStat()
        self._best_counts: Counter = Counter()

    def is_running(self) -> bool:
        with self._lock:
            return self.state == "running"

    def start(self):
        with self._lock:
            if self.state == "running":
                return
            self._stop_flag = False
            self.error = None
            self.final_payload = None
            self.latest_jpeg = None
            self._best_frame_stat = FrameStat()
            self._best_counts = Counter()
            self.state = "running"
            self.started_at = time.time()
            self.ends_at = self.started_at + self.duration_s

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        with self._lock:
            self._stop_flag = True

    def status(self) -> dict:
        with self._lock:
            now = time.time()
            remaining = None
            if self.state == "running" and self.ends_at:
                remaining = max(0, int(self.ends_at - now))

            return {
                "state": self.state,
                "remaining_s": remaining,
                "error": self.error,
                "final": self.final_payload,
            }

    def get_latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self.latest_jpeg

    def _cls_name(self, names, cls_id: int) -> str:
        if isinstance(names, dict):
            return names.get(cls_id, str(cls_id))
        if isinstance(names, list):
            if 0 <= cls_id < len(names):
                return names[cls_id]
        return str(cls_id)

    def _iou(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(1, (ax2 - ax1)) * max(1, (ay2 - ay1))
        area_b = max(1, (bx2 - bx1)) * max(1, (by2 - by1))

        union = area_a + area_b - inter_area
        return inter_area / union if union > 0 else 0.0

    def _dedupe_packed(self, packed, iou_thr=0.45):
        """
        packed: [x1, y1, x2, y2, conf, cls_id]
        deja solo la caja de mayor confianza cuando hay mucho solapamiento
        """
        packed = sorted(packed, key=lambda x: x[4], reverse=True)
        kept = []

        for cand in packed:
            cbox = cand[:4]
            should_keep = True

            for prev in kept:
                pbox = prev[:4]
                if self._iou(cbox, pbox) >= iou_thr:
                    should_keep = False
                    break

            if should_keep:
                kept.append(cand)

        return kept

    def _draw_boxes(self, frame, boxes, names):
        h, w = frame.shape[:2]

        for b in boxes:
            x1, y1, x2, y2, conf, cls_id = b

            x1 = max(0, min(int(x1), w - 1))
            y1 = max(0, min(int(y1), h - 1))
            x2 = max(0, min(int(x2), w - 1))
            y2 = max(0, min(int(y2), h - 1))

            cls_name = self._cls_name(names, int(cls_id))
            label = f"{cls_name} {conf:.2f}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                label,
                (x1, max(15, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        return frame

    def _counts_from_packed(self, packed, names):
        counts = Counter()
        total_conf = 0.0
        detections = 0

        for x1, y1, x2, y2, conf, cls_id in packed:
            if conf < self.conf_count:
                continue
            cls_name = self._cls_name(names, int(cls_id))
            counts[cls_name] += 1
            total_conf += float(conf)
            detections += 1

        stat = FrameStat(counts=counts, total_conf=total_conf, detections=detections)
        return stat

    def _finalize_counts(self) -> dict:
        counts = dict(self._best_counts)
        grading = grade_from_counts(counts)
        payload = {
            "counts": counts,
            **grading,
        }
        return payload

    def _run_loop(self):
        try:
            model = get_model()
            names = model.names

            worker = get_camera_worker(self.cam_id, self.source_config)
            t0 = time.time()

            while worker.get_frame() is None:
                time.sleep(0.2)
                if time.time() - t0 > 10:
                    raise RuntimeError("No se pudo obtener frame de la cámara (timeout).")

            while True:
                with self._lock:
                    if self._stop_flag:
                        break
                    if self.ends_at and time.time() >= self.ends_at:
                        break

                frame = worker.get_frame()
                if frame is None:
                    time.sleep(0.02)
                    continue

                drawn = frame.copy()

                results = model.predict(
                    source=frame,
                    conf=self.conf_display,
                    verbose=False,
                )

                if not results:
                    ok2, jpg = cv2.imencode(".jpg", drawn)
                    if ok2:
                        with self._lock:
                            self.latest_jpeg = jpg.tobytes()
                    continue

                r0 = results[0]
                boxes = r0.boxes

                packed = []

                if boxes is not None and boxes.xyxy is not None and len(boxes) > 0:
                    xyxy = boxes.xyxy.cpu().numpy()
                    confs = boxes.conf.cpu().numpy()
                    clss = boxes.cls.cpu().numpy()

                    for i in range(len(xyxy)):
                        x1, y1, x2, y2 = xyxy[i]
                        conf = float(confs[i])
                        cls_id = int(clss[i])

                        w_box = max(1, x2 - x1)
                        h_box = max(1, y2 - y1)
                        area = w_box * h_box

                        if area > 9000:
                            continue

                        packed.append([x1, y1, x2, y2, conf, cls_id])

                if packed:
                    packed = self._dedupe_packed(packed, iou_thr=0.45)
                    drawn = self._draw_boxes(drawn, packed, names)

                    frame_stat = self._counts_from_packed(packed, names)

                    # guarda el mejor frame de la sesión:
                    # prioriza más detecciones; en empate, mayor suma de confianza
                    best_det = self._best_frame_stat.detections
                    cur_det = frame_stat.detections

                    if (
                        cur_det > best_det
                        or (cur_det == best_det and frame_stat.score() > self._best_frame_stat.score())
                    ):
                        self._best_frame_stat = frame_stat
                        self._best_counts = frame_stat.counts.copy()

                ok2, jpg = cv2.imencode(".jpg", drawn)
                if ok2:
                    with self._lock:
                        self.latest_jpeg = jpg.tobytes()

            final_payload = self._finalize_counts()
            with self._lock:
                self.final_payload = final_payload
                self.state = "finished"

        except Exception as e:
            with self._lock:
                self.error = str(e)
                self.state = "error"