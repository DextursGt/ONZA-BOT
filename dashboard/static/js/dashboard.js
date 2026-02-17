/**
 * ONZA-BOT Dashboard - Main JavaScript
 */

// Global state
const dashboard = {
    botOnline: false,
    selectedChannel: null,
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
    setInterval(updateBotStatus, 5000); // Update every 5 seconds

    // Load channels
    loadChannels();
});

/**
 * Update bot status indicator
 */
async function updateBotStatus() {
    try {
        const response = await fetch('/api/bot/status');
        const data = await response.json();

        const statusElement = document.getElementById('bot-status');
        const statusIcon = statusElement.querySelector('i');

        if (data.online) {
            dashboard.botOnline = true;
            statusIcon.className = 'bi bi-circle-fill text-success';
            statusElement.innerHTML = `<i class="bi bi-circle-fill text-success"></i> Online`;

            // Update stats
            document.getElementById('guild-count').textContent = data.guild_count || '-';
            document.getElementById('latency').textContent = data.latency || '-';
            document.getElementById('bot-user').textContent = data.user || '-';

            // Enable form controls
            enableForms();
        } else {
            dashboard.botOnline = false;
            statusIcon.className = 'bi bi-circle-fill text-danger';
            statusElement.innerHTML = `<i class="bi bi-circle-fill text-danger"></i> Offline`;

            // Disable form controls
            disableForms();
        }
    } catch (error) {
        console.error('Error updating bot status:', error);
    }
}

/**
 * Load channels list
 */
async function loadChannels() {
    const loadingElement = document.getElementById('channels-loading');
    const listElement = document.getElementById('channels-list');

    try {
        const response = await fetch(`/api/channels/${dashboard.guildId}`);
        const data = await response.json();

        dashboard.channels = data.channels || [];

        // Hide loading, show list
        loadingElement.style.display = 'none';
        listElement.style.display = 'block';

        // Populate channels list
        listElement.innerHTML = '';

        let currentCategory = null;
        dashboard.channels.forEach(channel => {
            // Add category header if changed
            if (channel.category !== currentCategory) {
                const categoryHeader = document.createElement('div');
                categoryHeader.className = 'list-group-item list-group-item-secondary py-1 px-2';
                categoryHeader.innerHTML = `<small><strong>${channel.category}</strong></small>`;
                listElement.appendChild(categoryHeader);
                currentCategory = channel.category;
            }

            // Add channel item
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `<i class="bi bi-hash"></i> ${channel.name}`;
            item.dataset.channelId = channel.id;
            item.dataset.channelName = channel.name;

            item.addEventListener('click', function(e) {
                e.preventDefault();
                selectChannel(channel.id, channel.name);
            });

            listElement.appendChild(item);
        });

        // Populate select dropdowns
        populateChannelSelects();

    } catch (error) {
        console.error('Error loading channels:', error);
        loadingElement.innerHTML = '<p class="text-danger">Error cargando canales</p>';
    }
}

/**
 * Populate channel select dropdowns
 */
function populateChannelSelects() {
    const textSelect = document.getElementById('text-channel-select');
    const embedSelect = document.getElementById('embed-channel-select');

    // Clear existing options
    textSelect.innerHTML = '<option value="">Selecciona un canal</option>';
    embedSelect.innerHTML = '<option value="">Selecciona un canal</option>';

    // Add channel options
    dashboard.channels.forEach(channel => {
        const option1 = document.createElement('option');
        option1.value = channel.id;
        option1.textContent = `# ${channel.name}`;
        textSelect.appendChild(option1);

        const option2 = document.createElement('option');
        option2.value = channel.id;
        option2.textContent = `# ${channel.name}`;
        embedSelect.appendChild(option2);
    });

    // Enable selects if bot is online
    if (dashboard.botOnline) {
        textSelect.disabled = false;
        embedSelect.disabled = false;
    }
}

/**
 * Select a channel
 */
function selectChannel(channelId, channelName) {
    dashboard.selectedChannel = { id: channelId, name: channelName };

    // Update active state in list
    document.querySelectorAll('#channels-list a').forEach(item => {
        item.classList.remove('active');
    });
    event.target.classList.add('active');

    console.log('Selected channel:', channelName);
}

/**
 * Enable form controls
 */
function enableForms() {
    document.getElementById('text-channel-select').disabled = false;
    document.getElementById('embed-channel-select').disabled = false;
    document.getElementById('send-text-btn').disabled = false;
    document.getElementById('send-embed-btn').disabled = false;
}

/**
 * Disable form controls
 */
function disableForms() {
    document.getElementById('text-channel-select').disabled = true;
    document.getElementById('embed-channel-select').disabled = true;
    document.getElementById('send-text-btn').disabled = true;
    document.getElementById('send-embed-btn').disabled = true;
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

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}
