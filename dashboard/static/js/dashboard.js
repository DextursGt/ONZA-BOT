/**
 * ONZA-BOT Dashboard - Main JavaScript
 */

// Global state
const dashboard = {
    botOnline: false,
    channels: [],
    guildId: null
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Dashboard initializing...');

    // Get guild ID from server config
    try {
        const configResponse = await fetch('/api/config');
        const config = await configResponse.json();
        dashboard.guildId = config.guild_id;
        console.log('Guild ID loaded:', dashboard.guildId);
    } catch (error) {
        console.error('Error loading config:', error);
        dashboard.guildId = 1408125343071736009; // Fallback
    }

    // Start status polling
    updateBotStatus();
    setInterval(updateBotStatus, 5000);

    // Load channels into dropdowns
    loadChannels();
});

/**
 * Update bot status indicator
 */
async function updateBotStatus() {
    try {
        const response = await fetch('/api/bot/status');
        const data = await response.json();

        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        const block = document.getElementById('bot-status-block');

        if (data.online) {
            dashboard.botOnline = true;
            dot.className = 'status-dot online';
            text.textContent = 'ONLINE';
            block.classList.add('online');
            block.classList.remove('offline');

            // Update stats
            const gc = document.getElementById('guild-count');
            const lat = document.getElementById('latency');
            const bu = document.getElementById('bot-user');
            if (gc) gc.textContent = data.guild_count || '---';
            if (lat) lat.textContent = (data.latency || '---') + ' ms';
            if (bu) bu.textContent = data.user || '---';

            enableForms();
        } else {
            dashboard.botOnline = false;
            dot.className = 'status-dot offline';
            text.textContent = 'OFFLINE';
            block.classList.remove('online');
            block.classList.add('offline');

            disableForms();
        }
    } catch (error) {
        console.error('Error updating bot status:', error);
    }
}

/**
 * Load channels into select dropdowns only
 */
async function loadChannels() {
    try {
        const response = await fetch(`/api/channels/${dashboard.guildId}`);
        const data = await response.json();

        dashboard.channels = data.channels || [];
        populateChannelSelects();
    } catch (error) {
        console.error('Error loading channels:', error);
    }
}

/**
 * Populate channel select dropdowns
 */
function populateChannelSelects() {
    const selects = document.querySelectorAll('select[id$="-channel-select"], select[id$="-channel"]');

    selects.forEach(select => {
        const firstOption = select.querySelector('option');
        const defaultText = firstOption ? firstOption.textContent : '// Selecciona un canal';
        select.innerHTML = `<option value="">${defaultText}</option>`;

        dashboard.channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.id;
            option.textContent = `# ${channel.name}`;
            select.appendChild(option);
        });

        if (dashboard.botOnline) {
            select.disabled = false;
        }
    });
}

/**
 * Enable form controls
 */
function enableForms() {
    document.querySelectorAll('select[id$="-channel-select"], select[id$="-channel"]').forEach(s => s.disabled = false);
    document.querySelectorAll('.btn-cyber[type="submit"]').forEach(b => b.disabled = false);

    const badge = document.getElementById('text-status-badge');
    if (badge) {
        badge.innerHTML = '<i class="bi bi-shield-check"></i> Bot online';
        badge.classList.add('online');
    }
}

/**
 * Disable form controls
 */
function disableForms() {
    document.querySelectorAll('select[id$="-channel-select"]').forEach(s => s.disabled = true);
    document.querySelectorAll('.btn-cyber[type="submit"]').forEach(b => b.disabled = true);

    const badge = document.getElementById('text-status-badge');
    if (badge) {
        badge.innerHTML = '<i class="bi bi-shield-lock"></i> Esperando bot...';
        badge.classList.remove('online');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}
