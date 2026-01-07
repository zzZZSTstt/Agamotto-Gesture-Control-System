pyinstaller -F -w -i icon.png --collect-all mediapipe --collect-all cv2 --hidden-import=numpy --hidden-import=src.vision --hidden-import=src.controller --add-data="src;src" main.py
