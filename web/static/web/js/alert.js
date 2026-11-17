document.addEventListener('DOMContentLoaded', () => {
  const ackButton = document.getElementById('alert-confirm');
  const emergencyButton = document.getElementById('emergency-off');
  const toastContainer = document.getElementById('toast-container');

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const post = (url) => fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  });

  const showToast = (message, tone = 'info') => {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${tone}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 2200);
  };

  if (ackButton) {
    ackButton.addEventListener('click', async () => {
      try {
        const response = await post('/api/alert/ack/');
        if (!response.ok) throw new Error('request failed');
        showToast('Alert acknowledged', 'success');
      } catch (error) {
        showToast('Could not acknowledge the alert', 'error');
      }
    });
  }

  if (emergencyButton) {
    emergencyButton.addEventListener('click', async () => {
      try {
        const response = await post('/api/sim/stop/');
        if (!response.ok) throw new Error('request failed');
        showToast('Outputs switched off and alert cleared', 'warning');
      } catch (error) {
        showToast('Emergency stop failed', 'error');
      }
    });
  }
});
