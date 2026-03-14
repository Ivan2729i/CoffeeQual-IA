import cv2
import os

url = os.getenv("CAM1_RTSP_URL")

cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("No se pudo abrir la camara")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo leer el frame")
        break

    frame_small = cv2.resize(frame, (640, 360))
    cv2.imshow("Camara", frame_small)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()