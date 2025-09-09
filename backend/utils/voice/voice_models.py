import torch
from onnx_asr import load_model
from .path_config import SILERO_VAD_MODEL_PATH, PARAKEET_MODEL_DIR, SILERO_TTS_MODEL_PATH

silero_vad_model = torch.jit.load(SILERO_VAD_MODEL_PATH)
silero_vad_model.eval()


parakeet_stt_model = load_model(model="nemo-parakeet-tdt-0.6b-v3", 
                            path=PARAKEET_MODEL_DIR, 
                            providers=["CPUExecutionProvider"])

silero_tts_model = torch.package.PackageImporter(SILERO_TTS_MODEL_PATH).load_pickle("tts_models", "model")