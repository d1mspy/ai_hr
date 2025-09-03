<script lang="ts">
	let inputValue = '';
	let responseText = '';

	async function sendPost() {
		try {
			const res = await fetch('/api/test', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ string: inputValue })
			});
			const json = await res.json();
			responseText = JSON.stringify(json);
		} catch (err) {
			responseText = 'Ошибка при POST-запросе';
		}
	}

	async function sendGet() {
		try {
			const res = await fetch('/api/test');
			const json = await res.json();
			responseText = JSON.stringify(json);
		} catch (err) {
			responseText = 'Ошибка при GET-запросе';
		}
	}
</script>

<div style="display: flex; gap: 0.5rem; align-items: center;">
	<input bind:value={inputValue} placeholder="Введите что-нибудь" />
	<button on:click={sendPost}>Post</button>
</div>

<div style="margin-top: 1rem;">
	<button on:click={sendGet}>Get</button>
	<p>Ответ: {responseText}</p>
</div>
