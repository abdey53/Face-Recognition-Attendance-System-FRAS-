from flask import Flask, render_template, request
import cv2
import os
import pyodbc
import winsound
import numpy as np

app = Flask(__name__)

# Ensure dataset directory exists
if not os.path.exists('dataset'):
    os.makedirs('dataset')

# ✅ Database connection function
def connect_db():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=ABDEYALI\\SQLEXPRESS;'
        'DATABASE=Face_Recognization;'
        'UID=jobportal;'
        'PWD=123;'
    )

@app.route('/attendance', methods=['GET'])
def attendance():
    filter_date = request.args.get('filter_date')  # Get the selected date
    conn = connect_db()
    cursor = conn.cursor()

    # If a date is provided, filter the records by that date
    if filter_date:
        cursor.execute("""
            SELECT id, user_id, name, date, CONVERT(VARCHAR, create_Date, 108) AS time
            FROM Attendance
            WHERE date = ?
        """, (filter_date,))
    else:
        cursor.execute("""
            SELECT id, user_id, name, date, CONVERT(VARCHAR, create_Date, 108) AS time
            FROM Attendance
            order by date desc
        """)

    attendance = cursor.fetchall()
    conn.close()

    return render_template('attendance.html', attendance=attendance, filter_date=filter_date)


# ✅ Home route
@app.route('/')
def home():
    return render_template('index.html')

# ✅ Attendance route (shows table on UI)
@app.route("/attendance")
def show_attendance():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, date, create_Date FROM Attendance ORDER BY create_Date DESC")
    records = cursor.fetchall()
    conn.close()

    attendance_data = [{
        'id': row.id,
        'user_id': row.user_id,
        'name': row.name,
        'date': row.date.strftime('%Y-%m-%d'),
        'time': row.create_Date.strftime('%H:%M:%S')
    } for row in records]

    return render_template("attendance.html", attendance=attendance_data)


# ✅ Collect face route
@app.route('/collect', methods=['POST'])
def collect():
    user_id = request.form['user_id']
    user_name = request.form['user_name']

    user_folder = os.path.join('dataset', f'User.{user_id}')
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return "❌ Error: Could not open webcam. Please check your camera."

    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    total_samples = 30
    count = 0

    while True:
        ret, img = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            if count >= total_samples:
                break

            count += 1
            face_image_path = os.path.join(user_folder, f"{count}.jpg")
            cv2.imwrite(face_image_path, gray[y:y+h, x:x+w])

            # Draw face rectangle
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # ✅ Beep on capture
            winsound.Beep(1000, 200)

        # ✅ Progress bar (bottom of frame)
        progress = int((count / total_samples) * 500)
        cv2.rectangle(img, (50, 450), (550, 470), (255, 255, 255), -1)  # Background
        cv2.rectangle(img, (50, 450), (50 + progress, 470), (0, 255, 0), -1)  # Filled

        cv2.putText(img, f'Collecting: {count}/{total_samples}', (50, 440),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow('Collecting Faces - Press Q to stop', img)

        if cv2.waitKey(1) & 0xFF == ord('q') or count >= total_samples:
            break

    cam.release()
    cv2.destroyAllWindows()

    # ✅ Save last image to DB
    conn = connect_db()
    cursor = conn.cursor()

    image_path = os.path.join(user_folder, f"{count}.jpg")
    image = cv2.imread(image_path)
    _, img_encoded = cv2.imencode('.jpg', image)
    img_binary = img_encoded.tobytes()

    insert_query = "INSERT INTO users (UserID, name, Image) VALUES (?, ?, ?)"
    cursor.execute(insert_query, (user_id, user_name, img_binary))

    conn.commit()
    cursor.close()
    conn.close()

    # ✅ Final success message
    success_image = 255 * np.ones((300, 600, 3), dtype=np.uint8)
    cv2.putText(success_image, f"✅ {count} Faces Captured!", (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.imshow("Success", success_image)
    cv2.waitKey(2000)
    cv2.destroyAllWindows()

    return f"✅ Collected {count} face samples for {user_name} (ID: {user_id})"
if __name__ == '__main__':
    app.run(debug=True)
