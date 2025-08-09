# app/controllers/video_controller.py
from app.services.video_service import VideoService

class VideoController:
    def __init__(self):
        self.video_service = VideoService()
    
    def start_video(self, callback=None):
        if callback:
            self.video_service.set_frame_callback(callback)
        return self.video_service.start_camera()
    
    def stop_video(self):
        self.video_service.stop_camera()
    
    def set_detection_mode(self, mode):
        self.video_service.set_detection_mode(mode)
    
    def set_target_object(self, object_name):
        self.video_service.set_target_object(object_name)
    
    def set_mask_method(self, method):
        self.video_service.mask_method = method  # Usando property ahora
    
    def toggle_voice_listening(self):
        return self.video_service.toggle_listening()
    
    def process_command(self, command):
        return self.video_service.process_command(command)
    
    def speak(self, text):
        self.video_service.speak(text)