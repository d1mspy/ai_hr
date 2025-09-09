import torch

class OnlineVAD():
    def __init__(self,
                 model,
                 threshold: float = 0.3,
                 sampling_rate: int = 16000,
                 min_silence_duration_ms: int = 300,
                 max_silence_duration_ms: int = 3000
                 ):
        
        self.model = model
        self.threshold = threshold
        self.sampling_rate = sampling_rate

        self.min_silence_samples = sampling_rate * min_silence_duration_ms / 1000
        self.max_silence_samples = sampling_rate * max_silence_duration_ms / 1000
        self.speech_stack = []
        self.reset_states()

    def reset_states(self):

        self.model.reset_states()
        self.triggered = False
        self.temp_end = 0
        self.current_sample = 0
        self.last_speech_sample = 0


    @torch.no_grad()     
    def __call__(self, x) -> torch.Tensor | str:

        if not torch.is_tensor(x):
            try:
                x = torch.Tensor(x)
            except:
                raise TypeError("Audio cannot be casted to tensor. Cast it manually")

        speech_prob = self.model(x, self.sampling_rate).item()
        window_size_samples = len(x[0]) if x.dim() == 2 else len(x)
        self.current_sample += window_size_samples

        if (speech_prob >= self.threshold):
            self.last_speech_sample = self.current_sample
            self.speech_stack.append(x)
            self.temp_end = 0
            self.triggered = True
        
        if (self.current_sample - self.last_speech_sample >= self.max_silence_samples):
            self.reset_states()
            return 'stop_answer'
            
        if (speech_prob < self.threshold - 0.05) and self.triggered:
            if not self.temp_end:
                self.temp_end = self.current_sample
            if self.current_sample - self.temp_end < self.min_silence_samples:
                return 'ok'
            else:
                self.temp_end = 0
                self.triggered = False
                self.speech_stack.append(x)
                concated_audio = torch.cat(self.speech_stack, dim=0)
                self.speech_stack = []
                return concated_audio
            
        return 'ok'