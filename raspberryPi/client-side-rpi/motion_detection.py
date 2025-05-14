import cv2
import time
from datetime import datetime

# Set up video capture (0 = default camera, works for USB or Pi with drivers)
cap = cv2.VideoCapture(0)
time.sleep(2)  # Warm-up time

# First frame (baseline)
ret, frame1 = cap.read()
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)

while True:
    ret, frame2 = cap.read()
    if not ret:
        break

    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

    # Difference between frames
    delta = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    movement = False

    for contour in contours:
        if cv2.contourArea(contour) > 200:  # Adjust for insect size
            movement = True
            break

    if movement:
        filename = f"insect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame2)
        print(f"📸 Insect detected! Photo saved: {filename}")
        time.sleep(2)  # Optional: Pause briefly to avoid rapid captures

    # Update reference frame
    gray1 = gray2

    # Optional: quit with 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
