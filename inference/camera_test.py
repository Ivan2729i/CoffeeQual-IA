import cv2
import time

url = "rtsp://192.168.100.10:8554/live/gopro"
#url = "rtmp://itverland.com/live/stream"

print("Conectando al stream...")

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

time.sleep(2)

if not cap.isOpened():
    raise RuntimeError("No se pudo abrir el stream.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Esperando frame...")
        time.sleep(0.05)
        continue

    cv2.imshow("GoPro Live", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
