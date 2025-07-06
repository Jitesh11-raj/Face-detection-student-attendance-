import cv2
import sqlite3
from datetime import datetime
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox
import os
import time

# Initialize OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Directory to store student images
IMAGE_DIR = "student_images/"

# Function to create a new SQLite database if it doesn't exist or is corrupted
def create_database():
    try:
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()

        # Create user table if not exists
        c.execute('''CREATE TABLE IF NOT EXISTS students
                     (id INTEGER PRIMARY KEY, student_id TEXT UNIQUE, name TEXT)''')

        # Create attendance table if not exists
        c.execute('''CREATE TABLE IF NOT EXISTS attendance
                     (id INTEGER PRIMARY KEY, student_id TEXT, time TEXT,
                     FOREIGN KEY(student_id) REFERENCES students(student_id))''')

        conn.commit()
        conn.close()
        return True

    except sqlite3.DatabaseError as e:
        print(f"Error creating database: {str(e)}")
        return False

# Attempt to recover the database
def recover_database():
    try:
        os.rename('attendance.db', 'attendance_backup.db')
        create_database()
        return True

    except Exception as e:
        print(f"Error recovering database: {str(e)}")
        return False

# Check if the database exists and is valid
def check_database():
    if os.path.exists('attendance.db'):
        try:
            conn = sqlite3.connect('attendance.db')
            conn.execute("PRAGMA integrity_check;")
            conn.close()
            return True

        except sqlite3.DatabaseError:
            print("Database is corrupted.")
            return False
    else:
        return False

# Create or recover the database
if not check_database():
    print("Creating/recovering database...")

    if not create_database() and not recover_database():
        print("Failed to create/recover database.")
        exit()

# Function to register a new student
def register_student():
    def add_student():
        student_id = student_id_entry.text()
        name = name_entry.text()

        if len(student_id) != 5:
            QMessageBox.warning(add_student_window, "Error", "Student ID must be 5 digits long.")
            return
        if not name:
            QMessageBox.warning(add_student_window, "Error", "Please enter the name.")
            return

        try:
            conn = sqlite3.connect('attendance.db')
            c = conn.cursor()

            c.execute("SELECT * FROM students WHERE student_id=?", (student_id,))
            existing_student = c.fetchone()

            if existing_student:
                QMessageBox.warning(add_student_window, "Error", "Student ID already exists. Please choose a different one.")
                conn.close()
                return

            c.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
            conn.commit()

            capture_and_save_image(student_id)
            conn.close()

            # Open webcam for 10 seconds before showing success message
            elapsed_time = open_webcam_for_10_seconds(student_id)
            QMessageBox.information(add_student_window, "Success", "Student registered successfully.")
            add_student_window.close()

        except Exception as e:
            QMessageBox.critical(add_student_window, "Error", f"An error occurred: {str(e)}")

    def capture_and_save_image(student_id):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)

        image_path = os.path.join(IMAGE_DIR, f"{student_id}.jpg")
        cv2.imwrite(image_path, frame)

    def open_webcam_for_10_seconds(student_id):
        cap = cv2.VideoCapture(0)
        start_time = time.time()

        while time.time() - start_time < 10:
            ret, frame = cap.read()
            elapsed_time = int(time.time() - start_time)
            cv2.putText(frame, f" Elapsed Time: {elapsed_time} seconds", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            cv2.imshow('Face Attendance', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        return elapsed_time

    app = QApplication(sys.argv)
    add_student_window = QWidget()
    add_student_window.setWindowTitle("Register Student")

    student_id_label = QLabel("Student ID (5 digits):", add_student_window)
    student_id_label.move(10, 10)

    student_id_entry = QLineEdit(add_student_window)
    student_id_entry.move(150, 10)

    name_label = QLabel("Name:", add_student_window)
    name_label.move(10, 50)

    name_entry = QLineEdit(add_student_window)
    name_entry.move(150, 50)

    register_button = QPushButton("Register", add_student_window)
    register_button.move(100, 100)
    register_button.clicked.connect(add_student)

    add_student_window.setGeometry(100, 100, 300, 150)
    add_student_window.show()
    sys.exit(app.exec_())


# Login with unique ID user as register.
def login():
    def capture_attendance(student_id):
        cap = cv2.VideoCapture(0)
        start_time = time.time()

        while True:
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                roi_gray = gray[y:y + h, x:x + w]

            elapsed_time = time.time() - start_time
            cv2.putText(frame, f"Time Elapsed: {int(elapsed_time)} seconds", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('Face Attendance', frame)

            if elapsed_time >= 10:
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                try:
                    conn = sqlite3.connect('attendance.db')
                    c = conn.cursor()

                    c.execute("INSERT INTO attendance (student_id, time) VALUES (?, ?)", (student_id, current_time))
                    conn.commit()
                    conn.close()

                    QMessageBox.information(login_window, "Success", "Attendance marked successfully.")
                except Exception as e:
                    QMessageBox.critical(login_window, "Error", f"An error occurred: {str(e)}")

                break

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

        def validate_login():
            student_id = student_id_entry.text()

            try:
                conn = sqlite3.connect('attendance.db')
                c = conn.cursor()

                c.execute("SELECT * FROM students WHERE student_id=?", (student_id,))
                student = c.fetchone()
                conn.close()

                if student:
                    login_window.close()
                    capture_attendance(student_id)
                else:
                    QMessageBox.warning(login_window, "Error", "Invalid student ID.")

            except Exception as e:
                QMessageBox.critical(login_window, "Error", f"An error occurred: {str(e)}")

        app = QApplication(sys.argv)
        login_window = QWidget()
        login_window.setWindowTitle("Login")

        student_id_label = QLabel("Student ID:", login_window)
        student_id_label.move(10, 10)

        student_id_entry = QLineEdit(login_window)
        student_id_entry.move(150, 10)

        login_button = QPushButton("Login", login_window)
        login_button.move(100, 50)
        login_button.clicked.connect(validate_login)

        login_window.setGeometry(100, 100, 300, 100)
        login_window.show()
        sys.exit(app.exec_())

    # Function to delete a student's attendance records
    def delete_student():
        def delete():
            student_id = student_id_entry.text()

            try:
                conn = sqlite3.connect('attendance.db')
                c = conn.cursor()

                c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
                conn.commit()
                conn.close()

                QMessageBox.information(delete_student_window, "Success", "Attendance records deleted successfully.")
                delete_student_window.close()

            except Exception as e:
                QMessageBox.critical(delete_student_window, "Error", f"An error occurred: {str(e)}")

        app = QApplication(sys.argv)
        delete_student_window = QWidget()
        delete_student_window.setWindowTitle("Delete Student")

        student_id_label = QLabel("Student ID:", delete_student_window)
        student_id_label.move(10, 10)

        student_id_entry = QLineEdit(delete_student_window)
        student_id_entry.move(150, 10)

        delete_button = QPushButton("Delete", delete_student_window)
        delete_button.move(100, 50)
        delete_button.clicked.connect(delete)

        delete_student_window.setGeometry(100, 100, 300, 100)
        delete_student_window.show()
        sys.exit(app.exec_())

    # Command-line interface for registration, login, and deletion
    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Attendance System")

            register_button = QPushButton("Register Student", self)
            register_button.clicked.connect(register_student)
            register_button.move(50, 50)

            login_button = QPushButton("Login", self)
            login_button.clicked.connect(login)
            login_button.move(200, 50)

            delete_button = QPushButton("Delete Student", self)
            delete_button.clicked.connect(delete_student)
            delete_button.move(350, 50)

            self.setGeometry(100, 100, 500, 150)

    if __name__ == '__main__':
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())

