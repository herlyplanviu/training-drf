from operator import attrgetter
import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
cap = cv2.VideoCapture(0)
frame = 0

# --- NEWLY ADDED CODE START --- #

# Constants for tweaking program.
FRAMES_TO_ANALYZE = 10
NODDING_SENSITIVITY = 0.0125
SHAKING_SENSITIVITY = 0.02

VERTICAL_ADJUSTMENT = 0.2
HORIZONTAL_ADJUSTMENT = 0.12

# Lists to store frame data.
nodding_coordinates = []
shaking_coordinates = []

# Counter for nods
nod_count = 0

"""
Returns the number of times data[coord] changes directions (increasing,
decreasing) when read sequentially. The parameter 'sensitivity'
prevents insignificantly small changes in direction from counting.
"""
def direction_changes(data, coord, sensitivity):
    current_data = None
    prev_data = None
    current_direction = None
    prev_direction = None
    peak_or_valley = getattr(data[0], coord)
    num_direction_changes = 0

    # Traverse the entire list of data.
    for i in range(len(data)):
        current_data = getattr(data[i], coord)
        if prev_data:
            # If the two neighboring data points are significantly far away...
            if abs(peak_or_valley - current_data) > sensitivity:
                # Determine the direction of travel (variables won't be equivalent).
                if peak_or_valley > current_data:
                    current_direction = 'increasing'
                else:
                    current_direction = 'decreasing'

                # Determine if there has been a directional change.
                if prev_direction and current_direction != prev_direction:
                    # Assign a new peak or valley as the current data point.
                    num_direction_changes += 1
                    peak_or_valley = current_data

                # For the first time a direction is established.
                elif not prev_direction:
                    prev_direction = current_direction
                    peak_or_valley = current_data

        prev_data = current_data

    # Return the total number of significant directional changes.
    return num_direction_changes

# --- NEWLY ADDED CODE END --- #

with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_tesselation_style())
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_contours_style())
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_iris_connections_style())

                # --- NEWLY ADDED CODE START --- #

                chin = face_landmarks.landmark[199]
                sidehead = face_landmarks.landmark[447]

                tophead = face_landmarks.landmark[10]
                bottomhead = face_landmarks.landmark[152]
                distance_adjustment = (bottomhead.y - tophead.y) / 0.5

                nodding_coordinates.append(chin)
                shaking_coordinates.append(sidehead)

                if (len(nodding_coordinates) > FRAMES_TO_ANALYZE and len(shaking_coordinates) > FRAMES_TO_ANALYZE):
                    nodding_coordinates.pop(0)
                    shaking_coordinates.pop(0)

                    if (direction_changes(nodding_coordinates, "z", NODDING_SENSITIVITY * distance_adjustment) > 0
                            and direction_changes(shaking_coordinates, "z", SHAKING_SENSITIVITY * distance_adjustment) == 0
                            and abs(max(nodding_coordinates, key=attrgetter('y')).y - min(nodding_coordinates, key=attrgetter('y')).y)
                            <= VERTICAL_ADJUSTMENT * distance_adjustment):
                        print("YES")
                        nod_count += 1  # Increment nod count
                        nodding_coordinates = []
                        shaking_coordinates = []

                        # Check if nod count reaches 3
                        if nod_count >= 3:
                            nod_count = 0  # Reset nod count
                            verification_text = "Verification Success"  # Set verification message

                    elif (direction_changes(shaking_coordinates, "z", SHAKING_SENSITIVITY * distance_adjustment) > 0
                          and direction_changes(nodding_coordinates, "z", NODDING_SENSITIVITY * distance_adjustment) == 0
                          and abs(max(shaking_coordinates, key=attrgetter('x')).x - min(shaking_coordinates, key=attrgetter('x')).x)
                          <= HORIZONTAL_ADJUSTMENT * distance_adjustment):
                        print("NO")
                        nodding_coordinates = []
                        shaking_coordinates = []

                # --- NEWLY ADDED CODE END --- #

                # Display verification message if set
                if 'verification_text' in locals():
                    cv2.putText(image, verification_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('MediaPipe Face Mesh', image)
        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()