from pydantic import BaseModel
from onnx_asr.adapters import TextResultsAsrAdapter
from online_vad import OnlineVAD


class ChunkProcessAns(BaseModel):
    status: str
    content: str = "-"

class ChunkProcessor():
    def __init__(self, vad_model, stt_model: TextResultsAsrAdapter):
        self.online_vad = self.create_vad(vad_model)
        self.stt_model = stt_model
    
    def create_vad(self, vad_model) -> OnlineVAD:
        return OnlineVAD(vad_model)
    
    def reset(self):
        self.online_vad.reset_states()

    async def __call__(self, audio_chunk) -> ChunkProcessAns:
        try:
            phrase_audio = self.online_vad(audio_chunk)
            if phrase_audio is None:
                return ChunkProcessAns(status='ok')
            else:
                phrase_text = self.stt_model.recognize(phrase_audio)
                return ChunkProcessAns(status='answer', content=phrase_text)
        except Exception as e:
            return ChunkProcessAns(status='bad', content=str(e))