# import cv2
# import mediapipe as mp
# import os
# import csv
# import math
from pathlib import Path       
DIR = Path(__file__).resolve().parent

# MARK: Complete code with pose detection.
import cv2
import mediapipe as mp
import math

mp_face_mesh = mp.solutions.face_mesh

def process_face(image):
    h, w, _ = image.shape

    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True
    ) as face_mesh:

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return image, None

        lm = results.multi_face_landmarks[0].landmark

        # Landmark indices
        NOSE = 1
        LEFT_CHEEK = 234
        RIGHT_CHEEK = 454
        CHIN = 152

        def pt(i):
            return (
                int(lm[i].x * w),
                int(lm[i].y * h)
            )

        nose = pt(NOSE)
        left_cheek = pt(LEFT_CHEEK)
        right_cheek = pt(RIGHT_CHEEK)
        chin = pt(CHIN)

        # ---------- FACE WIDTH ----------
        face_width = abs(right_cheek[0] - left_cheek[0])
        if face_width == 0:
            return image, None

        # ---------- PIVOT ----------
        pivot_x = (left_cheek[0] + right_cheek[0]) // 2
        pivot_y = chin[1]

        # ---------- NORMALIZATION ----------
        nose_norm = (
            (nose[0] - pivot_x) / face_width,
            (nose[1] - pivot_y) / face_width
        )

        left_cheek_norm = (
            (left_cheek[0] - pivot_x) / face_width,
            (left_cheek[1] - pivot_y) / face_width
        )

        right_cheek_norm = (
            (right_cheek[0] - pivot_x) / face_width,
            (right_cheek[1] - pivot_y) / face_width
        )

        chin_norm = (
            (chin[0] - pivot_x) / face_width,
            (chin[1] - pivot_y) / face_width
        )

        # ---------- HEAD TURN ANGLE ----------
        dx = nose[0] - pivot_x
        dy = pivot_y - nose[1]

        angle = math.degrees(math.atan2(dx, dy))
        # angle > 0  → looking right
        # angle < 0  → looking left

        # ---------- DRAWING ----------
        # cv2.circle(image, nose, 5, (0, 0, 255), -1)
        # cv2.circle(image, left_cheek, 5, (255, 0, 0), -1)
        # cv2.circle(image, right_cheek, 5, (255, 0, 0), -1)
        # cv2.circle(image, chin, 5, (0, 255, 0), -1)

        # cv2.line(image, (pivot_x, 0), (pivot_x, h), (255, 255, 0), 2)
        normalized_data = {
            "nose": nose_norm,
            "left_cheek": left_cheek_norm,
            "right_cheek": right_cheek_norm,
            "chin": chin_norm,
            "angle": angle
        }
        pose = estimate_face_pose(nose_norm, left_cheek_norm, right_cheek_norm)

        normalized_data = {
            "nose": nose_norm,
            "left_cheek": left_cheek_norm,
            "right_cheek": right_cheek_norm,
            "chin": chin_norm,
            "angle": angle,
            "pose": pose
        }

        return image, normalized_data

# MARK: pose estimation code.
def estimate_face_pose(nose_norm, left_cheek_norm, right_cheek_norm):
    nx, ny = nose_norm
    lcx, lcy = left_cheek_norm
    rcx, rcy = right_cheek_norm

    # Horizontal thresholds
    HORIZONTAL_THRESHOLD = 0.08

    # Vertical thresholds
    UP_THRESHOLD = -0.12    # nose above cheeks for looking UP
    DOWN_THRESHOLD = 0.12   # nose below cheeks for looking DOWN

    # Average Y of cheeks
    avg_cheek_y = (lcy + rcy) / 2

    # ---------- Check UP ----------
    if ny < avg_cheek_y and ny < UP_THRESHOLD:
        return "UP"

    # ---------- Check DOWN ----------
    if ny > avg_cheek_y and ny > DOWN_THRESHOLD:
        return "DOWN"

    # ---------- Check LEFT / RIGHT ----------
    if nx < -HORIZONTAL_THRESHOLD:
        return "LEFT"
    if nx > HORIZONTAL_THRESHOLD:
        return "RIGHT"

    # Default
    return "STRAIGHT"


