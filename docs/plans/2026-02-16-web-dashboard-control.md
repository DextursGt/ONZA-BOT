# ONZA-BOT Web Dashboard Control Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an interactive web dashboard to control the ONZA-BOT Discord bot, allowing message sending, embed creation, and bot management from a browser interface.

**Architecture:** Build a Flask/FastAPI web application that communicates with the running Discord bot via REST API endpoints. The dashboard will have authentication, real-time status monitoring, message composer with embed builder, and administrative controls.

**Tech Stack:** Python FastAPI, HTML/CSS/JavaScript (Bootstrap 5), WebSockets for real-time updates, nextcord bot integration

---

## Phase 1: Backend API Setup

### Task 1: Create FastAPI Application Structure

**Files:**
- Create: `/root/ONZA-BOT/dashboard/app.py`
- Create: `/root/ONZA-BOT/dashboard/__init__.py`
- Create: `/root/ONZA-BOT/dashboard/config.py`
- Create: `/root/ONZA-BOT/requirements-dashboard.txt`

**Step 1: Create dashboard directory**

```bash
mkdir -p /root/ONZA-BOT/dashboard/static/css
mkdir -p /root/ONZA-BOT/dashboard/static/js
mkdir -p /root/ONZA-BOT/dashboard/templates
```

**Step 2: Create requirements file**

Create `/root/ONZA-BOT/requirements-dashboard.txt`:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
aiofiles==23.2.1
```

**Step 3: Install dependencies**

```bash
cd /root/ONZA-BOT
pip3 install -r requirements-dashboard.txt
```

Expected: All packages installed successfully

**Step 4: Create base FastAPI app**

Create `/root/ONZA-BOT/dashboard/app.py`:

```python
"""Web dashboard for ONZA-BOT control."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
from pathlib import Path

# Get dashboard directory
DASHBOARD_DIR = Path(__file__).parent

# Initialize FastAPI app
app = FastAPI(title="ONZA-BOT Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")

# Setup templates
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Render main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ONZA-BOT Dashboard"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 5: Create dashboard config**

Create `/root/ONZA-BOT/dashboard/config.py`:

```python
"""Dashboard configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

# Dashboard settings
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8000))
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change-me-in-production")

