import cv2
import mediapipe as mp
import math

class PoseEstimationClass:
    # MARK: pose estimation code.
    @staticmethod
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

    @staticmethod
    def process_face_pose(image):
        if image is None:
            return "no image found"

        mp_face_mesh = mp.solutions.face_mesh # type: ignore
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
            pose = PoseEstimationClass.estimate_face_pose(nose_norm, left_cheek_norm, right_cheek_norm)
            
            return pose

    @staticmethod
    def count_face_mediapipe(image):
        mp_face_mesh = mp.solutions.face_mesh # type: ignore
        
        with mp_face_mesh.FaceMesh(
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            if not results.multi_face_landmarks:
                return image, None
            
            print(f'total face count: {len(results.multi_face_landmarks)}')


image = cv2.imread('/Users/mc/Exam Proctoring/FYP-II/ML/Data Set/Front/IMG_7164.JPG')
PoseEstimationClass.count_face_mediapipe(image)