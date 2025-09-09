import torch
from voice_models import silero_tts_model

class VoiceGenerator():
    def __init__(self, tts_model: None = None):
        self.tts_model = tts_model
        self.speaker = 'xenia'
        self.sample_rate = 24000
    
    @torch.no_grad()
    def __call__(self, text: str=silero_tts_model) -> torch.Tensor:
        audio_torch = self.tts_model.apply_tts(text=text,
                                        speaker=self.speaker,
                                        sample_rate=self.sample_rate,
                                        put_accent=True,
                                        put_yo=True)
        return audio_torch