# Bot settings (from main .env)
GUILD_ID = int(os.getenv("GUILD_ID", 0))
```

**Step 6: Test basic server**

```bash
cd /root/ONZA-BOT
python3 dashboard/app.py &
sleep 3
curl http://localhost:8000/health
pkill -f "python3 dashboard/app.py"
```

Expected: `{"status":"ok","service":"ONZA-BOT Dashboard"}`

**Step 7: Commit**

```bash
cd /root/ONZA-BOT
git add dashboard/ requirements-dashboard.txt
git commit -m "feat: add FastAPI dashboard structure"
```

---

### Task 2: Create Bot API Integration

**Files:**
- Create: `/root/ONZA-BOT/dashboard/bot_api.py`
- Modify: `/root/ONZA-BOT/main.py` (add API endpoints)

**Step 1: Create bot API client**

Create `/root/ONZA-BOT/dashboard/bot_api.py`:

```python
"""API client to communicate with Discord bot."""
import asyncio
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class BotAPIClient:
    """Client to interact with the running Discord bot."""

    def __init__(self, bot_instance=None):
        """Initialize with optional bot instance."""
        self.bot = bot_instance
        self._channels_cache = {}

    async def get_bot_status(self) -> Dict[str, Any]:
        """Get bot status information."""
        if not self.bot:
            return {"online": False, "error": "Bot not connected"}

        try:
            return {
                "online": True,
                "user": str(self.bot.user) if self.bot.user else "Unknown",
                "guild_count": len(self.bot.guilds),
                "latency": round(self.bot.latency * 1000, 2)  # ms
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {"online": False, "error": str(e)}

    async def get_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get list of channels in a guild."""
        if not self.bot:
            return []

        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return []

            channels = []
            for channel in guild.text_channels:
                channels.append({
                    "id": channel.id,
                    "name": channel.name,
                    "category": channel.category.name if channel.category else "Sin categoría"
                })

            self._channels_cache = {ch["id"]: ch for ch in channels}
            return sorted(channels, key=lambda x: x["name"])

        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []

    async def send_message(self, channel_id: int, content: str) -> Dict[str, Any]:
        """Send a text message to a channel."""
        if not self.bot:
            return {"success": False, "error": "Bot not connected"}

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"success": False, "error": "Canal no encontrado"}

            message = await channel.send(content)
            return {
                "success": True,
                "message_id": message.id,
                "channel": channel.name
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}

    async def send_embed(
        self,
        channel_id: int,
        title: str,
        description: str,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an embed message to a channel."""
        if not self.bot:
            return {"success": False, "error": "Bot not connected"}

        try:
            import nextcord

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {"success": False, "error": "Canal no encontrado"}

            embed = nextcord.Embed(
                title=title,
                description=description,
                color=color or 0x00E5A8
            )

            if fields:
                for field in fields:
                    embed.add_field(
                        name=field.get("name", ""),
                        value=field.get("value", ""),
                        inline=field.get("inline", False)
                    )

            if footer:
                embed.set_footer(text=footer)

            if image_url:
                embed.set_image(url=image_url)

            message = await channel.send(embed=embed)
            return {
                "success": True,
                "message_id": message.id,
                "channel": channel.name
            }

        except Exception as e:
            logger.error(f"Error sending embed: {e}")
            return {"success": False, "error": str(e)}

# Global bot API client instance
bot_api = BotAPIClient()
```

**Step 2: Modify main.py to expose bot instance**

Add to `/root/ONZA-BOT/main.py` after bot initialization (around line 35):

```python
# Import dashboard bot API
from dashboard.bot_api import bot_api

# ... existing bot setup code ...

# In the main() function, after bot is created:
async def main():
    bot = IntegratedONZABot()

    # Connect bot API to bot instance
    bot_api.bot = bot

    # ... rest of existing code ...
```

**Step 3: Add API endpoints to dashboard**

Add to `/root/ONZA-BOT/dashboard/app.py`:

```python
from .bot_api import bot_api
from pydantic import BaseModel

class MessageRequest(BaseModel):
    channel_id: int
    content: str

class EmbedRequest(BaseModel):
    channel_id: int
    title: str
    description: str
    color: Optional[int] = None
    fields: Optional[List[Dict[str, str]]] = None
    footer: Optional[str] = None
    image_url: Optional[str] = None

@app.get("/api/bot/status")
async def get_bot_status():
    """Get bot status."""
    return await bot_api.get_bot_status()

@app.get("/api/channels/{guild_id}")
async def get_channels(guild_id: int):
    """Get list of channels."""
    channels = await bot_api.get_channels(guild_id)
    return {"channels": channels}

@app.post("/api/message/send")
async def send_message(request: MessageRequest):
    """Send a text message."""
    result = await bot_api.send_message(request.channel_id, request.content)
    return result

@app.post("/api/message/embed")
async def send_embed(request: EmbedRequest):
    """Send an embed message."""
    result = await bot_api.send_embed(
        request.channel_id,
        request.title,
        request.description,
        request.color,
        request.fields,
        request.footer,
        request.image_url
    )
    return result
```

**Step 4: Test API endpoints**

```bash
# Start dashboard in background
cd /root/ONZA-BOT
python3 dashboard/app.py &
sleep 3

# Test health endpoint
curl http://localhost:8000/health

# Test bot status
curl http://localhost:8000/api/bot/status

# Stop dashboard
pkill -f "python3 dashboard/app.py"
```

Expected: JSON responses from both endpoints

**Step 5: Commit**

```bash
git add dashboard/bot_api.py dashboard/app.py main.py
git commit -m "feat: add bot API integration for dashboard"
```

---

## Phase 2: Frontend Dashboard

### Task 3: Create Dashboard HTML Template

**Files:**
- Create: `/root/ONZA-BOT/dashboard/templates/index.html`
- Create: `/root/ONZA-BOT/dashboard/templates/base.html`

**Step 1: Create base template**

Create `/root/ONZA-BOT/dashboard/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}ONZA-BOT Dashboard{% endblock %}</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link href="/static/css/dashboard.css" rel="stylesheet">

    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-dark bg-dark navbar-expand-lg">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">
                <i class="bi bi-robot"></i> ONZA-BOT Dashboard
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <span class="nav-link" id="bot-status">
                            <i class="bi bi-circle-fill text-secondary"></i> Conectando...
                        </span>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container-fluid mt-4">
        {% block content %}{% endblock %}
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Custom JS -->
    <script src="/static/js/dashboard.js"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Step 2: Create main dashboard page**

