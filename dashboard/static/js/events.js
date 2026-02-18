/**
 * Events Configuration JavaScript
 * Depends on dashboard.js (loaded first) for: dashboard.guildId, loadChannels(), populateChannelSelects(), showAlert()
 */

// Initialize events page
document.addEventListener('DOMContentLoaded', async function() {
    // Wait for dashboard.js to load guild ID (it runs on same event)
    // Use a small delay to ensure dashboard.js DOMContentLoaded runs first
    await new Promise(r => setTimeout(r, 100));

    // Use guildId from dashboard.js global
    const guildId = dashboard.guildId;
    if (!guildId) {
        console.error('Guild ID not available from dashboard.js');
        return;
    }

    // Load all configs
    await loadJoinConfig(guildId);
    await loadLeaveConfig(guildId);
    await loadJoinDMConfig(guildId);
    await loadInviteStats(guildId);

    // Setup form handlers
    setupFormHandlers(guildId);
});

/**
 * Load join configuration
 */
async function loadJoinConfig(guildId) {
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
 * Load leave configuration
 */
async function loadLeaveConfig(guildId) {
    try {
        const response = await fetch(`/api/events/leave/${guildId}`);
        const config = await response.json();
        if (config.guild_id) {
            document.getElementById('leave-enabled').checked = config.enabled;
            document.getElementById('leave-channel').value = config.channel_id || '';
            document.getElementById('leave-message').value = config.message_template || '';
        }
    } catch (error) {
        console.error('Error loading leave config:', error);
    }
}

/**
 * Load join DM configuration
 */
async function loadJoinDMConfig(guildId) {
    try {
        const response = await fetch(`/api/events/join-dm/${guildId}`);
        const config = await response.json();
        if (config.guild_id) {
            document.getElementById('joindm-enabled').checked = config.enabled;
            document.getElementById('joindm-message').value = config.message_template || '';
        }
    } catch (error) {
        console.error('Error loading join DM config:', error);
    }
}

/**
 * Load invite statistics and leaderboard
 */
async function loadInviteStats(guildId) {
    // Use dashboard global if no param (for onclick in HTML)
    guildId = guildId || dashboard.guildId;

    try {
        const [statsRes, leaderRes] = await Promise.all([
            fetch(`/api/events/invites/${guildId}/stats`),
            fetch(`/api/events/invites/${guildId}/leaderboard?limit=10`)
        ]);

        if (statsRes.ok) {
            const stats = await statsRes.json();
            document.getElementById('stat-total-invites').textContent = stats.total_invites ?? 0;
            document.getElementById('stat-total-uses').textContent = stats.total_uses ?? 0;
        }

        if (leaderRes.ok) {
            const data = await leaderRes.json();
            const tbody = document.getElementById('invite-leaderboard');
            if (data.leaderboard && data.leaderboard.length > 0) {
                tbody.innerHTML = data.leaderboard.map((entry, i) => `
                    <tr>
                        <td>${i + 1}</td>
                        <td><code>${entry.user_id}</code></td>
                        <td><span class="badge bg-warning">${entry.total_points} pts</span></td>
                    </tr>
                `).join('');
                if (data.leaderboard[0]) {
                    document.getElementById('stat-top-inviter').textContent =
                        `${data.leaderboard[0].total_points} pts`;
                }
            } else {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center">No data yet</td></tr>';
            }
        }
    } catch (error) {
        console.error('Error loading invite stats:', error);
    }
}

/**
 * Setup form handlers
 */
function setupFormHandlers(guildId) {
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
                showAlert('Configuration saved successfully', 'success');
            } else {
                showAlert(`Error: ${result.detail || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert('Error saving configuration', 'danger');
            console.error(error);
        }
    });

    // Toggle join enabled
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

    // Leave config form
    document.getElementById('leave-config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            guild_id: guildId,
            enabled: document.getElementById('leave-enabled').checked,
            channel_id: document.getElementById('leave-channel').value,
            message_template: document.getElementById('leave-message').value
        };
        try {
            const response = await fetch('/api/events/leave/configure', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (response.ok) {
                showAlert('Leave config saved', 'success');
            } else {
                showAlert(`Error: ${result.detail || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert('Error saving leave config', 'danger');
        }
    });

    // Join DM config form
    document.getElementById('joindm-config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            guild_id: guildId,
            enabled: document.getElementById('joindm-enabled').checked,
            message_template: document.getElementById('joindm-message').value
        };
        try {
            const response = await fetch('/api/events/join-dm/configure', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (response.ok) {
                showAlert('Join DM config saved', 'success');
            } else {
                showAlert(`Error: ${result.detail || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert('Error saving join DM config', 'danger');
        }
    });
}
