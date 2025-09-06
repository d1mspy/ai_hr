import os

#can be changed
SILERO_VAD_MODEL_DIR = "./silero_vad"
SILERO_TTS_MODEL_DIR = "./silero_tts"
PARAKEET_MODEL_DIR = "./parakeet_stt"


#do not change
SILERO_VAD_MODEL_PATH = os.path.join(SILERO_VAD_MODEL_DIR, "silero_vad_jit.pth")
SILERO_TTS_MODEL_PATH = os.path.join(SILERO_TTS_MODEL_DIR, 'v3_1_ru.pt')
