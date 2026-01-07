import cv2
import threading
import time
import numpy as np
from .ui import COLOR_CYAN, COLOR_GREEN, COLOR_WHITE, COLOR_GRAY, COLOR_BLACK

class ThreadedCamera:
    def __init__(self, src=0, width=640, height=480):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
        self.stopped = False
        
    def start(self):
        if self.started:
            return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            if self.stopped:
                break
            grabbed, frame = self.cap.read()
            if grabbed:
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
            else:
                self.stopped = True
            
            time.sleep(0.001)

    def read(self):
        with self.read_lock:
            if self.grabbed and self.frame is not None:
                return True, self.frame.copy()
            return False, None

    def release(self):
        self.started = False
        self.stopped = True
        if hasattr(self, 'thread'):
            self.thread.join()
        self.cap.release()
        
    def isOpened(self):
        return self.cap.isOpened()

class CameraSelector:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.available_cameras = []
        self.selected_index = 0
        self.scanning = True

    def scan_cameras(self):
        self.available_cameras = []
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    self.available_cameras.append(i)
                cap.release()
        
        if not self.available_cameras:
            self.available_cameras = [0]
        self.scanning = False

    def draw_ui(self, frame):
        h, w = frame.shape[:2]
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 10), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        cv2.putText(frame, "SELECT CAMERA", (50, 80), self.font, 1.5, COLOR_CYAN, 3)
        cv2.putText(frame, "Press TAB to switch, ENTER to confirm", (50, 130), self.font, 0.7, COLOR_WHITE, 1)
        
        start_y = 200
        for i, cam_idx in enumerate(self.available_cameras):
            color = COLOR_GRAY
            prefix = "  "
            if i == self.selected_index:
                color = COLOR_GREEN
                prefix = "> "
            
            text = f"{prefix}Camera {cam_idx}"
            cv2.putText(frame, text, (50, start_y + i * 60), self.font, 1.0, color, 2)

    def select_camera(self):
        self.scan_cameras()
        
        current_cam = self.available_cameras[self.selected_index]
        cap = cv2.VideoCapture(current_cam)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
            else:
                frame = cv2.flip(frame, 1)
            
            self.draw_ui(frame)
            cv2.imshow('Agamotto Gesture Control System', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27: 
                cap.release()
                return None
            elif key == 13: 
                cap.release()
                return self.available_cameras[self.selected_index]
            elif key == 9: 
                self.selected_index = (self.selected_index + 1) % len(self.available_cameras)
                new_cam = self.available_cameras[self.selected_index]
                cap.release()
                cap = cv2.VideoCapture(new_cam)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
