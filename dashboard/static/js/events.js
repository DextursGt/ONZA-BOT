/**
 * Events Configuration JavaScript
 */

let guildId = null;

// Initialize
document.addEventListener('DOMContentLoaded', async function() {
    // Get guild ID
    const configResponse = await fetch('/api/config');
    const config = await configResponse.json();
    guildId = config.guild_id;

    // Load channels
    await loadChannels();

    // Load join config
    await loadJoinConfig();

    // Setup form handlers
    setupFormHandlers();
});

/**
 * Load channels into select
 */
async function loadChannels() {
    try {
        const response = await fetch(`/api/channels/${guildId}`);
        const data = await response.json();

        const select = document.getElementById('join-channel');
        select.innerHTML = '<option value="">Select a channel</option>';

        data.channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.id;
            option.textContent = `# ${channel.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading channels:', error);
    }
}

/**
 * Load join configuration
 */
async function loadJoinConfig() {
    try {
        const response = await fetch(`/api/events/join/${guildId}`);
        const config = await response.json();

        if (config.guild_id) {
            document.getElementById('join-enabled').checked = config.enabled;
            document.getElementById('join-channel').value = config.channel_id;
            document.getElementById('join-message').value = config.message_template || '';
            document.getElementById('join-embed').checked = config.embed_enabled;
        }
    } catch (error) {
        console.error('Error loading join config:', error);
    }
}

/**
 * Setup form handlers
 */
function setupFormHandlers() {
    // Join config form
    document.getElementById('join-config-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            guild_id: guildId,
            enabled: document.getElementById('join-enabled').checked,
            channel_id: document.getElementById('join-channel').value,
            message_template: document.getElementById('join-message').value,
            embed_enabled: document.getElementById('join-embed').checked
        };

        try {
            const response = await fetch('/api/events/join/configure', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                showAlert('✅ Configuration saved successfully', 'success');
            } else {
                showAlert(`❌ Error: ${result.detail || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert('❌ Error saving configuration', 'danger');
            console.error(error);
        }
    });

    // Toggle enabled
    document.getElementById('join-enabled').addEventListener('change', async (e) => {
        try {
            const response = await fetch(`/api/events/join/toggle?guild_id=${guildId}&enabled=${e.target.checked}`, {
                method: 'POST'
            });

            if (response.ok) {
                showAlert(`Join messages ${e.target.checked ? 'enabled' : 'disabled'}`, 'info');
            }
        } catch (error) {
            console.error('Error toggling:', error);
        }
    });
}

/**
 * Show alert
 */
function showAlert(message, type) {
    const container = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    setTimeout(() => alert.remove(), 5000);
}