Create `/root/ONZA-BOT/dashboard/templates/index.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="row">
    <!-- Left Sidebar - Channel List -->
    <div class="col-md-3">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <i class="bi bi-list-ul"></i> Canales
            </div>
            <div class="card-body">
                <div id="channels-loading" class="text-center">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span class="ms-2">Cargando...</span>
                </div>
                <div id="channels-list" class="list-group" style="display:none;"></div>
            </div>
        </div>

        <!-- Bot Stats -->
        <div class="card mt-3">
            <div class="card-header bg-info text-white">
                <i class="bi bi-graph-up"></i> Estadísticas
            </div>
            <div class="card-body">
                <div id="bot-stats">
                    <p class="mb-2"><strong>Servidores:</strong> <span id="guild-count">-</span></p>
                    <p class="mb-2"><strong>Latencia:</strong> <span id="latency">-</span> ms</p>
                    <p class="mb-0"><strong>Usuario:</strong> <span id="bot-user">-</span></p>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content - Message Composer -->
    <div class="col-md-9">
        <!-- Tab Navigation -->
        <ul class="nav nav-tabs" id="composerTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="text-tab" data-bs-toggle="tab" data-bs-target="#text-composer" type="button">
                    <i class="bi bi-chat-text"></i> Mensaje de Texto
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="embed-tab" data-bs-toggle="tab" data-bs-target="#embed-composer" type="button">
                    <i class="bi bi-card-text"></i> Mensaje Embed
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content border border-top-0 p-4" id="composerTabsContent">
            <!-- Text Message Composer -->
            <div class="tab-pane fade show active" id="text-composer" role="tabpanel">
                <h5>Enviar Mensaje de Texto</h5>
                <form id="text-message-form">
                    <div class="mb-3">
                        <label for="text-channel-select" class="form-label">Canal de destino</label>
                        <select class="form-select" id="text-channel-select" required disabled>
                            <option value="">Selecciona un canal</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="text-content" class="form-label">Contenido del mensaje</label>
                        <textarea class="form-control" id="text-content" rows="6" required
                                  placeholder="Escribe tu mensaje aquí..."></textarea>
                        <div class="form-text">
                            Caracteres: <span id="char-count">0</span>/2000
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary" id="send-text-btn" disabled>
                        <i class="bi bi-send"></i> Enviar Mensaje
                    </button>
                </form>
            </div>

            <!-- Embed Message Composer -->
            <div class="tab-pane fade" id="embed-composer" role="tabpanel">
                <h5>Crear Mensaje Embed</h5>
                <form id="embed-message-form">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="embed-channel-select" class="form-label">Canal de destino</label>
                                <select class="form-select" id="embed-channel-select" required disabled>
                                    <option value="">Selecciona un canal</option>
                                </select>
                            </div>

                            <div class="mb-3">
                                <label for="embed-title" class="form-label">Título del Embed</label>
                                <input type="text" class="form-control" id="embed-title" required
                                       placeholder="Título principal" maxlength="256">
                            </div>

                            <div class="mb-3">
                                <label for="embed-description" class="form-label">Descripción</label>
                                <textarea class="form-control" id="embed-description" rows="4"
                                          placeholder="Descripción del embed" maxlength="4096"></textarea>
                            </div>

                            <div class="mb-3">
                                <label for="embed-color" class="form-label">Color</label>
                                <div class="input-group">
                                    <input type="color" class="form-control form-control-color" id="embed-color" value="#00e5a8">
                                    <input type="text" class="form-control" id="embed-color-hex" value="#00e5a8" placeholder="#00e5a8">
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="embed-footer" class="form-label">Footer (opcional)</label>
                                <input type="text" class="form-control" id="embed-footer" placeholder="Texto del footer">
                            </div>

                            <div class="mb-3">
                                <label for="embed-image" class="form-label">URL de Imagen (opcional)</label>
                                <input type="url" class="form-control" id="embed-image" placeholder="https://example.com/image.png">
                            </div>
                        </div>

                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Vista Previa</label>
                                <div class="card" id="embed-preview">
                                    <div class="card-body">
                                        <div id="preview-content">
                                            <div class="border-start border-4 ps-3" style="border-color: #00e5a8 !important;">
                                                <h6 class="card-title" id="preview-title">Título del Embed</h6>
                                                <p class="card-text" id="preview-description">Descripción del embed aparecerá aquí...</p>
                                                <img id="preview-image" src="" class="img-fluid mt-2" style="display:none;">
                                                <small class="text-muted d-block mt-2" id="preview-footer"></small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary" id="send-embed-btn" disabled>
                        <i class="bi bi-send"></i> Enviar Embed
                    </button>
                </form>
            </div>
        </div>

        <!-- Status Messages -->
        <div id="alert-container" class="mt-3"></div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="/static/js/composer.js"></script>
{% endblock %}
```