img_path = str(DIR.parent/ "test_images/5 images/11.jpg")
print(img_path)
img = cv2.imread(img_path)
out_img, data = process_face(img)
cv2.putText(
    out_img,
    f"Pose: {data['pose']}",
    (30, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    1,
    (0, 255, 0),
    2
)

cv2.imshow("Result", out_img)
cv2.waitKey(0)
cv2.destroyAllWindows()

# MARK: ChatGPT code with some variations by me.
# import cv2
# import mediapipe as mp
# import math
# mp_face_mesh = mp.solutions.face_mesh


# def get_distance(p1, p2):
#     return math.sqrt(
#         (p1[0] - p2[0]) ** 2 +
#         (p1[1] - p2[1]) ** 2 +
#         (p1[2] - p2[2]) ** 2
#     )
# def draw_face_landmarks_and_pivot(image):
#     if image is None:
#         print("no image found")
#         return

#     h, w, _ = image.shape

#     with mp_face_mesh.FaceMesh(
#         static_image_mode=True,
#         max_num_faces=1,
#         refine_landmarks=True
#     ) as face_mesh:

#         rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#         results = face_mesh.process(rgb)

#         if not results.multi_face_landmarks:
#             return image

#         landmarks = results.multi_face_landmarks[0].landmark

        
#         # Landmark indices
#         NOSE = 1
#         LEFT_CHEEK = 234
#         RIGHT_CHEEK = 454
#         CHIN = 152

#         nose = [landmarks[NOSE].x, landmarks[NOSE].y, landmarks[NOSE].z]
#         left_cheek = [landmarks[LEFT_CHEEK].x, landmarks[LEFT_CHEEK].y, landmarks[LEFT_CHEEK].z]
#         right_cheek = [landmarks[RIGHT_CHEEK].x, landmarks[RIGHT_CHEEK].y, landmarks[RIGHT_CHEEK].z]
#         chin = [landmarks[CHIN].x, landmarks[CHIN].y, landmarks[CHIN].z]

#         face_width = get_distance(left_cheek, right_cheek)

#         print("Points Before normalization.")

#         print(f"Nose = {nose}")
#         print(f"left cheek = {left_cheek}")
#         print(f"right cheek = {right_cheek}")
#         print(f"chin = {chin}")


#         if face_width == 0:
#             return

#         nose = [x / face_width for x in nose]
#         left_cheek = [x / face_width for x in left_cheek]
#         right_cheek = [x / face_width for x in right_cheek]
#         chin = [x / face_width for x in chin]

#         print("Points after normalization.")
#         print(f"Nose = {nose}")
#         print(f"left cheek = {left_cheek}")
#         print(f"right cheek = {right_cheek}")
#         print(f"chin = {chin}")

#         # Draw points
#         # cv2.circle(image, nose, 5, (0, 0, 255), -1)
#         # cv2.circle(image, left_cheek, 5, (255, 0, 0), -1)
#         # cv2.circle(image, right_cheek, 5, (255, 0, 0), -1)
#         # cv2.circle(image, chin, 5, (0, 255, 0), -1)

#         # Pivot center between cheeks
#         pivot_x = (left_cheek[0] + right_cheek[0]) // 2

#         # Draw pivot vertical line
#         # cv2.line(
#         #     image,
#         #     (pivot_x, 0),
#         #     (pivot_x, h),
#         #     (255, 255, 0),
#         #     2
#         # )

#         return image

# DATASET_PATH = str(DIR.parent/ "test_images/5 images/4.png")
# img = cv2.imread(DATASET_PATH)
# output = draw_face_landmarks_and_pivot(img)

# cv2.imshow("Face Landmarks + Pivot", output)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
