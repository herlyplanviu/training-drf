from operator import attrgetter
import cv2
import mediapipe as mp

# Initialize MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Constants for tweaking program
FRAMES_TO_ANALYZE = 10
NODDING_SENSITIVITY = 0.0125
SHAKING_SENSITIVITY = 0.02

VERTICAL_ADJUSTMENT = 0.2
HORIZONTAL_ADJUSTMENT = 0.12

# Lists to store frame data
nodding_coordinates = []
shaking_coordinates = []
nod_count = 0

def direction_changes(data, coord, sensitivity):
    """Detects the number of significant direction changes."""
    if len(data) < 2:
        return 0

    peak_or_valley = getattr(data[0], coord)
    num_direction_changes = 0
    prev_direction = None

    for i in range(1, len(data)):
        current_data = getattr(data[i], coord)
        if abs(peak_or_valley - current_data) > sensitivity:
            current_direction = 'increasing' if peak_or_valley < current_data else 'decreasing'

            if prev_direction and current_direction != prev_direction:
                num_direction_changes += 1
                peak_or_valley = current_data
            elif not prev_direction:
                prev_direction = current_direction
                peak_or_valley = current_data

    return num_direction_changes

def detect_nodding(frame):
    """Process the frame to detect nodding and shaking."""
    global nodding_coordinates, shaking_coordinates, nod_count
    verification_text = ""

    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # Draw Face Mesh
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )

                # Select landmark points
                chin = face_landmarks.landmark[199]
                sidehead = face_landmarks.landmark[447]
                tophead = face_landmarks.landmark[10]
                bottomhead = face_landmarks.landmark[152]

                # Calculate distance adjustment
                distance_adjustment = (bottomhead.y - tophead.y) / 0.5

                # Store coordinates
                nodding_coordinates.append(chin)
                shaking_coordinates.append(sidehead)

                # Limit stored frames
                if len(nodding_coordinates) > FRAMES_TO_ANALYZE:
                    nodding_coordinates.pop(0)
                if len(shaking_coordinates) > FRAMES_TO_ANALYZE:
                    shaking_coordinates.pop(0)

                # Detect nodding (YES)
                if (direction_changes(nodding_coordinates, "z", NODDING_SENSITIVITY * distance_adjustment) > 0
                        and direction_changes(shaking_coordinates, "z", SHAKING_SENSITIVITY * distance_adjustment) == 0
                        and abs(max(nodding_coordinates, key=attrgetter('y')).y - min(nodding_coordinates, key=attrgetter('y')).y)
                        <= VERTICAL_ADJUSTMENT * distance_adjustment):
                    print("YES")
                    nod_count += 1
                    nodding_coordinates.clear()
                    shaking_coordinates.clear()

                    # Verify after 3 nods
                    if nod_count >= 3:
                        nod_count = 0
                        verification_text = "Verification Success"

                # Detect shaking (NO)
                elif (direction_changes(shaking_coordinates, "z", SHAKING_SENSITIVITY * distance_adjustment) > 0
                      and direction_changes(nodding_coordinates, "z", NODDING_SENSITIVITY * distance_adjustment) == 0
                      and abs(max(shaking_coordinates, key=attrgetter('x')).x - min(shaking_coordinates, key=attrgetter('x')).x)
                      <= HORIZONTAL_ADJUSTMENT * distance_adjustment):
                    print("NO")
                    nodding_coordinates.clear()
                    shaking_coordinates.clear()

                # Display verification message
                if verification_text:
                    cv2.putText(frame, verification_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return frame