**Step 3: Commit**

```bash
git add dashboard/templates/
git commit -m "feat: add dashboard HTML templates"
```

---

### Task 4: Create Dashboard JavaScript

**Files:**
- Create: `/root/ONZA-BOT/dashboard/static/js/dashboard.js`
- Create: `/root/ONZA-BOT/dashboard/static/js/composer.js`
- Create: `/root/ONZA-BOT/dashboard/static/css/dashboard.css`

**Step 1: Create main dashboard JS**

Create `/root/ONZA-BOT/dashboard/static/js/dashboard.js`:

```javascript
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
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');

    // Get guild ID from config (you'll need to expose this)
    // For now, hardcode or get from API
    dashboard.guildId = 1408125343071736009; // Your GUILD_ID

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
```

**Step 2: Create composer JS**

Create `/root/ONZA-BOT/dashboard/static/js/composer.js`:

```javascript
/**
 * Message Composer JavaScript
 */

// Character counter for text messages
document.getElementById('text-content')?.addEventListener('input', function() {
    const charCount = this.value.length;
    document.getElementById('char-count').textContent = charCount;
});

// Text message form submission
document.getElementById('text-message-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const channelId = parseInt(document.getElementById('text-channel-select').value);
    const content = document.getElementById('text-content').value;

    if (!channelId || !content) {
        showAlert('Por favor completa todos los campos', 'warning');
        return;
    }

    const sendBtn = document.getElementById('send-text-btn');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando...';

    try {
        const response = await fetch('/api/message/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                channel_id: channelId,
                content: content
            })
        });

        const result = await response.json();

        if (result.success) {
            showAlert(`✅ Mensaje enviado a #${result.channel}`, 'success');
            document.getElementById('text-content').value = '';
            document.getElementById('char-count').textContent = '0';
        } else {
            showAlert(`❌ Error: ${result.error}`, 'danger');
        }
    } catch (error) {
        showAlert('❌ Error al enviar mensaje', 'danger');
        console.error(error);
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bi bi-send"></i> Enviar Mensaje';
    }
});

// Embed preview updates
const embedInputs = {
    title: document.getElementById('embed-title'),
    description: document.getElementById('embed-description'),
    color: document.getElementById('embed-color'),
    colorHex: document.getElementById('embed-color-hex'),
    footer: document.getElementById('embed-footer'),
    image: document.getElementById('embed-image')
};

// Update preview on input
Object.values(embedInputs).forEach(input => {
    if (input) {
        input.addEventListener('input', updateEmbedPreview);
    }
});

// Color picker sync
embedInputs.color?.addEventListener('input', function() {
    embedInputs.colorHex.value = this.value;
    updateEmbedPreview();
});

