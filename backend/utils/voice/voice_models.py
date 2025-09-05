import torch
from onnx_asr import load_model
from download_models_script import SILERO_MODEL_PATH, PARAKEET_MODEL_DIR

silero_vad_model = torch.jit.load(SILERO_MODEL_PATH)
silero_vad_model.eval()


parakeet_stt_model = load_model(model="nemo-parakeet-tdt-0.6b-v3", 
                            path=PARAKEET_MODEL_DIR, 
                            providers=["CPUExecutionProvider"])