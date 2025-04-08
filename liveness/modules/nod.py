# Landmark indices
CHIN, SIDEHEAD, TOPHEAD, BOTTOMHEAD = 199, 447, 10, 152

# Constants for nod detection
FRAMES_TO_ANALYZE = 10
NODDING_SENSITIVITY = 0.0125
SHAKING_SENSITIVITY = 0.02
VERTICAL_ADJUSTMENT = 0.2
HORIZONTAL_ADJUSTMENT = 0.12

# Store nodding frames
nodding_coordinates = []
shaking_coordinates = []
nod_count = 0


def direction_changes(data, coord_index, sensitivity):
    """Detects the number of significant direction changes in NumPy landmarks."""
    if len(data) < 2:
        return 0

    peak_or_valley = data[0][coord_index]
    num_direction_changes = 0
    prev_direction = None

    for i in range(1, len(data)):
        current_data = data[i][coord_index]
        if abs(peak_or_valley - current_data) > sensitivity:
            current_direction = 'increasing' if peak_or_valley < current_data else 'decreasing'

            if prev_direction and current_direction != prev_direction:
                num_direction_changes += 1
                peak_or_valley = current_data
            elif not prev_direction:
                prev_direction = current_direction
                peak_or_valley = current_data

    return num_direction_changes


def detect_nod(landmarks):
    """Detect head nodding (YES) movement."""
    global nodding_coordinates, shaking_coordinates, nod_count

    chin = landmarks[CHIN]
    sidehead = landmarks[SIDEHEAD]
    tophead = landmarks[TOPHEAD]
    bottomhead = landmarks[BOTTOMHEAD]

    # Calculate distance adjustment
    distance_adjustment = (bottomhead[1] - tophead[1]) / 0.5

    # Store coordinates
    nodding_coordinates.append(chin)
    shaking_coordinates.append(sidehead)

    # Limit stored frames
    if len(nodding_coordinates) > FRAMES_TO_ANALYZE:
        nodding_coordinates.pop(0)
    if len(shaking_coordinates) > FRAMES_TO_ANALYZE:
        shaking_coordinates.pop(0)

    # Detect nodding (YES)
    if (direction_changes(nodding_coordinates, 2, NODDING_SENSITIVITY * distance_adjustment) > 0
            and direction_changes(shaking_coordinates, 2, SHAKING_SENSITIVITY * distance_adjustment) == 0
            and abs(max(nodding_coordinates, key=lambda lm: lm[1])[1] - min(nodding_coordinates, key=lambda lm: lm[1])[1])
            <= VERTICAL_ADJUSTMENT * distance_adjustment):

        nod_count += 1
        nodding_coordinates.clear()
        shaking_coordinates.clear()

        # Verify after 3 nods
        if nod_count >= 3:
            nod_count = 0
            return True

    return False