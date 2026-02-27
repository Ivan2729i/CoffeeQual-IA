import time
import threading
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import cv2
from inference.predictor import get_model
from inference.grading import grade_from_counts


@dataclass
class TrackStat:
    frames_seen: int = 0
    max_conf: float = 0.0
    votes: Counter = field(default_factory=Counter)

    def update(self, cls_name: str, conf: float):
        self.frames_seen += 1
        if conf > self.max_conf:
            self.max_conf = conf
        self.votes[cls_name] += 1

    def final_class(self) -> str | None:
        if not self.votes:
            return None
        return self.votes.most_common(1)[0][0]


class LiveEvalSession:
    """
    Sesión de evaluación en vivo para 1 cámara:
    - Lee RTSP
    - Corre YOLO+ByteTrack
    - Produce frame anotado (para MJPEG)
    - Produce conteos por ID únicos confirmados
    - Termina automáticamente a los N segundos (default 30)
    """

    def __init__(
        self,
        rtsp_url: str,
        duration_s: int = 30,
        conf_display: float = 0.35,
        conf_count: float = 0.50,
        min_frames_confirm: int = 5,
        tracker_cfg: str = "bytetrack.yaml",
    ):
        self.rtsp_url = rtsp_url
        self.duration_s = duration_s
        self.conf_display = conf_display
        self.conf_count = conf_count
        self.min_frames_confirm = min_frames_confirm
        self.tracker_cfg = tracker_cfg

        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_flag = False

        # Estado público
        self.state = "idle"  # idle | running | finished | error
        self.started_at = None
        self.ends_at = None
        self.error = None

        self.latest_jpeg: bytes | None = None  # frame anotado
        self.latest_preview_counts: dict = {"primary": {}, "secondary": {}}
        self.final_payload: dict | None = None  # lo que se guarda al terminar

        # tracking data
        self._tracks: dict[int, TrackStat] = defaultdict(TrackStat)
        self._counted_ids: set[int] = set()  # IDs ya contados (cuando cumplen las reglas)

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
            self._tracks.clear()
            self._counted_ids.clear()
            self.latest_jpeg = None
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

    def _finalize_counts(self) -> dict:
        """
        Aplica reglas:
        - frames_seen >= min_frames_confirm
        - max_conf >= conf_count (al menos una vez)
        - 1 vez por ID
        - clase final = voto mayoritario
        """
        counts = Counter()

        for tid, st in self._tracks.items():
            if st.frames_seen < self.min_frames_confirm:
                continue
            if st.max_conf < self.conf_count:
                continue

            cls = st.final_class()
            if not cls:
                continue

            counts[cls] += 1

        grading = grade_from_counts(dict(counts))
        payload = {
            "counts": dict(counts),
            **grading,
        }
        return payload

    def _draw_boxes(self, frame, boxes, names):
        """
        Dibujo propio para asegurar etiquetas con ID + clase + conf.
        """
        h, w = frame.shape[:2]
        for b in boxes:
            x1, y1, x2, y2, conf, cls_id, tid = b
            x1 = max(0, min(int(x1), w - 1))
            y1 = max(0, min(int(y1), h - 1))
            x2 = max(0, min(int(x2), w - 1))
            y2 = max(0, min(int(y2), h - 1))

            cls_name = names.get(int(cls_id), str(int(cls_id)))
            label = f"#{int(tid)} {cls_name} {conf:.2f}"

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

    def _run_loop(self):
        try:
            model = get_model()
            names = model.names

            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            t0 = time.time()

            # reintenta apertura
            while not cap.isOpened():
                time.sleep(0.5)
                cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                if time.time() - t0 > 10:
                    raise RuntimeError("No se pudo abrir RTSP (timeout).")

            # tracking persistente
            while True:
                with self._lock:
                    if self._stop_flag:
                        break
                    if self.ends_at and time.time() >= self.ends_at:
                        break

                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                # YOLO TRACK: conf_display para overlay/detección en frame
                # ByteTrack mantiene IDs
                results = model.track(
                    source=frame,
                    conf=self.conf_display,
                    persist=True,
                    tracker=self.tracker_cfg,
                    verbose=False,
                )

                r0 = results[0]
                boxes = r0.boxes

                # Si no hay detecciones, igual emitimos frame
                drawn = frame.copy()

                if boxes is not None and boxes.xyxy is not None and len(boxes) > 0:
                    xyxy = boxes.xyxy.cpu().numpy()
                    confs = boxes.conf.cpu().numpy()
                    clss = boxes.cls.cpu().numpy()

                    # ids pueden venir None si el tracker aún no asigna
                    ids = None
                    if getattr(boxes, "id", None) is not None:
                        ids = boxes.id.cpu().numpy()

                    packed = []
                    for i in range(len(xyxy)):
                        if ids is None or ids[i] is None:
                            continue

                        x1, y1, x2, y2 = xyxy[i]
                        conf = float(confs[i])
                        cls_id = int(clss[i])
                        tid = int(ids[i])

                        cls_name = names.get(cls_id, str(cls_id))

                        # stats para conteo
                        st = self._tracks[tid]
                        st.update(cls_name, conf)

                        packed.append([x1, y1, x2, y2, conf, cls_id, tid])

                    # dibuja cajas con ID
                    if packed:
                        drawn = self._draw_boxes(drawn, packed, names)

                # Comprime a JPG para MJPEG
                ok2, jpg = cv2.imencode(".jpg", drawn)
                if ok2:
                    with self._lock:
                        self.latest_jpeg = jpg.tobytes()

            cap.release()

            # Finaliza resultados
            final_payload = self._finalize_counts()
            with self._lock:
                self.final_payload = final_payload
                self.state = "finished"

        except Exception as e:
            with self._lock:
                self.error = str(e)
                self.state = "error"

