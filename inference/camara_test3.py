import cv2

# Prueba con 0, 1, 2 o 3 si no abre en el primero
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("No se pudo abrir la cámara")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo leer el frame")
        break

    cv2.imshow("Camara Iriun", frame)

    # ESC para salir
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()