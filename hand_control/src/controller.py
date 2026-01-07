import pyautogui
import numpy as np
import time
import math
from .filter import OneEuroFilter
from .sound import SoundManager

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

class MouseController:
    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.filter_x = OneEuroFilter(min_cutoff=0.01, beta=0.05)
        self.filter_y = OneEuroFilter(min_cutoff=0.01, beta=0.05)
        
        self.last_left_click_time = 0
        self.last_right_click_time = 0
        self.is_dragging = False
        self.current_gesture = "move"
        self.last_gesture = "move"
        self.gesture_consecutive_frames = 0
        self.GESTURE_CONFIRM_FRAMES = 3
        
        self.gesture_lock_pos = None 
        self.deadzone_radius = 30 
        self.static_movement_deadzone = 4
        self.last_cursor_pos = None
        
        self.is_active = False 
        self.activation_start_time = 0
        self.deactivation_start_time = 0
        self.ACTIVATION_DURATION = 1.5
        
        self.is_calibrated = False
        self.calibration_step = 0
        self.calibration_points = [] 
        self.calibration_add_hold_start = 0
        self.calibration_delete_hold_start = 0
        self.calibration_hold_duration = 0.45
        self.calibration_cooldown_until = 0
        self.calibration_point_cooldown = 2.0
        
        self.last_fist_click_time = 0
        self.fist_click_min_interval = 1.0
        self.is_four_fingers_active = False

        self.last_middle_click_time = 0
        self.middle_click_min_interval = 1.0
        self.is_middle_click_active = False
        
        self.scroll_anchor_y = None
        self.scroll_speed_factor = 0.5
        
        self.roi = {"x1": 0.2, "y1": 0.2, "x2": 0.8, "y2": 0.8}
        
        self.pinch_trigger = 0.28 
        self.right_pinch_trigger = 0.20 
        self.left_pinch_release = 0.34
        self.right_pinch_release = 0.30
        self.overdrive_factor = 1.3
        self.right_click_min_interval = 0.25
        self.left_click_min_interval = 0.03
        self.tap_max_duration = 0.6
        
        self.last_dist_index = 0
        self.last_dist_middle = 0
        
        self.left_pinch_start_time = 0
        self._left_pinching = False
        self._right_pinching = False
        
        self.unlock_phase = 0
        self.phase1_expire_time = 0
        self.activation_start_time = 0
        self.deactivation_start_time = 0
        self.pinky_pinch_trigger = 0.25
        self.pinky_pinch_release = 0.33
        self._pinky_pinching = False

    def get_stable_hand_pos(self, landmarks):
        indices = [0, 5, 9, 13, 17]
        avg_x = 0
        avg_y = 0
        for i in indices:
            avg_x += landmarks.landmark[i].x
            avg_y += landmarks.landmark[i].y
        
        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        
        return Point(avg_x / len(indices), avg_y / len(indices))

    def get_distance(self, p1, p2):
        x1 = p1.x if hasattr(p1, 'x') else p1[0]
        y1 = p1.y if hasattr(p1, 'y') else p1[1]
        x2 = p2.x if hasattr(p2, 'x') else p2[0]
        y2 = p2.y if hasattr(p2, 'y') else p2[1]
        return math.hypot(x1 - x2, y1 - y2)

    def get_hand_scale(self, landmarks):
        wrist = landmarks.landmark[0]
        middle_mcp = landmarks.landmark[9]
        return self.get_distance(wrist, middle_mcp)

    def get_finger_states(self, landmarks):
        states = []
        
        ref_thumb = self.get_distance(landmarks.landmark[3], landmarks.landmark[2])
        d_thumb = self.get_distance(landmarks.landmark[4], landmarks.landmark[2])
        states.append(d_thumb > ref_thumb * 1.4) 

        finger_indices = [(8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)]
        
        for tip, pip, mcp in finger_indices:
            ref = self.get_distance(landmarks.landmark[pip], landmarks.landmark[mcp])
            d_tip_mcp = self.get_distance(landmarks.landmark[tip], landmarks.landmark[mcp])
            states.append(d_tip_mcp > ref * 1.6) 
            
        return states

    def is_four_fingers_curled(self, landmarks):
        states = self.get_finger_states(landmarks)
        return not any(states[1:])

    def is_middle_click_gesture(self, landmarks):
        states = self.get_finger_states(landmarks)
        return (not states[0]) and states[1] and states[2] and (not states[3]) and (not states[4])

    def is_scroll_gesture(self, landmarks):
        states = self.get_finger_states(landmarks)
        if not all(states[1:]):
             return False

        tips = [8, 12, 16, 20]
        scale = self.get_hand_scale(landmarks) or 1.0
        
        max_spread = 0.35
        
        for i in range(len(tips) - 1):
            p1 = landmarks.landmark[tips[i]]
            p2 = landmarks.landmark[tips[i+1]]
            dist = self.get_distance(p1, p2) / scale
            if dist > max_spread:
                return False
                
        return True 

    def is_palm_open(self, landmarks):
        states = self.get_finger_states(landmarks)
        return all(states)


    def is_ring_pinch(self, landmarks):
        thumb = landmarks.landmark[4]
        ring = landmarks.landmark[16]
        scale = self.get_hand_scale(landmarks) or 1.0
        dist = self.get_distance(thumb, ring) / scale
        return dist < 0.22

    def is_pinky_pinch(self, landmarks):
        thumb = landmarks.landmark[4]
        pinky = landmarks.landmark[20]
        scale = self.get_hand_scale(landmarks) or 1.0
        dist = self.get_distance(thumb, pinky) / scale
        return dist < self.pinky_pinch_trigger

    def is_hands_crossed(self, h1, h2):
        pass

    def update_system_state(self, hands_data):
        if len(hands_data) < 2:
            self.activation_start_time = 0
            self.deactivation_start_time = 0
            self.unlock_phase = 0
            return 0, ""

        left_hand = None
        right_hand = None
        
        for hand in hands_data:
            if hand["label"] == "Left": left_hand = hand["landmarks"]
            if hand["label"] == "Right": right_hand = hand["landmarks"]
            
        if not left_hand or not right_hand:
            left_hand = hands_data[0]["landmarks"]
            right_hand = hands_data[1]["landmarks"]

        now = time.time()
        
        if not self.is_active:
            is_sealing = self.is_ring_pinch(left_hand) or self.is_ring_pinch(right_hand)
            
            if is_sealing:
                self.phase1_expire_time = now + 3.0 
                if self.unlock_phase == 0:
                    SoundManager.play_calibration_tick() 

            is_phase1_valid = now < self.phase1_expire_time
            
            if is_phase1_valid:
                margin = 0.05 
                is_crossed = left_hand.landmark[0].x > (right_hand.landmark[0].x + margin)
                
                if is_crossed:
                    self.unlock_phase = 2
                    if self.activation_start_time == 0: 
                        self.activation_start_time = now
                    
                    elapsed = now - self.activation_start_time
                    progress = min(1.0, elapsed / self.ACTIVATION_DURATION)
                    
                    if elapsed >= self.ACTIVATION_DURATION:
                        self.is_active = True
                        self.activation_start_time = 0
                        self.unlock_phase = 0
                        self.phase1_expire_time = 0
                        SoundManager.play_active() 
                        return 1.0, "EYE OPENED"
                    
                    return progress, "OPENING..."
                else:
                    self.unlock_phase = 1
                    self.activation_start_time = 0 
                    remaining = int(self.phase1_expire_time - now) + 1
                    return 0.0, f"CROSS HANDS ({remaining}s)"
            else:
                self.unlock_phase = 0
                self.activation_start_time = 0
                return 0.0, "PINCH RING"

        if self.is_active and self.is_palm_open(left_hand) and self.is_palm_open(right_hand):
            if self.deactivation_start_time == 0: self.deactivation_start_time = now
            elapsed = now - self.deactivation_start_time
            progress = min(1.0, elapsed / self.ACTIVATION_DURATION)
            if elapsed >= self.ACTIVATION_DURATION:
                self.is_active = False
                self.deactivation_start_time = 0
                SoundManager.play_deactive() 
                return 1.0, "DEACTIVATED"
            return progress, "HOLD TO STOP"
        else:
            self.deactivation_start_time = 0
            
        return 0, ""

    def update_roi_from_calibration(self):
        if len(self.calibration_points) != 4:
            return
        xs = [p[0] for p in self.calibration_points]
        ys = [p[1] for p in self.calibration_points]
        self.roi = {
            "x1": min(xs), "y1": min(ys),
            "x2": max(xs), "y2": max(ys)
        }
        self.is_calibrated = True
        SoundManager.play_calibration_done()
    
    def get_roi_preview(self):
        if len(self.calibration_points) < 2:
            return None
        xs = [p[0] for p in self.calibration_points]
        ys = [p[1] for p in self.calibration_points]
        return {"x1": min(xs), "y1": min(ys), "x2": max(xs), "y2": max(ys)}

    def detect_gesture_priority(self, landmarks):
        thumb = landmarks.landmark[4]
        index = landmarks.landmark[8]
        middle = landmarks.landmark[12]
        scale = self.get_hand_scale(landmarks) or 1.0
        
        self.last_dist_index = self.get_distance(thumb, index) / scale
        self.last_dist_middle = self.get_distance(thumb, middle) / scale
        
        detected_gesture = "move"

        if self._right_pinching:
            if self.last_dist_middle > self.right_pinch_release:
                self._right_pinching = False
            else:
                 detected_gesture = "right_pinch"
        else:
            if self.last_dist_middle < self.right_pinch_trigger:
                self._right_pinching = True
                detected_gesture = "right_pinch"
        
        if detected_gesture == "move":
            if self._left_pinching:
                if self.last_dist_index > self.left_pinch_release:
                    self._left_pinching = False
                else:
                    detected_gesture = "left_pinch"
            else:
                if self.last_dist_index < self.pinch_trigger:
                    self._left_pinching = True
                    detected_gesture = "left_pinch"
        
        if detected_gesture == "move":
            if self.is_middle_click_gesture(landmarks):
                detected_gesture = "middle_click"
        
        if detected_gesture == "move":
            if self.is_scroll_gesture(landmarks):
                detected_gesture = "scroll"

        if detected_gesture == "move":
             if self.is_four_fingers_curled(landmarks):
                 detected_gesture = "fist"

        if detected_gesture == self.last_gesture:
            self.gesture_consecutive_frames += 1
        else:
            self.gesture_consecutive_frames = 0
            self.last_gesture = detected_gesture
            
        if self.gesture_consecutive_frames >= self.GESTURE_CONFIRM_FRAMES:
            return detected_gesture
        else:
            return self.current_gesture

    def map_coordinates(self, hand_pos, now):
        roi_w = self.roi["x2"] - self.roi["x1"]
        roi_h = self.roi["y2"] - self.roi["y1"]
        if roi_w == 0 or roi_h == 0: return 0, 0
        
        norm_x = (hand_pos.x - self.roi["x1"]) / roi_w
        norm_y = (hand_pos.y - self.roi["y1"]) / roi_h
        
        norm_x -= 0.5
        norm_y -= 0.5
        norm_x *= self.overdrive_factor
        norm_y *= self.overdrive_factor
        norm_x += 0.5
        norm_y += 0.5
        
        norm_x = max(0, min(1, norm_x))
        norm_y = max(0, min(1, norm_y))
        
        target_x = norm_x * self.screen_w
        target_y = norm_y * self.screen_h
        
        smooth_x = self.filter_x(target_x, t=now)
        smooth_y = self.filter_y(target_y, t=now)
        
        return smooth_x, smooth_y
    
    def move_cursor(self, x, y):
        xi, yi = int(x), int(y)
        if self.last_cursor_pos is not None:
            lx, ly = self.last_cursor_pos
            if abs(xi - lx) <= self.static_movement_deadzone and abs(yi - ly) <= self.static_movement_deadzone:
                return
        pyautogui.moveTo(xi, yi)
        self.last_cursor_pos = (xi, yi)

    def process_calibration(self, hand_pos, landmarks):
        now = time.time()
        
        thumb = landmarks.landmark[4]
        index = landmarks.landmark[8]
        middle = landmarks.landmark[12]
        scale = self.get_hand_scale(landmarks) or 1.0
        self.last_dist_index = self.get_distance(thumb, index) / scale
        self.last_dist_middle = self.get_distance(thumb, middle) / scale
        
        if self._pinky_pinching:
            if not self.is_pinky_pinch(landmarks) and (self.get_distance(thumb, landmarks.landmark[20]) / scale) > self.pinky_pinch_release:
                self._pinky_pinching = False
        else:
            if self.is_pinky_pinch(landmarks):
                self._pinky_pinching = True
        
        is_fist_now = self.is_four_fingers_curled(landmarks)
        is_open_now = self.is_palm_open(landmarks)
        is_pinky_pinching_now = self._pinky_pinching
        
        self.calibration_step = len(self.calibration_points)
        next_point_num = min(4, self.calibration_step + 1)
        
        msg = f"CALIBRATE POINT {next_point_num}"
        progress = 0.0
        
        if len(self.calibration_points) >= 4:
            self.update_roi_from_calibration()
            return {
                "mode": "calibration",
                "msg": "CALIBRATION COMPLETE",
                "step": 4,
                "progress": 1.0,
                "hand_pos": (hand_pos.x, hand_pos.y),
                "points": list(self.calibration_points),
                "roi_preview": self.get_roi_preview(),
                "debug": {
                    "dist_idx": self.last_dist_index,
                    "dist_mid": self.last_dist_middle,
                    "thresh": self.pinch_trigger,
                    "fingers": self.get_finger_states(landmarks)
                }
            }
        
        in_cooldown = now < self.calibration_cooldown_until
        if in_cooldown:
            remaining = self.calibration_cooldown_until - now
            progress = max(0.0, min(1.0, 1.0 - (remaining / self.calibration_point_cooldown)))
            msg = f"CALIBRATION SUCCESS | PROCEED TO POINT {next_point_num}"
        
        if is_fist_now:
            if self.calibration_delete_hold_start == 0:
                self.calibration_delete_hold_start = now
                SoundManager.play_calibration_tick()
            elapsed = now - self.calibration_delete_hold_start
            progress = min(1.0, elapsed / self.calibration_hold_duration)
            msg = "HOLD FIST TO UNDO"
            if elapsed >= self.calibration_hold_duration:
                if self.calibration_points:
                    self.calibration_points.pop()
                    SoundManager.play_calibration_tick()
                self.calibration_cooldown_until = 0
                self.calibration_delete_hold_start = 0
        elif (not in_cooldown) and is_pinky_pinching_now:
            if self.calibration_add_hold_start == 0:
                self.calibration_add_hold_start = now
                SoundManager.play_calibration_tick()
            elapsed = now - self.calibration_add_hold_start
            progress = min(1.0, elapsed / self.calibration_hold_duration)
            msg = "HOLD PINKY PINCH TO ADD"
            if elapsed >= self.calibration_hold_duration:
                self.calibration_points.append((hand_pos.x, hand_pos.y))
                SoundManager.play_calibration_tick()
                self.calibration_cooldown_until = now + self.calibration_point_cooldown
                self.calibration_add_hold_start = 0
                if len(self.calibration_points) >= 4:
                    self.update_roi_from_calibration()
                    msg = "CALIBRATION COMPLETE"
                else:
                    msg = f"CALIBRATION SUCCESS | PROCEED TO POINT {len(self.calibration_points) + 1}"
        else:
            self.calibration_add_hold_start = 0
            self.calibration_delete_hold_start = 0
            if not in_cooldown:
                msg = f"CALIBRATE POINT {next_point_num} | PINKY PINCH TO SET"
        
        return {
            "mode": "calibration", 
            "msg": msg, 
            "progress": progress,
            "hand_pos": (hand_pos.x, hand_pos.y),
            "step": len(self.calibration_points),
            "points": list(self.calibration_points),
            "roi_preview": self.get_roi_preview(),
            "debug": {
                "dist_idx": self.last_dist_index,
                "dist_mid": self.last_dist_middle,
                "thresh": self.pinch_trigger,
                "fingers": self.get_finger_states(landmarks)
            }
        }

    def process_running(self, hand_pos, gesture, landmarks):
        now = time.time()
        target_x, target_y = self.map_coordinates(hand_pos, now)
        
        if gesture != self.current_gesture:
            if gesture == "left_pinch":
                self.gesture_lock_pos = (target_x, target_y)
                self.left_pinch_start_time = now
                
            elif gesture == "right_pinch":
                 if now - self.last_right_click_time > self.right_click_min_interval:
                    pyautogui.rightClick(int(target_x), int(target_y))
                    self.last_right_click_time = now
            
            elif gesture == "move":
                if self.is_dragging:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                else:
                    if self.current_gesture == "left_pinch" and self.gesture_lock_pos is not None:
                        if now - self.left_pinch_start_time <= self.tap_max_duration:
                            if now - self.last_left_click_time > self.left_click_min_interval:
                                lock_x, lock_y = self.gesture_lock_pos
                                pyautogui.click(int(lock_x), int(lock_y))
                                self.last_left_click_time = now
                self.gesture_lock_pos = None
            
            elif gesture == "scroll":
                self.scroll_anchor_y = target_y
                self.gesture_lock_pos = (target_x, target_y)

            self.current_gesture = gesture

        final_x, final_y = target_x, target_y
        
        if self.current_gesture == "left_pinch":
            if self.gesture_lock_pos:
                lock_x, lock_y = self.gesture_lock_pos
                dist = math.hypot(target_x - lock_x, target_y - lock_y)
                
                if dist < self.deadzone_radius:
                    final_x, final_y = lock_x, lock_y
                else:
                    if not self.is_dragging:
                        pyautogui.mouseDown(int(lock_x), int(lock_y))
                        self.is_dragging = True
            
            self.move_cursor(final_x, final_y)
            
        elif self.current_gesture == "right_pinch":
             self.move_cursor(final_x, final_y) 
        
        elif self.current_gesture == "fist":
            if not self.is_four_fingers_active:
                if now - self.last_fist_click_time > self.fist_click_min_interval:
                    pyautogui.doubleClick()
                    self.last_fist_click_time = now
                    self.is_four_fingers_active = True
            self.move_cursor(final_x, final_y)

        elif self.current_gesture == "middle_click":
            if not self.is_middle_click_active:
                if now - self.last_middle_click_time > self.middle_click_min_interval:
                    pyautogui.middleClick()
                    self.last_middle_click_time = now
                    self.is_middle_click_active = True
            self.move_cursor(final_x, final_y)
            
        elif self.current_gesture == "scroll":
            if self.gesture_lock_pos:
                final_x, final_y = self.gesture_lock_pos
            
            if self.scroll_anchor_y is not None:
                dy = target_y - self.scroll_anchor_y
                scroll_threshold = 25
                
                if abs(dy) > scroll_threshold:
                    move_delta_y = target_y - (self.last_cursor_pos[1] if self.last_cursor_pos else target_y)
                    
                    is_returning = (dy * move_delta_y) < -0.1
                    
                    if not is_returning:
                        clicks = int(dy * self.scroll_speed_factor / 10) 
                        if clicks != 0:
                            pyautogui.scroll(clicks * 20)
            
            self.move_cursor(final_x, final_y)

        else:
            self.is_four_fingers_active = False
            self.is_middle_click_active = False
            self.move_cursor(final_x, final_y)
        
        return {
            "mode": "running",
            "screen_pos": (final_x, final_y),
            "is_dragging": self.is_dragging,
            "roi": self.roi,
            "hand_pos": (hand_pos.x, hand_pos.y),
            "debug": {
                "dist_idx": self.last_dist_index,
                "dist_mid": self.last_dist_middle,
                "thresh": self.pinch_trigger,
                "fingers": self.get_finger_states(landmarks)
            }
        }

    def process(self, hands_data):
        progress, msg = self.update_system_state(hands_data)
        system_info = {"is_active": self.is_active, "state_progress": progress, "state_msg": msg}

        if not self.is_active or not hands_data:
            return {"system": system_info}
        
        hand = hands_data[0]
        landmarks = hand["landmarks"]
        hand_pos = self.get_stable_hand_pos(landmarks)

        if not self.is_calibrated:
            result = self.process_calibration(hand_pos, landmarks)
        else:
            gesture = self.detect_gesture_priority(landmarks)
            result = self.process_running(hand_pos, gesture, landmarks)
            
        result["system"] = system_info
        return result
