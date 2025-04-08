import cv2
import tensorflow as tf
import numpy as np
import imutils
import pickle
import os

model_path = './api/modules/liveness.h5'
le_path = './api/modules/label_encoder.pickle'
encodings = './api/modules/encoded_faces.pickle'
detector_folder = './api/modules/face_detector'
confidence_threshold = 0.5

# Load the encoded faces and names
print('[INFO] loading encodings...')
with open(encodings, 'rb') as file:
    encoded_data = pickle.loads(file.read())

# Load serialized face detector
print('[INFO] loading face detector...')
proto_path = os.path.sep.join([detector_folder, 'deploy.prototxt'])
md = os.path.sep.join([detector_folder, 'res10_300x300_ssd_iter_140000.caffemodel'])
detector_net = cv2.dnn.readNetFromCaffe(proto_path, md)

# Load liveness detection model and label encoder
print('[INFO] loading liveness model...')
liveness_model = tf.keras.models.load_model(model_path)
# liveness_model = tf.keras.layers.TFSMLayer(
#     './api/modules/liveness.model',
#     call_endpoint='serving_default'  # or change if different
# )
le = pickle.loads(open(le_path, 'rb').read())

# Start video stream
print('[INFO] starting video stream...')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = imutils.resize(frame, width=800)
    (h, w) = frame.shape[:2]

    # Convert to blob and detect faces
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    detector_net.setInput(blob)
    detections = detector_net.forward()

    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > confidence_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Expand bounding box
            startX = max(0, startX - 20)
            startY = max(0, startY - 20)
            endX = min(w, endX + 20)
            endY = min(h, endY + 20)

            face = frame[startY:endY, startX:endX]

            try:
                face = cv2.resize(face, (32, 32))
            except:
                continue

            face = face.astype("float") / 255.0
            face = tf.keras.preprocessing.image.img_to_array(face)
            face = np.expand_dims(face, axis=0)

            preds = liveness_model.predict(face)[0]
            j = np.argmax(preds)
            label_name = le.classes_[j]
            label = f'{label_name}: {preds[j]:.4f}'

            color = (0, 255, 0) if label_name == 'real' else (0, 0, 255)
            name = "Unknown"

            # Draw on frame
            cv2.putText(frame, name, (startX, startY - 35),
                        cv2.FONT_HERSHEY_COMPLEX, 0.7, (0, 130, 255), 2)
            cv2.putText(frame, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_COMPLEX, 0.7, color, 2)
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 4)

    cv2.imshow("Liveness Detection", frame)
    
    # Press `q` to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()