embedInputs.colorHex?.addEventListener('input', function() {
    if (/^#[0-9A-F]{6}$/i.test(this.value)) {
        embedInputs.color.value = this.value;
        updateEmbedPreview();
    }
});

/**
 * Update embed preview
 */
function updateEmbedPreview() {
    const title = embedInputs.title.value || 'Título del Embed';
    const description = embedInputs.description.value || 'Descripción del embed aparecerá aquí...';
    const color = embedInputs.color.value;
    const footer = embedInputs.footer.value;
    const imageUrl = embedInputs.image.value;

    document.getElementById('preview-title').textContent = title;
    document.getElementById('preview-description').textContent = description;
    document.querySelector('#embed-preview .border-start').style.borderColor = color + ' !important';

    const footerElement = document.getElementById('preview-footer');
    if (footer) {
        footerElement.textContent = footer;
        footerElement.style.display = 'block';
    } else {
        footerElement.style.display = 'none';
    }

    const imageElement = document.getElementById('preview-image');
    if (imageUrl && isValidUrl(imageUrl)) {
        imageElement.src = imageUrl;
        imageElement.style.display = 'block';
    } else {
        imageElement.style.display = 'none';
    }
}

/**
 * Validate URL
 */
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

/**
 * Convert hex color to decimal
 */
function hexToDecimal(hex) {
    return parseInt(hex.replace('#', ''), 16);
}

// Embed message form submission
document.getElementById('embed-message-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();

    const channelId = parseInt(document.getElementById('embed-channel-select').value);
    const title = document.getElementById('embed-title').value;
    const description = document.getElementById('embed-description').value;
    const color = hexToDecimal(document.getElementById('embed-color').value);
    const footer = document.getElementById('embed-footer').value;
    const imageUrl = document.getElementById('embed-image').value;

    if (!channelId || !title) {
        showAlert('Por favor completa al menos el canal y el título', 'warning');
        return;
    }

    const sendBtn = document.getElementById('send-embed-btn');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando...';

    try {
        const payload = {
            channel_id: channelId,
            title: title,
            description: description,
            color: color
        };

        if (footer) payload.footer = footer;
        if (imageUrl) payload.image_url = imageUrl;

        const response = await fetch('/api/message/embed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.success) {
            showAlert(`✅ Embed enviado a #${result.channel}`, 'success');
            // Clear form
            document.getElementById('embed-message-form').reset();
            embedInputs.color.value = '#00e5a8';
            embedInputs.colorHex.value = '#00e5a8';
            updateEmbedPreview();
        } else {
            showAlert(`❌ Error: ${result.error}`, 'danger');
        }
    } catch (error) {
        showAlert('❌ Error al enviar embed', 'danger');
        console.error(error);
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bi bi-send"></i> Enviar Embed';
    }
});
```

**Step 3: Create CSS**

Create `/root/ONZA-BOT/dashboard/static/css/dashboard.css`:

```css
/**
 * ONZA-BOT Dashboard Styles
 */

body {
    background-color: #f5f5f5;
}

.navbar-brand {
    font-weight: bold;
}

#channels-list .list-group-item {
    cursor: pointer;
    padding: 0.5rem 0.75rem;
}

#channels-list .list-group-item:hover {
    background-color: #f8f9fa;
}

#channels-list .list-group-item.active {
    background-color: #0d6efd;
    border-color: #0d6efd;
}

#embed-preview {
    background-color: #2f3136;
    color: #dcddde;
}

#embed-preview .border-start {
    padding-left: 1rem !important;
}

#preview-title {
    color: #ffffff;
    font-weight: 600;
}

#preview-description {
    color: #dcddde;
    white-space: pre-wrap;
}

#preview-footer {
    color: #72767d;
    font-size: 0.75rem;
}

.card-header {
    font-weight: 600;
}

