import cv2
import mediapipe as mp
import numpy as np

class VisionTracker:
    def __init__(self, max_hands=2, detection_confidence=0.8, tracking_confidence=0.8):
        self.mp_hands = mp.solutions.hands
        
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
            model_complexity=1
        )
        
    def process(self, frame):
        frame.flags.writeable = False
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = self.hands.process(image)
        
        frame.flags.writeable = True
        
        hands_data = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                hands_data.append({
                    "landmarks": hand_landmarks,
                    "label": label
                })
        
        return hands_data

    def close(self):
        self.hands.close()
