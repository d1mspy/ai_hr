<script lang="ts">
  import { onMount } from 'svelte';

  let vacancyFile: File | null = null;
  let resumeFiles: File[] = []; // несколько резюме
  let isLoading = false;
  let progress = 0;

  // DOCX-валидатор
  const isValidFileType = (file: File): boolean =>
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    file.name.toLowerCase().endsWith('.docx');

  const navigateToResults = () => {
    window.location.href = '/results';
  };

  const handleVacancyUpload = (event: Event): void => {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file && isValidFileType(file)) {
      vacancyFile = file;
    } else {
      alert('Пожалуйста, загружайте только файлы в формате DOCX');
      target.value = '';
    }
  };

  const handleResumeUpload = (event: Event): void => {
    const target = event.target as HTMLInputElement;
    const files = Array.from(target.files ?? []);
    const valid = files.filter(isValidFileType);
    if (valid.length !== files.length) {
      alert('Пожалуйста, загружайте только файлы в формате DOCX');
      target.value = '';
      resumeFiles = [];
      return;
    }
    resumeFiles = valid;
  };

  type BackendDecision = {
    decision: 'reject' | string; // любые иные значения трактуем как "собеседование"
    score: number;               // 0..1
    reasons?: string[];
    details?: Record<string, unknown>;
  };

  type CompareResponse = {
    decision: BackendDecision | Record<string, never>;
    vacancy: Record<string, unknown>;
    text: { cv_text: string; vac_text: string };
  };

  type UIResult = {
    id: number;
    fileName: string;
    verdict: 'собеседование' | 'отказ';
    comment: string;
    score: number; // 0..100
  };

  const startComparison = async (): Promise<void> => {
    if (!vacancyFile || resumeFiles.length === 0) {
      alert('Загрузите вакансию и хотя бы одно резюме');
      return;
    }

    isLoading = true;
    progress = 0;

    const results: UIResult[] = [];
    const total = resumeFiles.length;

    // Последовательно (проще контролировать прогресс). Можно легко распараллелить при желании.
    for (let i = 0; i < total; i++) {
      const cvFile = resumeFiles[i];

      const form = new FormData();
      // ВАЖНО: сначала cv, потом vacancy
      form.append('cv', cvFile, cvFile.name);
      form.append('vacancy', vacancyFile, vacancyFile.name);

      try {
        const resp = await fetch('/api/compare', {
          method: 'POST',
          body: form,
        });

        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`);
        }

        const data: CompareResponse = await resp.json();

        const dec = (data?.decision ?? {}) as BackendDecision;
        const isReject = dec.decision === 'reject';
        const verdict: UIResult['verdict'] = isReject ? 'отказ' : 'собеседование';
        const comment =
          verdict === 'собеседование'
            ? 'здесь должна быть ссылка'
            : Array.isArray(dec.reasons) && dec.reasons.length > 0
              ? dec.reasons.join('; ')
              : 'Причины не указаны';

        const score = Math.round(((dec.score ?? 0) as number) * 100);

        results.push({
          id: i + 1,
          fileName: cvFile.name,
          verdict,
          comment,
          score,
        });
      } catch (e: any) {
        results.push({
          id: i + 1,
          fileName: cvFile.name,
          verdict: 'отказ',
          comment: `Ошибка запроса: ${e?.message ?? e}`,
          score: 0,
        });
      } finally {
        // Простой прогресс по числу обработанных резюме
        progress = Math.min(100, Math.round(((i + 1) / total) * 100));
      }
    }

    // Сохраняем результаты для страницы /results
    sessionStorage.setItem('aihr_results', JSON.stringify(results));

    // Небольшая пауза для UX, затем переход
    setTimeout(() => navigateToResults(), 300);
  };
</script>


<div class="container">
  <div class="column">
    <h2 class="title">ВАКАНСИИ</h2>
    <label class="upload-btn" class:disabled={isLoading}>
      <input
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        on:change={handleVacancyUpload}
        disabled={isLoading}
      />
      <span>+ добавить</span>
    </label>
    <p class="hint">(только DOCX)</p>
    {#if vacancyFile}
      <p class="file-name">{vacancyFile.name}</p>
    {/if}
  </div>

  <div class="center">
    <button class="image-btn" on:click={startComparison} disabled={isLoading}>
      {#if isLoading}
        <div class="loader">
          <div class="spinner"></div>
          <span class="progress-text">{progress}%</span>
        </div>
      {:else}
        <img src="/comparison-icon.png" alt="Сравнить вакансии и резюме" />
      {/if}
    </button>
    <p class="center-hint">Нажмите для сравнения</p>
  </div>

  <div class="column">
    <h2 class="title">РЕЗЮМЕ</h2>
    <label class="upload-btn" class:disabled={isLoading}>
      <input
        type="file"
        multiple
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        on:change={handleResumeUpload}
        disabled={isLoading}
      />
      <span>+ добавить</span>
    </label>
    <p class="hint">(только DOCX)</p>
    {#if resumeFiles.length > 0}
  <ul class="file-list">
    {#each resumeFiles as f}
      <li class="file-name">{f.name}</li>
    {/each}
  </ul>
{/if}
  </div>
</div>

<style>
  :global(body) {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .container {
    display: flex;
    align-items: center;
    gap: 80px;
    padding: 60px;
    background: white;
    border-radius: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    max-width: 900px;
    width: 100%;
  }

  .column {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    min-width: 200px;
    flex: 1;
  }

  .center {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 15px;
  }

  .title {
    font-size: 24px;
    font-weight: 700;
    color: #2d3748;
    margin: 0;
    text-align: center;
  }

  .upload-btn {
    position: relative;
    cursor: pointer;
    padding: 16px 32px;
    background: #f8fafc;
    border: 2px dashed #cbd5e1;
    border-radius: 12px;
    transition: all 0.3s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60px;
    width: 100%;
    box-sizing: border-box;
  }

  .upload-btn:hover:not(.disabled) {
    background: #f1f5f9;
    border-color: #94a3b8;
    transform: translateY(-2px);
  }

  .upload-btn.disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .upload-btn span {
    color: #64748b;
    font-weight: 600;
    font-size: 18px;
  }

  .upload-btn input {
    position: absolute;
    opacity: 0;
    width: 100%;
    height: 100%;
    top: 0;
    left: 0;
    cursor: pointer;
  }

  .hint {
    font-size: 14px;
    color: #94a3b8;
    margin: 0;
    text-align: center;
  }

  .image-btn {
    border: none;
    background: none;
    cursor: pointer;
    padding: 0;
    border-radius: 50%;
    transition: transform 0.3s ease;
    width: 120px;
    height: 120px;
    display: flex;
    justify-content: center;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    position: relative;
    overflow: hidden;
  }

  .image-btn:hover:not(:disabled) {
    transform: scale(1.08);
  }

  .image-btn:disabled {
    cursor: wait;
  }

  .image-btn img {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
  }

  .loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #f1f5f9;
    border-top: 3px solid #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .progress-text {
    font-size: 14px;
    font-weight: 600;
    color: #3b82f6;
  }

  .center-hint {
    font-size: 14px;
    color: #64748b;
    margin: 0;
    text-align: center;
    font-weight: 500;
  }

  .file-name {
    font-size: 14px;
    color: #475569;
    margin: 10px 0 0 0;
    text-align: center;
    max-width: 180px;
    word-break: break-word;
    font-weight: 500;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Адаптивность */
  @media (max-width: 768px) {
    .container {
      flex-direction: column;
      gap: 40px;
      padding: 30px;
    }
    
    .center {
      order: -1;
    }
    
    .image-btn {
      width: 100px;
      height: 100px;
    }
    
    .spinner {
      width: 30px;
      height: 30px;
    }
  }
</style>