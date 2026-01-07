import cv2
import mediapipe as mp
import time

class HandDetector:
    def __init__(self, mode=False, max_hands=2, detection_con=0.5, track_con=0.5):
        self.mode = mode
        self.max_hands = max_hands
        self.detection_con = detection_con
        self.track_con = track_con

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.detection_con,
            min_tracking_confidence=self.track_con
        )
        self.mp_draw = mp.solutions.drawing_utils

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

        if self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        return img

    def get_hand_type(self, hand_no=0):
        if self.results.multi_handedness:
            if hand_no < len(self.results.multi_handedness):
                return self.results.multi_handedness[hand_no].classification[0].label
        return None

    def find_position(self, img, hand_no=0, draw=True):
        lm_list = []
        if self.results.multi_hand_landmarks:
            if hand_no < len(self.results.multi_hand_landmarks):
                my_hand = self.results.multi_hand_landmarks[hand_no]
                for id, lm in enumerate(my_hand.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)
        return lm_list

    def get_gesture(self, lm_list, hand_type="Right"):
        if not lm_list:
            return None

        tip_ids = [4, 8, 12, 16, 20]
        fingers = []

        thumb_tip_x = lm_list[tip_ids[0]][1]
        thumb_ip_x = lm_list[tip_ids[0] - 1][1] 
        index_root_x = lm_list[5][1]
        pinky_root_x = lm_list[17][1]

        if index_root_x < pinky_root_x:
            if thumb_tip_x < thumb_ip_x:
                fingers.append(1)
            else:
                fingers.append(0)
        else:
            if thumb_tip_x > thumb_ip_x:
                fingers.append(1)
            else:
                fingers.append(0)

        for id in range(1, 5):
            if lm_list[tip_ids[id]][2] < lm_list[tip_ids[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        total_fingers = fingers.count(1)
        
        if total_fingers == 0:
            return "Fist (0)"
        elif total_fingers == 5:
            return "Open Hand (5)"
        else:
            return f"{total_fingers} Fingers"

def main():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    detector = HandDetector()
    p_time = 0

    print("Starting Hand Tracking... Press 'q' to exit.")

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to read frame.")
            break
        
        img = cv2.flip(img, 1)

        img = detector.find_hands(img)
        
        if detector.results.multi_hand_landmarks:
            for hand_no in range(len(detector.results.multi_hand_landmarks)):
                lm_list = detector.find_position(img, hand_no=hand_no, draw=True)
                hand_type = detector.get_hand_type(hand_no)
                
                gesture = detector.get_gesture(lm_list, hand_type)
                
                x_coords = [lm[1] for lm in lm_list]
                y_coords = [lm[2] for lm in lm_list]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                cv2.putText(img, f'{hand_type}: {gesture}', (x_min, y_min - 20), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)
                cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

                key_points = {
                    "Wrist": lm_list[0],
                    "Thumb": lm_list[4],
                    "Index": lm_list[8],
                    "Middle": lm_list[12],
                    "Ring": lm_list[16],
                    "Pinky": lm_list[20]
                }
                
                coords_str = ", ".join([f"{k}:({v[1]},{v[2]})" for k, v in key_points.items()])
                print(f"Hand: {hand_type}, Gesture: {gesture} | {coords_str}")

        c_time = time.time()
        fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
        p_time = c_time

        cv2.putText(img, f'FPS: {int(fps)}', (10, 40), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

        cv2.imshow("Image", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
