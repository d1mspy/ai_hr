import os

MODELS_ROOT = os.getenv("MODELS_ROOT", "/models")

SILERO_VAD_MODEL_DIR  = os.getenv("SILERO_VAD_MODEL_DIR",  os.path.join(MODELS_ROOT, "silero_vad"))
SILERO_TTS_MODEL_DIR  = os.getenv("SILERO_TTS_MODEL_DIR",  os.path.join(MODELS_ROOT, "silero_tts"))
PARAKEET_MODEL_DIR    = os.getenv("PARAKEET_MODEL_DIR",    os.path.join(MODELS_ROOT, "parakeet_stt"))


#do not change
SILERO_VAD_MODEL_PATH = os.path.join(SILERO_VAD_MODEL_DIR, "silero_vad_jit.pth")
SILERO_TTS_MODEL_PATH = os.path.join(SILERO_TTS_MODEL_DIR, 'v3_1_ru.pt')
