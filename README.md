# 📍 Liveness Check & Presence System

This project is a Django REST Framework (DRF)-based API system designed for **face-based liveness detection** and **location-based presence check**.

It allows users to:

- Register/train a face using an image.
- Use a WebSocket connection for liveness detection.
- Perform location-based presence check to ensure the user is within an allowed geofence radius (e.g., 20 meters).

---

## ✅ Features

- 🔐 Face registration using a simple API call with image upload
- 📡 Real-time **WebSocket** for liveness detection
- 📍 Geolocation validation using latitude and longitude
- ⚠️ Distance check (within 20 meters radius)
- 💬 Clear API responses for success and failure

---

## 🛠️ Tech Stack

- Django REST Framework
- WebSocket (Channels / Django-Channels or FastAPI-compatible)
- Geopy (for distance calculation)
- OpenCV / Dlib / Custom ML (for face recognition and liveness)
- Frontend optional: React / Vue for integration

---

## 🚀 How to Operate Liveness Check for Presence

### 1. 🧠 Train/Register the Face

Send a face image to the API to register and associate it with the user.

```bash
curl --request POST \
  --url http://0.0.0.0:8008/api/face/train/ \
  --header 'Authorization: Bearer $TOKEN' \
  --header 'Content-Type: multipart/form-data' \
  --form image=@IMG_6885.jpg
```

- Replace `IMG_6885.jpg` with the image file of the user's face.
- `$TOKEN` is your JWT or DRF token for authenticated API access.

---

### 2. 👁️ Start Liveness Detection (WebSocket)

Connect to the WebSocket endpoint using your preferred WebSocket client (e.g., browser, Postman, Python script, JS frontend).

```bash
ws://localhost:8080/ws/liveness/?user_id=$USER_ID
```

- Replace `$USER_ID` with the actual `User` ID from the Django `auth.User` model.
- The WebSocket server will handle real-time liveness checks (e.g., eye blink detection or head movement).

---

### 3. 📍 Perform Presence Check (Location)

Send your current GPS coordinates (latitude and longitude) to the presence-check API.

```bash
curl --request POST \
  --url http://0.0.0.0:8008/api/presence/presence-check/ \
  --header 'Authorization: Bearer $TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "lat": -7.9674532,
    "lon": 112.627025
}'
```

- This checks if your coordinates are within **20 meters** of the allowed location (`-7.9673435`, `112.6267206`).

#### 📥 Success Response

```json
{
  "detail": "Success. You are within the allowed area."
}
```

#### 🚫 Error Response (Outside 20m Radius)

```json
{
  "detail": "You are out of area"
}
```

---

## 📌 Sample Allowed Location

```json
{
  "lat": -7.9673435,
  "lon": 112.6267206
}
```

---

## 🧪 Testing Locally

You can test the WebSocket using browser tools or libraries such as:

- JavaScript:
  ```js
  const ws = new WebSocket("ws://localhost:8080/ws/liveness/?user_id=1");
  ws.onmessage = (e) => console.log(e.data);
  ```
