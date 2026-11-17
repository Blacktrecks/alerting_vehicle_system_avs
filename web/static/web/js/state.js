document.addEventListener('DOMContentLoaded', () => {
  const clockEl = document.getElementById('clock');
  const modeToggle = document.getElementById('mode-toggle');
  const modeToggleLabel = document.getElementById('mode-toggle-label');
  const themeToggle = document.getElementById('theme-toggle');
  const stateDataEl = document.getElementById('state-data');
  const liveState = stateDataEl ? JSON.parse(stateDataEl.textContent) : {};

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  const getCookie = (name) => {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const applyTheme = (theme) => {
    const resolved = theme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', resolved);
    document.body.setAttribute('data-theme', resolved);
    if (themeToggle) {
      themeToggle.textContent = resolved === 'dark' ? '☀️' : '🌙';
      themeToggle.setAttribute('aria-label', resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }
    try {
      window.localStorage.setItem('proximity-theme', resolved);
    } catch (error) {
      console.warn('Theme storage unavailable:', error);
    }
  };

  const savedTheme = (() => {
    try {
      return window.localStorage.getItem('proximity-theme') || 'dark';
    } catch (error) {
      return 'dark';
    }
  })();
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  const updateClock = () => {
    if (clockEl) clockEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isHardware = (mode) => ['hardware', 'real', 'hw'].includes(String(mode || '').toLowerCase());

  const updateModeDisplay = (mode) => {
    const hardware = isHardware(mode);
    if (modeToggle) modeToggle.classList.toggle('is-hardware', hardware);
    if (modeToggleLabel) modeToggleLabel.textContent = hardware ? 'HARDWARE' : 'SIMULATION';
    setText('mode-value', hardware ? 'Hardware' : 'Simulation');
  };

  const setChip = (id, label, text, tone) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = `${label}: ${text}`;
    el.className = `status-chip ${tone}`;
  };

  const renderAlert = (alert) => {
    const pill = document.getElementById('alert-state');
    const panel = document.getElementById('alert-panel');
    const message = document.getElementById('alert-message');
    const active = Boolean(alert && alert.active);
    if (pill) {
      pill.className = `pill-text ${active ? 'error' : 'neutral'}`;
      pill.textContent = active ? 'Alert' : 'Clear';
    }
    if (panel) panel.classList.toggle('hidden', !active);
    if (message && active) message.textContent = `Remote ${alert.type || 'alert'} from ${alert.source || 'unknown'}`;
    setText('source-value', active ? (alert.source || '--') : '--');
    setText('type-value', active ? (alert.type || '--') : '--');
    setText('expires-value', active && alert.expires_in_s != null ? `${Number(alert.expires_in_s).toFixed(0)} s` : '-- s');
  };

  const applyState = (state) => {
    if (!state) return;
    const outputs = state.outputs || {};
    const links = state.links || {};
    const zigbee = (links.zigbee || {}).state || 'unknown';
    const mesh = (links.meshtastic || {}).state || 'unknown';
    const tone = (value) => (value === 'ok' || value === 'connected' ? 'ok' : 'warn');

    updateModeDisplay(state.mode);
    renderAlert(state.alert);
    setText('buzzer-value', outputs.buzzer ? 'ON' : 'OFF');
    setText('led-value', outputs.led ? 'ON' : 'OFF');
    setText('zigbee-value', zigbee.toUpperCase());
    setText('meshtastic-value', mesh.toUpperCase());
    setChip('chip-zigbee', 'Zigbee', zigbee.toUpperCase(), tone(zigbee));
    setChip('chip-meshtastic', 'LoRa Meshtastic', mesh.toUpperCase(), tone(mesh));
    setChip('chip-outputs', 'Buzzer/LED', outputs.buzzer || outputs.led ? 'ACTIVE' : 'OFF', outputs.buzzer || outputs.led ? 'error' : 'ok');
  };

  if (modeToggle) {
    modeToggle.addEventListener('click', async () => {
      const current = modeToggleLabel && modeToggleLabel.textContent.toLowerCase().includes('hardware') ? 'hardware' : 'simulation';
      const next = current === 'hardware' ? 'simulation' : 'hardware';
      const csrfToken = getCookie('csrftoken');
      try {
        const response = await fetch('/api/mode/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}) },
          body: JSON.stringify({ mode: next }),
        });
        if (!response.ok) throw new Error('Mode switch failed');
        const payload = await response.json();
        applyState(payload.state);
      } catch (error) {
        console.warn('Mode switch failed:', error);
      }
    });
  }

  const refreshFromApi = async () => {
    try {
      const response = await fetch('/api/state/');
      if (!response.ok) return;
      applyState(await response.json());
    } catch (error) {
      console.warn('State fetch failed:', error);
    }
  };

  updateClock();
  setInterval(updateClock, 30 * 1000);
  if (Object.keys(liveState).length) {
    applyState(liveState);
  } else {
    refreshFromApi();
  }
  window.setInterval(refreshFromApi, 2500);
});
