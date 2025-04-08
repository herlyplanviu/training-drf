import cv2
import tensorflow as tf
import numpy as np
import imutils
import pickle
import os

model_path = './liveness/modules/liveness.h5'
le_path = './liveness/modules/label_encoder.pickle'
encodings = './liveness/modules/encoded_faces.pickle'
detector_folder = './liveness/modules/face_detector'
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

def detect_spoofing(frame):
    frm = imutils.resize(frame, width=800)
    (h, w) = frm.shape[:2]

    blob = cv2.dnn.blobFromImage(cv2.resize(frm, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    detector_net.setInput(blob)
    detections = detector_net.forward()

    if detections.shape[2] == 0:
        return None  # No face detected

    # Get the first detection only (index 0)
    confidence = detections[0, 0, 0, 2]

    if confidence < 0.5:
        return None  # Detected face is not confident enough

    box = detections[0, 0, 0, 3:7] * np.array([w, h, w, h])
    (startX, startY, endX, endY) = box.astype('int')

    # Expand box slightly
    startX = max(0, startX - 20)
    startY = max(0, startY - 20)
    endX = min(w, endX + 20)
    endY = min(h, endY + 20)

    face = frm[startY:endY, startX:endX]

    try:
        face = cv2.resize(face, (32, 32))
    except:
        return None  # If resize fails

    face = face.astype("float") / 255.0
    face = tf.keras.preprocessing.image.img_to_array(face)
    face = np.expand_dims(face, axis=0)

    preds = liveness_model.predict(face)[0]
    j = np.argmax(preds)
    label_name = le.classes_[j]
    label = f'{label_name}: {preds[j]:.4f}'

    print(f"[INFO] Detected: {label}")

    return {
        "label": label,
        "label_name": label_name,
        "confidence": preds[j],
        "box": (startX, startY, endX, endY)
    }

