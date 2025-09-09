<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';

  let isMuted: boolean = false;
  let isRecording: boolean = false;
  let interviewTime: string = '00:00';
  let timerInterval: number | null = null;
  let startTime: number = 0;

  let encryptedUserId: string = '';
  $: encryptedUserId = ($page.params.id as string) ?? '';
  
  let ws: WebSocket | null = null;
  let audioContext: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let processor: ScriptProcessorNode | null = null;
  let source: MediaStreamAudioSourceNode | null = null;

  onMount(() => {
    console.log('Encrypted ID from route:', encryptedUserId);
    startTimer();
  });

  onDestroy(() => {
    if (timerInterval) clearInterval(timerInterval);
    stopRecording();
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ type: 'audio_end', timestamp: Date.now() })); } catch {}
      setTimeout(() => ws?.close(1000, 'page unload'), 100);
    }
  });

  const startTimer = () => {
    startTime = Date.now();
    timerInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const minutes = Math.floor(elapsed / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);
      interviewTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
  };

  const ensureWS = async (): Promise<boolean> => {
    if (!browser) return false;
    if (!encryptedUserId) {
      console.error('No encryptedUserId in URL');
      return false;
    }
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return true;
    }

    return new Promise((resolve) => {
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
      const host = location.host;
      ws = new WebSocket(`${scheme}://${host}/api/interview/${encryptedUserId}`);

      ws.onopen = () => {
        console.log('WS connected:', encryptedUserId);
        // ВАЖНО: первый кадр должен быть текстовым JSON
        ws!.send(JSON.stringify({ type: 'audio_start', timestamp: Date.now() }));
        resolve(true);
      };
      
      ws.onmessage = (e) => {
        if (e.data instanceof Blob) {
          handleAudioResponse(e.data);
        } else {
          try {
            const message = JSON.parse(e.data);
            console.log('WS message:', message);
          } catch (error) {
            console.log('Raw text message:', e.data);
          }
        }
      };
      
      ws.onerror = (e) => {
        console.error('WS error:', e);
        resolve(false);
      };
      
      ws.onclose = (e) => {
        console.log('WS closed:', e.code, e.reason);
        resolve(false);
      };

      // Таймаут подключения
      setTimeout(() => {
        if (ws?.readyState === WebSocket.CONNECTING) {
          console.error('WebSocket connection timeout');
          ws.close();
          resolve(false);
        }
      }, 5000);
    });
  };

  const bytesToBase64 = (bytes: Uint8Array) => {
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  };

  const convertFloat32ToInt16 = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }
    return int16Array;
  };

  const startRecording = async (): Promise<boolean> => {
    try {
      // Получаем доступ к микрофону с нужными параметрами
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      });

      // Создаем AudioContext с нужной частотой дискретизации
      audioContext = new AudioContext({ 
        sampleRate: 16000,
        latencyHint: 'interactive'
      });

      // Создаем источник из медиапотока
      source = audioContext.createMediaStreamSource(mediaStream);
      
      // Создаем процессор для обработки аудио (512 samples per chunk)
      processor = audioContext.createScriptProcessor(512, 1, 1);
      
      // Настраиваем обработчик данных
      processor.onaudioprocess = (event) => {
        if (!isRecording || !ws || ws.readyState !== WebSocket.OPEN) return;

        try {
          // Float32 → Int16
          const inputData = event.inputBuffer.getChannelData(0);
          const int16Data = convertFloat32ToInt16(inputData);
          const bytes = new Uint8Array(int16Data.buffer);

          // (опционально) простейший бэкпрешер
          if (ws.bufferedAmount > 1_000_000) { // ~1MB
            // пропускаем / ждём следующий такт аудио, чтобы не забить сокет
            return;
          }

          // base64 и JSON
          const b64 = bytesToBase64(bytes);
          ws.send(JSON.stringify({
            type: 'audio_chunk',
            chunk: b64,
            timestamp: Date.now()
          }));
        } catch (error) {
          console.error('Error processing audio chunk:', error);
        }
      };
      
      // Соединяем узлы
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      isRecording = true;
      console.log('Recording started with 16kHz mono, 512 sample chunks');
      return true;
      
    } catch (error) {
      console.error('Error starting recording:', error);
      stopRecording();
      return false;
    }
  };

  const stopRecording = () => {
    // Отключаем и очищаем аудио узлы
    if (processor) {
      processor.disconnect();
      processor = null;
    }
    if (source) {
      source.disconnect();
      source = null;
    }
    
    // Останавливаем медиапоток
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => {
        track.stop();
        track.enabled = false;
      });
      mediaStream = null;
    }
    
    // Закрываем аудиоконтекст
    if (audioContext) {
      if (audioContext.state !== 'closed') {
        audioContext.close();
      }
      audioContext = null;
    }
    
    isRecording = false;
    console.log('Recording stopped');
  };

  const handleAudioResponse = async (audioBlob: Blob) => {
    try {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.volume = isMuted ? 0 : 1;
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
    } catch (error) {
      console.error('Error playing audio response:', error);
    }
  };

  const toggleMicrophone = async () => {
    if (isRecording) {
      // Останавливаем запись
      stopRecording();
      
      // Закрываем WebSocket соединение
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'audio_end', timestamp: Date.now() }));
        } catch {}
        // небольшая пауза, чтобы кадр успел уйти
        setTimeout(() => ws?.close(1000, 'Recording stopped by user'), 100);
      }
      ws = null;
    } else {
      try {
        // Сначала устанавливаем WebSocket соединение
        const connected = await ensureWS();
        if (!connected) {
          console.error('Failed to establish WebSocket connection');
          return;
        }
        
        // Затем начинаем запись
        const recordingStarted = await startRecording();
        if (!recordingStarted) {
          console.error('Failed to start recording');
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close(1000, 'Recording failed');
          }
          ws = null;
        }
      } catch (error) {
        console.error('Error starting recording session:', error);
        stopRecording();
        if (ws) {
          ws.close(1000, 'Recording session error');
          ws = null;
        }
      }
    }
  };

  const toggleMute = () => {
    isMuted = !isMuted;
    // Здесь можно добавить логику для реального отключения звука
    console.log(isMuted ? 'Audio muted' : 'Audio unmuted');
  };

  const endInterview = async () => {
    if (confirm("Завершить собеседование?")) {
      // Останавливаем запись и закрываем соединения
      stopRecording();
      if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ type: 'audio_end', timestamp: Date.now() })); } catch {}
        setTimeout(() => ws?.close(1000, 'page unload'), 100);
      }
      ws = null;
      
      // Перенаправляем на страницу результатов
      window.location.href = "/results";
    }
  };
