import cv2
import numpy as np
import os
import pyodbc
from datetime import datetime

# Database connection
def connect_db():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=ABDEYALI\\SQLEXPRESS;'
        'DATABASE=Face_Recognization;'
        'UID=jobportal;'
        'PWD=123;'
    )

# Train face recognition model
def train_face_recognition():
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = []
    labels = []
    label_map = {}

    # Fetch users from DB
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Id, UserID, name FROM users")
    users = cursor.fetchall()
    conn.close()

    for user in users:
        user_id = user.Id
        user_folder = os.path.join("dataset", f"User.{user.UserID}")
        if not os.path.isdir(user_folder):
            continue

        label_map[user_id] = user.name  # Label = user DB Id, mapped to name
        for image_file in os.listdir(user_folder):
            image_path = os.path.join(user_folder, image_file)
            img = cv2.imread(image_path)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces_detected = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (x, y, w, h) in faces_detected:
                face = gray[y:y + h, x:x + w]
                faces.append(face)
                labels.append(user_id)

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    return recognizer, label_map

# Record attendance
def record_attendance(user_id, user_name):
    conn = connect_db()
    cursor = conn.cursor()
    today = datetime.now().date()

    # Avoid duplicate entries for the same date
    cursor.execute(
        "SELECT * FROM Attendance WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    if cursor.fetchone():
        conn.close()
        return  # Already marked

    cursor.execute(
        "INSERT INTO Attendance (user_id, name, date) VALUES (?, ?, ?)",
        (user_id, user_name, today)
    )
    conn.commit()
    conn.close()

# Attendance check and face recognition
def check_attendance():
    recognizer, label_map = train_face_recognition()
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = recognizer.predict(face)

            if confidence < 100 and label in label_map:
                user_name = label_map[label]
                cv2.putText(frame, f"Hello {user_name}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                record_attendance(label, user_name)
                print(f"✅ Attendance marked for {user_name}")
            else:
                cv2.putText(frame, "Unknown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
            break

    cap.release()
    cv2.destroyAllWindows()

# Start system
check_attendance()
