import torch
import os
import requests


#silero
SILERO_MODEL_DIR = "./silero_vad"
os.makedirs(SILERO_MODEL_DIR, exist_ok=True)

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=True, 
                              trust_repo=True, 
                              onnx=False)         

model_path = os.path.join(SILERO_MODEL_DIR, "silero_vad_jit.pth")
torch.jit.save(model, model_path)

SILERO_MODEL_PATH=model_path



#parakeet
PARAKEET_MODEL_DIR = "./parakeet_stt"
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