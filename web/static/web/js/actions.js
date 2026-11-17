document.addEventListener('DOMContentLoaded', () => {
  const resultEl = document.getElementById('action-result');

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  document.querySelectorAll('[data-api-post]').forEach((button) => {
    button.addEventListener('click', async () => {
      const url = button.getAttribute('data-api-post');
      const showLog = button.hasAttribute('data-show-log');
      const csrfToken = getCookie('csrftoken');
      button.disabled = true;
      if (resultEl) resultEl.textContent = 'Running...';
      try {
        const response = await fetch(url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}) },
          body: '{}',
        });
        const payload = await response.json().catch(() => ({}));
        if (!resultEl) return;
        if (!response.ok) {
          resultEl.textContent = `Error ${response.status}: ${payload.error || 'request failed'}`;
        } else if (showLog) {
          const verdict = payload.ok ? 'PASS' : 'FAIL';
          resultEl.textContent = `${verdict}: ${payload.tests_run} tests, ${payload.failures} failures, ${payload.errors} errors, ${payload.skipped} skipped\n\n${payload.log || ''}`;
        } else {
          resultEl.textContent = 'OK';
        }
      } catch (error) {
        if (resultEl) resultEl.textContent = `Request failed: ${error}`;
      } finally {
        button.disabled = false;
      }
    });
  });
});
