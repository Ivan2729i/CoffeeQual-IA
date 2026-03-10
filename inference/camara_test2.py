import cv2

# URL HLS, usa local si estás en la misma VM
hls_url = "http://itverland.com:8080/hls/stream.m3u8"

cap = cv2.VideoCapture(hls_url)

if not cap.isOpened():
    raise RuntimeError("No se pudo abrir el stream HLS")

while True:
    ret, frame = cap.read()
    if not ret:
        print("No hay más frames, esperando...")
        cv2.waitKey(1000)  # espera 1s y vuelve a intentar
        continue

    cv2.imshow("HLS Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()