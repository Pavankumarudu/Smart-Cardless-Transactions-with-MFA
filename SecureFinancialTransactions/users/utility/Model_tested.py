import cv2
import face_recognition
import numpy as np
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.models import Model
from cryptography.fernet import Fernet
import secrets
import os
from django.conf import settings
from PIL import Image

# --- Face Recognition Setup ---
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_encodings = []
face_names = []
known_face_dir = os.path.join(settings.MEDIA_ROOT, "known_faces")  # Directory to store known faces
os.makedirs(known_face_dir, exist_ok=True)


# --- Load known faces and their encodings ---
def load_known_faces():
    face_encodings.clear()
    face_names.clear()
    
    for filename in os.listdir(known_face_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(known_face_dir, filename)
            try:
                # Open image and ensure it's RGB
                with Image.open(path) as pil_image:
                    pil_image = pil_image.convert("RGB")
                    image = np.array(pil_image)

                # Ensure the image is 8-bit
                if image.dtype != np.uint8:
                    image = image.astype(np.uint8)

                # Check shape
                if len(image.shape) != 3 or image.shape[2] != 3:
                    print(f"[ERROR] {filename}: Image is not standard RGB shape {image.shape}")
                    continue

                # Get face encodings
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    face_encodings.append(encodings[0])
                    face_names.append(os.path.splitext(filename)[0])
                    print(f"[INFO] Loaded face: {filename}")
                else:
                    print(f"[WARNING] No face detected in {filename}")

            except Exception as e:
                print(f"[ERROR] {filename}: {e}")

# Load faces on startup
load_known_faces()


# Capture and store a new face (for demonstration - in real use, this would be part of user registration)
def capture_and_store_face(name):
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        faces = face_cascade.detectMultiScale(frame, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.imshow('Press C to capture', frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):  # Press 'c' to capture
            face_image = frame[y:y + h, x:x + w]
            cv2.imwrite(os.path.join(known_face_dir, f"{name}.jpg"), face_image)
            print(f"Face captured and stored as {name}.jpg")
            load_known_faces()  # Reload known faces after adding a new one
            cap.release()
            cv2.destroyAllWindows()
            return True
        elif cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            cap.release()
            cv2.destroyAllWindows()
            return False


# --- ResNet-50 Feature Extraction Setup ---
base_model = ResNet50(weights='imagenet', include_top=False,
                      input_shape=(224, 224, 3))  # You might need to adjust input_shape
model = Model(inputs=base_model.input, outputs=base_model.output)


def extract_features_resnet50(img_path):
    try:
        img = cv2.imread(img_path)
        img = cv2.resize(img, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
        img_array = np.expand_dims(img, axis=0)
        img_preprocessed = preprocess_input(img_array)
        features = model.predict(img_preprocessed)
        features_flattened = features.flatten()
        return features_flattened
    except Exception as e:
        print(f"Error extracting features: {e}")
        return None


# --- AES Encryption Setup ---
key = Fernet.generate_key()  # Store this securely!
cipher_suite = Fernet(key)


def encrypt(data):
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data


def decrypt(encrypted_data):
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
    return decrypted_data


# --- OTP Generation ---
def generate_otp(length=6):
    return secrets.token_hex(length)[:length].upper()


# --- Main Workflow ---
def main():
    print("Starting Cardless Transaction Simulation")

    # 1. User Initiates Transaction (Simulated)
    print("Simulating user initiating transaction at ATM")

    # 2. Face Recognition
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    recognized_face_name = None
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        faces = face_cascade.detectMultiScale(frame, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)  # Draw rectangle around face

        cv2.imshow('Face Recognition Press F Key', frame)

        if cv2.waitKey(1) & 0xFF == ord('f'):  # Press 'f' to 'freeze' and recognize
            face_locations = face_recognition.face_locations(frame)
            if face_locations:
                face_encodings_current_frame = face_recognition.face_encodings(frame, face_locations)

                for face_encoding in face_encodings_current_frame:
                    matches = face_recognition.compare_faces(face_encodings, face_encoding)
                    if matches:
                        best_match_index = np.argmin(
                            [np.linalg.norm(face_encodings[i] - face_encoding) for i in range(len(face_encodings))])
                        if matches[best_match_index]:
                            recognized_face_name = face_names[best_match_index]
                            print(f"**Face matched: {recognized_face_name}**")
                            break
                    else:
                        print("**Face not recognized.**")
            else:
                print("**No face detected.**")
            break  # Exit loop after recognition attempt
        elif cv2.waitKey(1) & 0xFF == ord('q'):  # Press q to quit
            print("Quitting")
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    if recognized_face_name:
        # 3. Extract Features (ResNet-50)
        face_image_path = os.path.join(known_face_dir, f"{recognized_face_name}.jpg")
        features = extract_features_resnet50(face_image_path)
        if features is not None:
            print("Features extracted from face image.")
            #  Show feature plot (similar to your paper)
            import matplotlib.pyplot as plt
            plt.plot(features, marker='.', linestyle='')
            plt.title("Matched Database Features")
            plt.xlabel("Feature Index")
            plt.ylabel("Feature Value")
            # plt.show()

            # 4. Generate OTP
            otp = generate_otp()
            print(f"Generated OTP: {otp}")

            # 5. Encrypt OTP
            encrypted_otp = encrypt(otp)
            print(f"Encrypted OTP: {encrypted_otp}")

            # 6. Decrypt OTP (Simulate system's decryption)
            decrypted_otp = decrypt(encrypted_otp)
            print(f"Decrypted OTP: {decrypted_otp}")

            # 7. User Enters OTP (Simulated)
            entered_otp = input("Enter the OTP displayed: ")
            if entered_otp == decrypted_otp:
                print("**OTP verified.**")

                #  Simulate PIN entry
                pin = input("Enter your 4-digit PIN: ")  # In a real system, securely handle PIN
                if len(pin) == 4 and pin.isdigit():
                    print("**PIN verified successfully.**")
                    print("**Transaction successful.**")
                else:
                    print("**Invalid PIN.** Transaction failed.")
            else:
                print("**OTP verification failed.** Transaction cancelled.")
        else:
            print("Feature extraction failed. Transaction cancelled.")
    else:
        print("Face recognition failed. Transaction cancelled.")


def check_face_match():
    print("Starting Cardless Transaction Simulation")
    # 1. User Initiates Transaction (Simulated)
    print("Simulating user initiating transaction at ATM")
    # 2. Face Recognition
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    recognized_face_name = None
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        faces = face_cascade.detectMultiScale(frame, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)  # Draw rectangle around face

        cv2.imshow('Face Recognition Press F Key', frame)

        if cv2.waitKey(1) & 0xFF == ord('f'):  # Press 'f' to 'freeze' and recognize
            face_locations = face_recognition.face_locations(frame)
            if face_locations:
                face_encodings_current_frame = face_recognition.face_encodings(frame, face_locations)

                for face_encoding in face_encodings_current_frame:
                    matches = face_recognition.compare_faces(face_encodings, face_encoding)
                    if matches:
                        best_match_index = np.argmin(
                            [np.linalg.norm(face_encodings[i] - face_encoding) for i in range(len(face_encodings))])
                        if matches[best_match_index]:
                            recognized_face_name = face_names[best_match_index]
                            print(f"**Face matched: {recognized_face_name}**")
                            return "success"
                            break
                    else:
                        return "failed"  # "**Face not recognized.**"
            else:
                return "failed"  # "**No face detected.**"
            break  # Exit loop after recognition attempt
        elif cv2.waitKey(1) & 0xFF == ord('q'):  # Press q to quit
            print("Quitting")
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    if recognized_face_name:
        # 3. Extract Features (ResNet-50)
        face_image_path = os.path.join(known_face_dir, f"{recognized_face_name}.jpg")
        features = extract_features_resnet50(face_image_path)
        if features is not None:
            print("Features extracted from face image.")
            #  Show feature plot (similar to your paper)
            import matplotlib.pyplot as plt
            plt.plot(features, marker='.', linestyle='')
            plt.title("Matched Database Features")
            plt.xlabel("Feature Index")
            plt.ylabel("Feature Value")
            # plt.show()

        else:
            return "failed"  # "Feature extraction failed. Transaction cancelled."
    else:
        return "failed"  # "Face recognition failed. Transaction cancelled."
# if __name__ == "__main__":
#     #  Optional: Capture and store a new face for testing
#     #  Only run this once to add a face to your 'known_faces' folder
#     if capture_and_store_face("user1"):  # Change "user1" to the desired name
#         print("Face captured. Running transaction simulation...")
#     #    main()
#     #else:
#     #    print("Face capture cancelled.")
#     main()
