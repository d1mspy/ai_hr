<script lang="ts">
  type UIResult = {
    id: number;
    fileName: string;
    verdict: 'собеседование' | 'отказ';
    comment: string; // ссылка-заглушка или причины
    score: number;   // 0..100
  };

  let results: UIResult[] = [];

  // Загружаем, если пусто — оставим [] (таблица просто будет пустой)
  const loadResults = () => {
    try {
      const raw = sessionStorage.getItem('aihr_results');
      results = raw ? (JSON.parse(raw) as UIResult[]) : [];
    } catch {
      results = [];
    }
  };

  loadResults();

  const copyToClipboard = (text: string): void => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Ссылка скопирована в буфер обмена');
    });
  };

  const goBack = (): void => {
    window.location.href = '/';
  };
</script>


<svelte:head>
  <title>Результаты анализа - AI-HR</title>
</svelte:head>

<div class="container">
  <div class="header">
    <h1 class="title">Результаты анализа резюме</h1>
    <p class="subtitle">AI-powered анализ соответствия вакансии</p>
  </div>

  <div class="table-container">
    <table class="results-table">
      <thead>
        <tr>
          <th class="file-column">Резюме</th>
          <th class="verdict-column">Вердикт</th>
          <th class="comment-column">Комментарий / Ссылка</th>
          <th class="score-column">Совпадение</th>
        </tr>
      </thead>
      <tbody>
        {#each results as result}
          <tr class="result-row">
            <td class="file-name">
              <div class="file-info">
                <span class="file-icon">📄</span>
                {result.fileName}
              </div>
            </td>
            
            <td class="verdict">
              <span class:verdict-badge={true} class:approved={result.verdict === 'собеседование'} class:rejected={result.verdict === 'отказ'}>
                {result.verdict}
              </span>
            </td>
            
            <td class="comment">
              {#if result.verdict === 'собеседование'}
                <a href={result.comment} target="_blank" class="interview-link">
                  {result.comment}
                </a>
                <button on:click={() => copyToClipboard(result.comment)} class="copy-btn" title="Скопировать ссылку">
                  <img class="copy-linl-img" src="/copy-icon.png" alt="copy link">
                </button>
              {:else}
                <span class="rejection-reason">{result.comment}</span>
              {/if}
            </td>
            
            <td class="score">
              <div class="score-container">
                <div class="score-bar">
                  <div 
                    class="score-fill" 
                    class:high-score={result.score >= 70}
                    class:medium-score={result.score >= 40 && result.score < 70}
                    class:low-score={result.score < 40}
                    style={`width: ${result.score}%`}
                  ></div>
                </div>
                <span class="score-text">{result.score}%</span>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <div class="footer">
    <button on:click={goBack} class="back-btn">
      ← Назад к загрузке
    </button>
    <p class="stats">Проанализировано резюме: {results.length}</p>
  </div>
</div>

<style>
  :global(body) {
    padding: 20px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    min-height: 100vh;
    box-sizing: border-box;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 24px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    padding: 40px;
    margin-top: 20px;
    margin-bottom: 20px;
  }

  .header {
    text-align: center;
    margin-bottom: 40px;
  }

  .title {
    font-size: 32px;
    font-weight: 700;
    color: #2d3748;
    margin: 0 0 10px 0;
  }

  .subtitle {
    font-size: 16px;
    color: #64748b;
    margin: 0;
  }

  .table-container {
    overflow-x: auto;
    margin-bottom: 30px;
  }

  .results-table {
    width: 100%;
    border-collapse: collapse;
    border-radius: 12px;
    overflow: hidden;
  }

  th {
    background: #f8fafc;
    padding: 16px;
    text-align: left;
    font-weight: 600;
    color: #475569;
    border-bottom: 2px solid #e2e8f0;
  }

  td {
    padding: 20px 16px;
    border-bottom: 1px solid #f1f5f9;
  }

  .result-row:hover {
    background: #fafafa;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 500;
    color: #374151;
  }

  .file-icon {
    font-size: 18px;
  }

  .copy-linl-img {
    height: 0.9rem;
    width: 0.9rem;
  }

  .verdict-badge {
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .approved {
    background: #dcfce7;
    color: #166534;
  }

  .rejected {
    background: #fee2e2;
    color: #991b1b;
  }

  .interview-link {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.3s ease;
  }

  .interview-link:hover {
    color: #1d4ed8;
    text-decoration: underline;
  }

  .rejection-reason {
    color: #6b7280;
    font-style: italic;
  }

  .copy-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 5px;
    margin-left: 10px;
    border-radius: 4px;
    transition: background 0.3s ease;
  }

  .copy-btn:hover {
    background: #f3f4f6;
  }

  .score-container {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .score-bar {
    width: 80px;
    height: 8px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
  }

  .score-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .high-score {
    background: #10b981;
  }

  .medium-score {
    background: #f59e0b;
  }

  .low-score {
    background: #ef4444;
  }

  .score-text {
    font-weight: 600;
    color: #374151;
    min-width: 40px;
  }

  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 20px;
    border-top: 1px solid #e5e7eb;
  }

  .back-btn {
    padding: 12px 24px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.3s ease;
  }

  .back-btn:hover {
    background: #2563eb;
  }

  .stats {
    color: #6b7280;
    font-size: 14px;
    margin: 0;
  }

  /* Адаптивность */
  @media (max-width: 768px) {
    .container {
      padding: 20px;
      margin: 10px;
    }
    
    .title {
      font-size: 24px;
    }
    
    th, td {
      padding: 12px 8px;
    }
    
    .file-info {
      flex-direction: column;
      align-items: flex-start;
      gap: 5px;
    }
    
    .footer {
      flex-direction: column;
      gap: 15px;
      text-align: center;
    }
    
    .score-container {
      flex-direction: column;
      gap: 5px;
    }
  }
</style>