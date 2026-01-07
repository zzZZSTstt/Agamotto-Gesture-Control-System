import cv2
import time
import numpy as np
import mediapipe as mp
from src.vision import VisionTracker
from src.controller import MouseController
from src.ui import HUD
from src.camera import CameraSelector, ThreadedCamera

def main():
    selector = CameraSelector()
    cam_idx = selector.select_camera()
    
    if cam_idx is None:
        print("Selection cancelled.")
        return

    cap = ThreadedCamera(cam_idx, width=640, height=480).start()
    
    tracker = VisionTracker()
    mouse = MouseController()
    hud = HUD()
    
    prev_time = 0

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: 
                time.sleep(0.001)
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            hands_data = tracker.process(frame)
            
            controller_data = mouse.process(hands_data)
            
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time) if prev_time > 0 else 0
            prev_time = curr_time
            
            system_info = controller_data.get("system", {})
            is_active = system_info.get("is_active", False)
            
            if hands_data:
                for hand in hands_data:
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, 
                        hand["landmarks"], 
                        mp.solutions.hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                        mp.solutions.drawing_styles.get_default_hand_connections_style()
                    )
            
            if not is_active:
                hud.draw_standby(frame, system_info)
            else:
                if controller_data.get("mode") == "calibration":
                    hud.draw_calibration(frame, controller_data)
                else:
                    hud.draw_running(frame, controller_data, fps)
                    hud.draw_system_overlay(frame, system_info) 

            cv2.imshow('Agamotto Gesture Control System', frame)
            
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
