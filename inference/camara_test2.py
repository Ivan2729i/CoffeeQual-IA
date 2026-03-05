import cv2

# La GoPro suele ser VideoCapture(0) o 1
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara USB")

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("GoPro USB Live", frame)

    # Presiona 'q' para salir
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()