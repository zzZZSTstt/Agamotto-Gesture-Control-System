import winsound
import threading

class SoundManager:
    @staticmethod
    def play_active():
        def _play():
            winsound.Beep(1000, 200) 
            winsound.Beep(1500, 300) 
        threading.Thread(target=_play, daemon=True).start()

    @staticmethod
    def play_deactive():
        def _play():
            winsound.Beep(800, 200) 
            winsound.Beep(500, 300) 
        threading.Thread(target=_play, daemon=True).start()

    @staticmethod
    def play_calibration_tick():
         threading.Thread(target=lambda: winsound.Beep(2000, 50), daemon=True).start()

    @staticmethod
    def play_calibration_done():
        def _play():
            winsound.Beep(1200, 100)
            winsound.Beep(1200, 100)
        threading.Thread(target=_play, daemon=True).start()