textarea {
    font-family: 'Consolas', 'Monaco', monospace;
}
```

**Step 4: Commit**

```bash
git add dashboard/static/
git commit -m "feat: add dashboard JavaScript and CSS"
```

---

## Phase 3: Integration and Deployment

### Task 5: Create Dashboard Startup Script

**Files:**
- Create: `/root/ONZA-BOT/start_dashboard.sh`
- Modify: `/root/ONZA-BOT/.env`

**Step 1: Create startup script**

Create `/root/ONZA-BOT/start_dashboard.sh`:

```bash
#!/bin/bash
# Start ONZA-BOT Dashboard

cd "$(dirname "$0")"

echo "Starting ONZA-BOT Dashboard..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start dashboard with uvicorn
python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

**Step 2: Make executable**

```bash
chmod +x /root/ONZA-BOT/start_dashboard.sh
```

**Step 3: Add dashboard configuration to .env**

Add to `/root/ONZA-BOT/.env`:

```bash
# Dashboard Configuration
DASHBOARD_PORT=8000
DASHBOARD_HOST=0.0.0.0
DASHBOARD_SECRET_KEY=your-secret-key-here
```

**Step 4: Test dashboard startup**

```bash
cd /root/ONZA-BOT
./start_dashboard.sh &
sleep 5
curl http://localhost:8000/health
pkill -f uvicorn
```

Expected: Dashboard starts and health check responds

**Step 5: Create pm2 ecosystem file**

Create `/root/ONZA-BOT/ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'ONZA-BOT',
      script: '/root/ONZA-BOT/main.py',
      interpreter: 'python3',
      cwd: '/root/ONZA-BOT',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M'
    },
    {
      name: 'ONZA-DASHBOARD',
      script: 'uvicorn',
      args: 'dashboard.app:app --host 0.0.0.0 --port 8000',
      interpreter: 'python3',
      cwd: '/root/ONZA-BOT',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M'
    }
  ]
};
```

**Step 6: Start both services with pm2**

```bash
cd /root/ONZA-BOT
pm2 delete all  # Stop existing
pm2 start ecosystem.config.js
pm2 save
```

Expected: Both ONZA-BOT and ONZA-DASHBOARD running

**Step 7: Commit**

```bash
git add start_dashboard.sh ecosystem.config.js .env
git commit -m "feat: add dashboard startup scripts and pm2 config"
```

---

### Task 6: Add Authentication (Optional but Recommended)

**Files:**
- Create: `/root/ONZA-BOT/dashboard/auth.py`
- Modify: `/root/ONZA-BOT/dashboard/app.py`

**Step 1: Add authentication dependencies**

Add to `/root/ONZA-BOT/requirements-dashboard.txt`:

```txt
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

Install:

```bash
pip3 install python-jose[cryptography] passlib[bcrypt]
```

**Step 2: Create simple auth module**

Create `/root/ONZA-BOT/dashboard/auth.py`:

```python
"""Simple authentication for dashboard."""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
import secrets
import os

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Basic Auth
security = HTTPBasic()

# Dashboard credentials (from environment)
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD_HASH = pwd_context.hash(os.getenv("DASHBOARD_PASSWORD", "changeme"))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Authenticate user with HTTP Basic Auth."""
    correct_username = secrets.compare_digest(credentials.username, DASHBOARD_USERNAME)
    correct_password = verify_password(credentials.password, os.getenv("DASHBOARD_PASSWORD", "changeme"))

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

**Step 3: Protect dashboard routes**

Modify `/root/ONZA-BOT/dashboard/app.py`:

```python
from .auth import authenticate_user

# Protect main dashboard page
@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, username: str = Depends(authenticate_user)):
    """Render main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "username": username})

# Protect API endpoints
@app.get("/api/bot/status")
async def get_bot_status(username: str = Depends(authenticate_user)):
    """Get bot status."""
    return await bot_api.get_bot_status()

# ... apply to all other endpoints ...
```

**Step 4: Add credentials to .env**

Add to `/root/ONZA-BOT/.env`:

```bash
# Dashboard Authentication
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=your-secure-password-here
```

**Step 5: Test authentication**

```bash
# Try accessing without auth (should fail)
curl http://localhost:8000/api/bot/status

