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

    const channelId = document.getElementById('text-channel-select').value;  // Keep as string
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
                channel_id: channelId,  // Send as string
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

    const accentBar = document.getElementById('preview-accent-bar');
    if (accentBar) accentBar.style.background = color;

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

    const channelId = document.getElementById('embed-channel-select').value;  // Keep as string
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
            channel_id: channelId,  // Send as string
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
