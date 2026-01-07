import cv2
import time
import numpy as np

COLOR_CYAN = (255, 255, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (50, 50, 50)
COLOR_BLACK = (0, 0, 0)

class HUD:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_text_centered(self, img, text, y, scale=1.0, color=COLOR_WHITE, thickness=2):
        h, w = img.shape[:2]
        (text_w, text_h), _ = cv2.getTextSize(text, self.font, scale, thickness)
        x = (w - text_w) // 2
        cv2.putText(img, text, (x+2, y+2), self.font, scale, COLOR_BLACK, thickness+1)
        cv2.putText(img, text, (x, y), self.font, scale, color, thickness)

    def draw_overlay_box(self, img, x, y, w, h, alpha=0.6):
        roi = img[y:y+h, x:x+w]
        black_rect = np.zeros(roi.shape, dtype=np.uint8)
        cv2.addWeighted(roi, 1 - alpha, black_rect, alpha, 0, roi)

    def draw_progress_circle(self, img, center, radius, progress, color=COLOR_CYAN):
        cv2.circle(img, center, radius, COLOR_GRAY, 5)
        if progress > 0:
            axes = (radius, radius)
            end_angle = 360 * progress
            cv2.ellipse(img, center, axes, -90, 0, end_angle, color, 5)

    def draw_crosshair(self, img, pos_norm):
        if not pos_norm: return
        h, w = img.shape[:2]
        cx = int(pos_norm[0] * w)
        cy = int(pos_norm[1] * h)
        
        cv2.line(img, (0, cy), (w, cy), (255, 255, 255), 1)
        cv2.line(img, (cx, 0), (cx, h), (255, 255, 255), 1)
        cv2.circle(img, (cx, cy), 5, COLOR_CYAN, -1)
        cv2.circle(img, (cx, cy), 15, COLOR_CYAN, 1)

    def draw_agamotto_eye(self, img, center, radius, progress, rotation=0, phase=0):
        try:
            cx, cy = int(center[0]), int(center[1])
            center = (cx, cy)
            radius = int(radius)
            
            GOLD = (0, 215, 255)       
            BRONZE = (30, 105, 180)    
            GREEN_GLOW = (100, 255, 100)
            GREEN_CORE = (0, 255, 0)
            
            t = time.time() * 40
            
            def draw_poly(img, center, r, sides, angle, color, thick=1, fill=False):
                try:
                    theta = np.deg2rad(angle + np.arange(sides) * 360 / sides)
                    x = center[0] + r * np.cos(theta)
                    y = center[1] + r * np.sin(theta)
                    pts = np.stack((x, y), axis=1).astype(np.int32)
                    
                    if fill:
                        cv2.fillPoly(img, [pts], color)
                    else:
                        cv2.polylines(img, [pts], True, color, thick, cv2.LINE_AA)
                except Exception:
                    pass

            cv2.circle(img, center, radius, BRONZE, 6, cv2.LINE_AA)
            cv2.circle(img, center, radius - 10, GOLD, 2, cv2.LINE_AA)
            
            if phase >= 1:
                draw_poly(img, center, radius + 20, 4, t, GOLD, 2)
                draw_poly(img, center, radius + 20, 4, -t, GOLD, 2)
                cv2.circle(img, center, radius + 40, GOLD, 1, cv2.LINE_AA)
                
            if phase >= 2:
                speed = t * (1.0 + progress * 2.0)
                draw_poly(img, center, radius + 60, 3, speed, GREEN_GLOW, 2)
                draw_poly(img, center, radius + 60, 3, -speed + 60, GREEN_GLOW, 2)
                
            if phase >= 2 and progress > 0:
                glow_radius = int(radius * 0.4 * progress)
                if glow_radius > 0:
                    overlay = img.copy()
                    cv2.circle(overlay, center, glow_radius + 10, GREEN_GLOW, -1)
                    cv2.addWeighted(overlay, 0.4 * progress, img, 1.0, 0, img)
                    cv2.circle(img, center, int(glow_radius * 0.6), GREEN_CORE, -1)

            lid_w = int(radius * 0.8)
            lid_h = int(radius * 0.5)
            
            cv2.ellipse(img, center, (lid_w, lid_h), 0, 0, 360, BRONZE, 3, cv2.LINE_AA)
            
            if phase < 2:
                cv2.line(img, (cx - lid_w, cy), (cx + lid_w, cy), BRONZE, 2)
                cv2.line(img, (cx, cy - lid_h), (cx, cy + lid_h), BRONZE, 2)
            
            if progress >= 0.95:
                cv2.circle(img, center, int(radius * 0.2), (255, 255, 255), -1)
                for i in range(12):
                    angle = np.deg2rad(i * 30)
                    r_end = radius * 2.0
                    x2 = int(cx + r_end * np.cos(angle))
                    y2 = int(cy + r_end * np.sin(angle))
                    cv2.line(img, center, (x2, y2), GREEN_GLOW, 2)
        except Exception:
            pass

    def draw_standby(self, img, system_info):
        try:
            h, w = img.shape[:2]
            overlay = img.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 10), -1)
            cv2.addWeighted(overlay, 0.9, img, 0.1, 0, img)
            
            progress = system_info.get("state_progress", 0)
            msg = system_info.get("state_msg") or ""
            
            phase = 0
            if "CROSS" in msg: phase = 1
            if "OPENING" in msg or "EYE" in msg: phase = 2
            
            center = (w//2, h//2)
            radius = 100
            
            self.draw_agamotto_eye(img, center, radius, progress, phase=phase)
            
            if phase == 0:
                self.draw_text_centered(img, "PHASE 1: THE SEAL", h//2 + 150, 0.7, COLOR_CYAN, 1)
                self.draw_text_centered(img, "(Pinch Ring Finger & Thumb)", h//2 + 180, 0.5, COLOR_WHITE, 1)
            elif phase == 1:
                self.draw_text_centered(img, "PHASE 2: THE CROSSING", h//2 + 150, 0.7, COLOR_CYAN, 1)
                self.draw_text_centered(img, "(Cross Hands to Unlock)", h//2 + 180, 0.5, COLOR_WHITE, 1)
            elif phase == 2:
                self.draw_text_centered(img, "UNLOCKING THE EYE...", h//2 + 150, 0.8, COLOR_GREEN, 2)
        except Exception:
             pass

    def draw_calibration(self, img, data):
        h, w = img.shape[:2]
        msg = data["msg"]
        progress = data.get("progress", 0)
        
        if data.get("hand_pos"):
            self.draw_crosshair(img, data["hand_pos"])
            if progress and progress > 0:
                cx = int(data["hand_pos"][0] * w)
                cy = int(data["hand_pos"][1] * h)
                
                is_cooldown = "SUCCESS" in str(msg)
                color = COLOR_RED if is_cooldown else COLOR_CYAN
                self.draw_progress_circle(img, (cx, cy), 35, progress, color)
        
        points = data.get("points") or []
        for i, (px, py) in enumerate(points):
            x = int(px * w)
            y = int(py * h)
            cv2.circle(img, (x, y), 10, COLOR_CYAN, 2)
            cv2.circle(img, (x, y), 3, COLOR_CYAN, -1)
            cv2.putText(img, str(i + 1), (x + 14, y - 8), self.font, 0.6, COLOR_WHITE, 2)
        
        roi = data.get("roi_preview")
        if roi:
            px1, py1 = int(roi["x1"] * w), int(roi["y1"] * h)
            px2, py2 = int(roi["x2"] * w), int(roi["y2"] * h)
            corner_len = 20
            color = COLOR_CYAN
            thick = 2
            
            cv2.line(img, (px1, py1), (px1 + corner_len, py1), color, thick)
            cv2.line(img, (px1, py1), (px1, py1 + corner_len), color, thick)
            cv2.line(img, (px2, py1), (px2 - corner_len, py1), color, thick)
            cv2.line(img, (px2, py1), (px2, py1 + corner_len), color, thick)
            cv2.line(img, (px2, py2), (px2 - corner_len, py2), color, thick)
            cv2.line(img, (px2, py2), (px2, py2 - corner_len), color, thick)
            cv2.line(img, (px1, py2), (px1 + corner_len, py2), color, thick)
            cv2.line(img, (px1, py2), (px1, py2 - corner_len), color, thick)
        
        lines = [part.strip() for part in str(msg).split("|")] if msg else [""]
        lines = [ln for ln in lines if ln]
        
        box_h = 80 if len(lines) <= 1 else 110
        self.draw_overlay_box(img, 0, h - box_h, w, box_h)
        if len(lines) <= 1:
            self.draw_text_centered(img, f"CALIBRATION: {msg}", h - 30, 0.8, COLOR_WHITE)
        else:
            self.draw_text_centered(img, lines[0], h - 60, 0.8, COLOR_WHITE)
            self.draw_text_centered(img, lines[1], h - 25, 0.7, COLOR_CYAN, 2)

    def draw_running(self, img, data, fps):
        h, w = img.shape[:2]
        
        if data.get("hand_pos"):
            self.draw_crosshair(img, data["hand_pos"])

        self.draw_overlay_box(img, 0, 0, w, 40, 0.4)
        cv2.putText(img, f"FPS: {int(fps)}", (20, 28), self.font, 0.6, COLOR_CYAN, 2)
        
        status = "ACTIVE"
        color = COLOR_GREEN
        if data.get("is_dragging"):
            status = "DRAGGING"
            color = COLOR_RED
            
        cv2.putText(img, f"MODE: {status}", (w - 180, 28), self.font, 0.6, color, 2)
        
        debug = data.get("debug")
        if debug:
            dist_idx = float(debug.get("dist_idx", 0.0))
            dist_mid = float(debug.get("dist_mid", 0.0))
            thresh = float(debug.get("thresh", 0.0))
            cv2.putText(img, f"IDX: {dist_idx:.2f} < {thresh:.2f}", (20, 70), self.font, 0.55, COLOR_WHITE, 2)
            cv2.putText(img, f"MID: {dist_mid:.2f} < 0.20", (20, 95), self.font, 0.55, COLOR_WHITE, 2)
        
        if data.get("roi"):
            x1, y1, x2, y2 = data["roi"]["x1"], data["roi"]["y1"], data["roi"]["x2"], data["roi"]["y2"]
            px1, py1 = int(x1 * w), int(y1 * h)
            px2, py2 = int(x2 * w), int(y2 * h)
            
            corner_len = 20
            color = COLOR_CYAN
            thick = 2
            
            cv2.line(img, (px1, py1), (px1 + corner_len, py1), color, thick)
            cv2.line(img, (px1, py1), (px1, py1 + corner_len), color, thick)
            cv2.line(img, (px2, py1), (px2 - corner_len, py1), color, thick)
            cv2.line(img, (px2, py1), (px2, py1 + corner_len), color, thick)
            cv2.line(img, (px2, py2), (px2 - corner_len, py2), color, thick)
            cv2.line(img, (px2, py2), (px2, py2 - corner_len), color, thick)
            cv2.line(img, (px1, py2), (px1 + corner_len, py2), color, thick)
            cv2.line(img, (px1, py2), (px1, py2 - corner_len), color, thick)

    def draw_system_overlay(self, img, system_info):
        h, w = img.shape[:2]
        progress = system_info.get("state_progress", 0)
        msg = system_info.get("state_msg", "")
        
        if progress > 0 and system_info.get("is_active"):
            self.draw_progress_circle(img, (w//2, h//2), 100, progress, COLOR_RED)
            self.draw_text_centered(img, msg, h//2 + 140, 0.8, COLOR_RED, 2)