</script>

<svelte:head>
  <title>Собеседование - AI-HR Сервис</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</svelte:head>

<div class="container">
  <div class="header">
    <div class="interview-info">
      <h1>Собеседование</h1>
      <p>Должность: Frontend разработчик</p>
    </div>
    <div class="timer">
      <span class="time">{interviewTime}</span>
      <span class="recording-indicator" class:active={isRecording}>● {isRecording ? 'Запись' : 'Пауза'}</span>
    </div>
  </div>

  <div class="main-content">
    <div class="audio-container">
      <div class="participants">
        <div class="participant candidate">
          <div class="avatar">
            <span>К</span>
          </div>
          <div class="participant-info">
            <h3>Кандидат</h3>
          </div>
          <div class="audio-indicator" class:active={isRecording}>
            <div class="audio-waves">
              {#each Array(5) as _, i}
                <div class="wave" style={`--i: ${i};`}></div>
              {/each}
            </div>
          </div>
        </div>
        
        <div class="participant hr">
          <div class="avatar">
            <span>Р</span>
          </div>
          <div class="participant-info">
            <h3>AI HR</h3>
          </div>
          <div class="audio-indicator" class:active={true}>
            <div class="audio-waves">
              {#each Array(5) as _, i}
                <div class="wave" style={`--i: ${i};`}></div>
              {/each}
            </div>
          </div>
        </div>
      </div>
      
      <div class="visualization-container">
        <div class="voice-visualization" class:active={isRecording}>
          <div class="pulse-ring ring-1"></div>
          <div class="pulse-ring ring-2"></div>
          <div class="pulse-ring ring-3"></div>
          <div class="center-circle">
            <div class="sound-waves">
              {#each Array(8) as _, i}
                <div class="wave-bar" style={`--i: ${i};`}></div>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="controls">
      <button class="control-btn" on:click={toggleMute} class:muted={isMuted}>
        {#if isMuted}
          <span class="icon">🔇</span>
          <span>Включить звук</span>
        {:else}
          <span class="icon">🔊</span>
          <span>Выключить звук</span>
        {/if}
      </button>
      
      <button class="mic-btn" on:click={toggleMicrophone} class:recording={isRecording}>
        <span class="icon">{isRecording ? '🎤' : '🎤'}</span>
      </button>
      
      <button class="control-btn end-call" on:click={endInterview}>
        <span class="icon">📞</span>
        <span>Завершить</span>
      </button>
    </div>
  </div>

  <div class="footer">
    <div class="ai-assistant">
      <span class="ai-icon">🤖</span>
      <span class="ai-message">AI анализирует ваши ответы в реальном времени</span>
    </div>
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    min-height: 100vh;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
  }

  .container {
    width: 100%;
    max-width: 900px;
    background: white;
    border-radius: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    height: 90vh;
    max-height: 700px;
    display: flex;
    flex-direction: column;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #e5e7eb;
    background: #f8fafc;
    flex-shrink: 0;
  }

  .interview-info h1 {
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .interview-info p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .timer {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .time {
    font-size: 16px;
    font-weight: 600;
    color: #374151;
  }

  .recording-indicator {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 4px;
  }

  .recording-indicator.active {
    color: #ef4444;
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
    overflow: hidden;
  }

  .audio-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    height: 100%;
    padding: 10px 0;
  }

  .participants {
    display: flex;
    justify-content: center;
    gap: 40px;
    width: 100%;
    margin-bottom: 20px;
  }

  .participant {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 20px;
    background: #f8fafc;
    border-radius: 16px;
    width: 180px;
  }

  .avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: #3b82f6;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 24px;
  }

  .participant.hr .avatar {
    background: #10b981;
  }

  .participant-info {
    text-align: center;
  }

  .participant-info h3 {
    font-size: 16px;
    font-weight: 600;
    color: #374151;
    margin: 0 0 4px 0;
  }

  .audio-indicator {
    width: 100%;
    height: 30px;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .audio-waves {
    display: flex;
    align-items: center;
    gap: 3px;
    height: 20px;
  }

  .wave {
    width: 3px;
    height: 8px;
    background: #d1d5db;
    border-radius: 2px;
    animation: wave 1.2s infinite;
    animation-delay: calc(var(--i) * 0.15s);
  }

  .audio-indicator.active .wave {
    background: #10b981;
    animation: wave-active 1.2s infinite;
    animation-delay: calc(var(--i) * 0.15s);
  }

  .visualization-container {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 10px 0;
  }

  .voice-visualization {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .pulse-ring {
    position: absolute;
    border: 2px solid #3b82f6;
    border-radius: 50%;
    opacity: 0;
  }

  .voice-visualization.active .pulse-ring {
    animation: pulse 3s infinite;
  }

  .ring-1 {
    width: 100px;
    height: 100px;
    animation-delay: 0s;
  }

  .ring-2 {
    width: 120px;
    height: 120px;
    animation-delay: 1s;
  }

  .ring-3 {
    width: 140px;
    height: 140px;
    animation-delay: 2s;
  }

  .center-circle {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: #3b82f6;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
    position: relative;
    z-index: 10;
  }

  .sound-waves {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 2px;
    width: 50px;
    height: 30px;
  }

  .wave-bar {
    width: 2px;
    height: 8px;
    background: white;
    border-radius: 1px;
    animation: wave 1.2s infinite;
    animation-delay: calc(var(--i) * 0.15s);
  }

  .voice-visualization.active .wave-bar {
    animation: wave-active 1.2s infinite;
    animation-delay: calc(var(--i) * 0.15s);
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 0.8;
    }
    70% {
      transform: scale(1.3);
      opacity: 0;
    }
    100% {
      transform: scale(1.3);
      opacity: 0;
    }
  }

  @keyframes wave {
    0%, 100% {
      height: 8px;
    }
    50% {
      height: 16px;
    }
  }

  @keyframes wave-active {
    0%, 100% {
      height: 12px;
    }
    50% {
      height: 24px;
    }
  }

  .controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 15px;
    margin-top: auto;
    padding-top: 20px;
  }

  .control-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 13px;
    color: #374151;
  }

  .control-btn:hover {
    background: #f1f5f9;
    transform: translateY(-2px);
  }

  .control-btn.muted {
    background: #fee2e2;
    border-color: #fecaca;
  }

  .control-btn.end-call {
    background: #fee2e2;
    color: #dc2626;
  }

  .control-btn.end-call:hover {
    background: #fecaca;
  }

  .icon {
    font-size: 18px;
  }

  .mic-btn {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: #3b82f6;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }

  .mic-btn:hover {
    background: #2563eb;
    transform: scale(1.05);
  }

  .mic-btn.recording {
    background: #ef4444;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
  }

  .mic-btn.recording:hover {
    background: #dc2626;
  }

  .mic-btn .icon {
    font-size: 24px;
    color: white;
  }

  .footer {
    padding: 12px 20px;
    border-top: 1px solid #e5e7eb;
    background: #f8fafc;
    flex-shrink: 0;
  }

  .ai-assistant {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 13px;
    color: #6b7280;
  }

  .ai-icon {
    font-size: 16px;
  }

  /* Адаптивность */
  @media (max-width: 768px) {
    .container {
      height: 95vh;
      max-height: none;
      border-radius: 16px;
    }
    
    .header {
      padding: 16px 20px;
    }
    
    .interview-info h1 {
      font-size: 18px;
    }
    
    .main-content {
      padding: 16px;
    }
    
    .participants {
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }
    
    .participant {
      width: 160px;
      padding: 16px;
    }
    
    .avatar {
      width: 60px;
      height: 60px;
      font-size: 20px;
    }
    
    .voice-visualization {
      width: 100px;
      height: 100px;
    }
    
    .center-circle {
      width: 70px;
      height: 70px;
    }
    
    .controls {
      gap: 10px;
    }
    
    .control-btn {
      padding: 8px 12px;
      font-size: 12px;
    }
    
    .mic-btn {
      width: 50px;
      height: 50px;
    }
    
    .mic-btn .icon {
      font-size: 20px;
    }
  }
</style>