# Try with auth
curl -u admin:your-secure-password-here http://localhost:8000/api/bot/status
```

**Step 6: Commit**

```bash
git add dashboard/auth.py requirements-dashboard.txt .env
git commit -m "feat: add HTTP Basic Auth to dashboard"
```

---

## Testing and Documentation

### Task 7: Create README and Testing Guide

**Files:**
- Create: `/root/ONZA-BOT/docs/DASHBOARD.md`

**Step 1: Create dashboard documentation**

Create `/root/ONZA-BOT/docs/DASHBOARD.md`:

```markdown
# ONZA-BOT Web Dashboard

## Descripción

Dashboard web interactivo para controlar ONZA-BOT desde el navegador.

## Características

- ✅ **Envío de mensajes de texto** a cualquier canal
- ✅ **Creación de embeds** con vista previa en tiempo real
- ✅ **Monitoreo del bot** (estado, latencia, servidores)
- ✅ **Selección de canales** por categorías
- ✅ **Autenticación HTTP Basic**
- ✅ **Interfaz responsive** con Bootstrap 5

## Instalación

1. Instalar dependencias:
```bash
pip3 install -r requirements-dashboard.txt
```

2. Configurar credenciales en `.env`:
```bash
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=tu-contraseña-segura
DASHBOARD_PORT=8000
```

3. Iniciar con pm2:
```bash
pm2 start ecosystem.config.js
pm2 save
```

## Acceso

Abrir en navegador: `http://tu-servidor-ip:8000`

Credenciales: Las configuradas en `.env`

## Uso

### Enviar Mensaje de Texto

1. Seleccionar canal de destino
2. Escribir mensaje
3. Click en "Enviar Mensaje"

### Crear Embed

1. Ir a pestaña "Mensaje Embed"
2. Seleccionar canal
3. Completar título y descripción
4. Personalizar color, footer, imagen (opcional)
5. Ver vista previa en tiempo real
6. Click en "Enviar Embed"

## API Endpoints

- `GET /health` - Health check
- `GET /api/bot/status` - Estado del bot
- `GET /api/channels/{guild_id}` - Lista de canales
- `POST /api/message/send` - Enviar mensaje de texto
- `POST /api/message/embed` - Enviar embed

## Seguridad

- Autenticación HTTP Basic
- HTTPS recomendado en producción
- No exponer puerto 8000 directamente a internet
- Usar reverse proxy (nginx/traefik)

## Troubleshooting

**Dashboard no carga:**
- Verificar que pm2 está corriendo: `pm2 status`
- Revisar logs: `pm2 logs ONZA-DASHBOARD`

**Bot aparece offline:**
- Verificar que ONZA-BOT está corriendo
- Revisar que main.py importa bot_api

**No se puede enviar mensajes:**
- Verificar permisos del bot en Discord
- Revisar logs del bot: `pm2 logs ONZA-BOT`
```

**Step 2: Update main README**

Add to `/root/ONZA-BOT/README.md`:

```markdown
## 🌐 Web Dashboard

ONZA-BOT incluye un dashboard web para control remoto.

**Características:**
- Envío de mensajes y embeds desde el navegador
- Monitoreo en tiempo real del bot
- Interfaz moderna y responsive

**Iniciar dashboard:**
```bash
pm2 start ecosystem.config.js
```

**Acceso:** `http://localhost:8000`

Ver [docs/DASHBOARD.md](docs/DASHBOARD.md) para más detalles.
```

**Step 3: Commit**

```bash
git add docs/DASHBOARD.md README.md
git commit -m "docs: add dashboard documentation"
```

---

## Post-Implementation Checklist

- [ ] FastAPI app running on port 8000
- [ ] Bot API integration working
- [ ] Can send text messages from dashboard
- [ ] Can send embed messages from dashboard
- [ ] Embed preview updates in real-time
- [ ] Channel list loads correctly
- [ ] Bot status updates every 5 seconds
- [ ] Authentication working (if enabled)
- [ ] pm2 manages both bot and dashboard
- [ ] Documentation complete

---

**Plan created:** 2026-02-16
**Estimated time:** 3-4 hours (7 tasks × 20-30 min each)
**Risk level:** Medium (new feature, requires testing)
**Dependencies:** ONZA-BOT must be running
