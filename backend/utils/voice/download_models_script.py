import torch
import os
import requests
from path_config import SILERO_TTS_MODEL_PATH, SILERO_TTS_MODEL_DIR, \
    SILERO_VAD_MODEL_DIR, SILERO_VAD_MODEL_PATH, PARAKEET_MODEL_DIR 

#silero_vad
os.makedirs(SILERO_VAD_MODEL_DIR, exist_ok=True)
silero_vad, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=True, 
                              trust_repo=True, 
                              onnx=False)         

torch.jit.save(silero_vad, SILERO_VAD_MODEL_PATH)



#silero_tts
os.makedirs(SILERO_TTS_MODEL_DIR, exist_ok=True)
if not os.path.isfile(SILERO_TTS_MODEL_PATH):
    silero_tts_url = 'https://models.silero.ai/models/tts/ru/v3_1_ru.pt'
    torch.hub.download_url_to_file(silero_tts_url, SILERO_TTS_MODEL_PATH, progress=False)



#parakeet
def download_file(url, local_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


repo_id = "istupakov/parakeet-tdt-0.6b-v3-onnx"
files_to_download = [
    "config.json",
    "vocab.txt",
    "encoder-model.onnx",
    "encoder-model.onnx.data",
    "decoder_joint-model.onnx",
]

for filename in files_to_download:
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    download_file(url, f"{PARAKEET_MODEL_DIR}/{filename}")