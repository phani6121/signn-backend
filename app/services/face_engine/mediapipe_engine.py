import mediapipe as mp
import cv2
import numpy as np

mp_face = mp.solutions.face_mesh

class MediaPipeEngine:
    def __init__(self):
        self.mesh = mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
        )

    def process(self, image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return self.mesh.process(rgb)
