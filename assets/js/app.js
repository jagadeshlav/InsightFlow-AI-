/**
 * InsightFlow AI — App JavaScript
 * Handles: config panel, file upload, provider/model logic, chat interface.
 */

// ─── State ───────────────────────────────────────────────────────────────────

const state = {
    sessionId: null,
    sampleId: null,
    filename: null,
    chunkCount: 0,
    provider: 'tokenrouter',
    model: 'qwen/qwen3.8-max-free',
    apiKey: '',
    chatMessages: [],
    isLoading: false,
    mode: null, // 'upload' or 'sample'
};

// ─── DOM Elements ────────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const configPanel = $('#configPanel');
const chatPanel = $('#chatPanel');
const uploadZone = $('#uploadZone');
const fileInput = $('#fileInput');
const providerOptions = $$('.provider-option');
const modelSelect = $('#modelSelect');
const apiKeyInput = $('#apiKeyInput');
const keyHint = $('#keyHint');
const startChatBtn = $('#startChatBtn');
const statusMessage = $('#statusMessage');
const sampleCards = $$('.sample-card:not(.coming-soon)');

// ─── Provider / Model Logic ──────────────────────────────────────────────────

function updateProviderUI(provider) {
    state.provider = provider;

    // Update active state
    providerOptions.forEach(opt => {
        opt.classList.toggle('active', opt.dataset.provider === provider);
    });

    // Update model dropdown
    const providerConfig = CONFIG.PROVIDERS[provider];
    modelSelect.innerHTML = '';
    providerConfig.models.forEach(m => {
        const option = document.createElement('option');
        option.value = m.id;
        option.textContent = m.name;
        modelSelect.appendChild(option);
    });

    if (providerConfig.allowsCustom) {
        const customOpt = document.createElement('option');
        customOpt.value = '__custom__';
        customOpt.textContent = '+ Custom model...';
        modelSelect.appendChild(customOpt);
    }

    // Update API key hint
    keyHint.textContent = '💡 ' + providerConfig.hint;
    keyHint.className = 'config-hint' + (providerConfig.requiresKey ? '' : ' success');

    // Update state
    state.model = providerConfig.models[0].id;
}

providerOptions.forEach(opt => {
    opt.addEventListener('click', () => updateProviderUI(opt.dataset.provider));
});

modelSelect.addEventListener('change', () => {
    if (modelSelect.value === '__custom__') {
        const custom = prompt('Enter custom model name (e.g., "org/model-name"):');
        if (custom && custom.trim()) {
            const opt = document.createElement('option');
            opt.value = custom.trim();
            opt.textContent = custom.trim();
            modelSelect.insertBefore(opt, modelSelect.lastChild);
            modelSelect.value = custom.trim();
            state.model = custom.trim();
        } else {
            modelSelect.value = state.model;
        }
    } else {
        state.model = modelSelect.value;
    }
});

apiKeyInput.addEventListener('input', () => {
    state.apiKey = apiKeyInput.value.trim();
});

// ─── Sample Card Selection ───────────────────────────────────────────────────

sampleCards.forEach(card => {
    card.addEventListener('click', () => {
        const sampleId = card.dataset.sample;
        if (!sampleId) return;

        // Toggle selection
        sampleCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');

        state.mode = 'sample';
        state.sampleId = sampleId;
        state.sessionId = null;

        // Reset upload state
        resetUploadZone();

        // Enable start button
        startChatBtn.disabled = false;
        showStatus('success', `✅ Sample "${card.querySelector('.title').textContent}" selected. Click "Start Chat"!`);
    });
});

// ─── File Upload ─────────────────────────────────────────────────────────────

uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFileUpload(file);
});

async function handleFileUpload(file) {
    // Client-side validation
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!CONFIG.SUPPORTED_EXTENSIONS.includes(ext)) {
        showStatus('error', `❌ Unsupported file type. Please upload PDF, TXT, or DOCX.`);
        return;
    }
    if (file.size > CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024) {
        showStatus('error', `❌ File exceeds ${CONFIG.MAX_FILE_SIZE_MB}MB limit.`);
        return;
    }

    // Clear sample selection
    sampleCards.forEach(c => c.classList.remove('selected'));
    state.sampleId = null;

    // Show uploading state
    showStatus('loading', '<span class="spinner"></span> Uploading and processing document...');
    uploadZone.classList.add('uploaded');
    uploadZone.innerHTML = `
        <div class="upload-info">
            <div class="file-icon">📎</div>
            <div class="details">
                <div class="filename">${file.name}</div>
                <div class="chunks"><span class="spinner"></span> Processing...</div>
            </div>
        </div>
    `;

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Upload failed');
        }

        // Success
        state.mode = 'upload';
        state.sessionId = data.session_id;
        state.filename = data.filename;
        state.chunkCount = data.chunk_count;

        uploadZone.innerHTML = `
            <div class="upload-info">
                <div class="file-icon">✅</div>
                <div class="details">
                    <div class="filename">${data.filename}</div>
                    <div class="chunks">${data.chunk_count} chunks indexed • Ready to chat!</div>
                </div>
            </div>
        `;

        startChatBtn.disabled = false;
        showStatus('success', `✅ Document processed! ${data.chunk_count} chunks indexed. Click "Start Chat"!`);

    } catch (error) {
        resetUploadZone();
        showStatus('error', `❌ ${error.message}`);
    }
}

function resetUploadZone() {
    uploadZone.classList.remove('uploaded', 'drag-over');
    uploadZone.innerHTML = `
        <div class="icon">📄</div>
        <div class="text"><strong>Drop your file here</strong> or click to browse</div>
        <div class="formats">Supports PDF, TXT, DOCX — Max 10MB</div>
        <input type="file" id="fileInput" accept=".pdf,.txt,.docx">
    `;
    // Re-bind file input
    const newInput = uploadZone.querySelector('#fileInput');
    if (newInput) {
        newInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleFileUpload(file);
        });
    }
}

// ─── Start Chat ──────────────────────────────────────────────────────────────

startChatBtn.addEventListener('click', () => {
    if (!state.mode) return;
    showChatPanel();
});

function showChatPanel() {
    configPanel.style.display = 'none';
    chatPanel.style.display = 'block';
    chatPanel.innerHTML = buildChatHTML();
    initChatListeners();
    hideStatus();
}

// ─── Chat Panel HTML (Task 8 will enhance this) ─────────────────────────────

function buildChatHTML() {
    const docInfo = state.mode === 'sample'
        ? `📎 Sample: One Piece Tenglish Story`
        : `📎 Document: ${state.filename} (${state.chunkCount} chunks)`;

    const providerName = CONFIG.PROVIDERS[state.provider].name;

    return `
        <div class="chat-header glass-card" style="padding: 1rem 1.25rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">${docInfo}</div>
                    <div style="margin-top: 0.3rem;">
                        <span class="model-pill">🤖 ${state.model} via ${providerName}</span>
                    </div>
                </div>
                <div class="chat-actions">
                    <button class="btn btn-secondary" id="newDocBtn" aria-label="Upload new document">📄 New Doc</button>
                    <button class="btn btn-secondary" id="changeModelBtn" aria-label="Change AI model">⚙️ Model</button>
                    <button class="btn btn-secondary" id="clearChatBtn" aria-label="Clear chat history">🗑️ Clear</button>
                </div>
            </div>
        </div>
        <div class="chat-messages" id="chatMessages" role="log" aria-live="polite" aria-label="Chat messages" style="min-height: 300px; max-height: 55vh; overflow-y: auto; padding: 0.5rem 0; margin-bottom: 1rem;">
            <div class="ai-welcome">
                <div class="welcome-icon">💬</div>
                <div class="welcome-text">Ask anything about the document!</div>
                <div class="welcome-hint">Your questions will be answered using AI + source citations.</div>
            </div>
        </div>
        <div class="chat-input-bar glass-card" style="padding: 0.75rem; display: flex; gap: 0.5rem; align-items: flex-end;">
            <label for="chatInput" class="sr-only">Type your question</label>
            <textarea id="chatInput" placeholder="Ask a question about the document..." rows="1" aria-label="Question input"
                style="flex: 1; resize: none; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.6rem 1rem; color: var(--text-primary); font-family: inherit; font-size: 0.85rem; line-height: 1.5; max-height: 120px; overflow-y: auto;"
            ></textarea>
            <button class="btn btn-primary" id="sendBtn" aria-label="Send message" style="padding: 0.6rem 1.2rem; flex-shrink: 0;">
                Send ➤
            </button>
        </div>
    `;
}

// ─── Chat Listeners ──────────────────────────────────────────────────────────

function initChatListeners() {
    const chatInput = $('#chatInput');
    const sendBtn = $('#sendBtn');
    const newDocBtn = $('#newDocBtn');
    const changeModelBtn = $('#changeModelBtn');
    const clearChatBtn = $('#clearChatBtn');

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Send on Enter (Shift+Enter for newline)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    // New Document — reset everything, go back to config
    newDocBtn.addEventListener('click', () => {
        state.sessionId = null;
        state.sampleId = null;
        state.mode = null;
        state.chatMessages = [];
        startChatBtn.disabled = true;
        resetUploadZone();
        sampleCards.forEach(c => c.classList.remove('selected'));

        chatPanel.style.display = 'none';
        configPanel.style.display = 'block';
    });

    // Change Model — show a quick model picker modal inline
    changeModelBtn.addEventListener('click', () => {
        const currentProvider = state.provider;
        const providerConfig = CONFIG.PROVIDERS[currentProvider];
        const modelNames = providerConfig.models.map(m => `${m.name} (${m.id})`).join('\n');

        const newModel = prompt(
            `Current: ${state.model}\n\nAvailable models for ${providerConfig.name}:\n${modelNames}\n\nEnter model ID to switch:`,
            state.model
        );

        if (newModel && newModel.trim() && newModel.trim() !== state.model) {
            state.model = newModel.trim();
            // Update the model pill in header
            const pill = chatPanel.querySelector('.model-pill');
            if (pill) {
                pill.textContent = `🤖 ${state.model} via ${providerConfig.name}`;
            }
        }
    });

    // Clear Chat — keep session, clear messages only
    clearChatBtn.addEventListener('click', () => {
        state.chatMessages = [];
        const messagesDiv = $('#chatMessages');
        messagesDiv.innerHTML = `
            <div class="ai-welcome">
                <div class="welcome-icon">💬</div>
                <div class="welcome-text">Chat cleared. Ask a new question!</div>
                <div class="welcome-hint">Same document still loaded — ready for more questions.</div>
            </div>
        `;
    });

    // Focus input on load
    chatInput.focus();
}

// ─── Send Message ────────────────────────────────────────────────────────────

async function sendMessage() {
    const chatInput = $('#chatInput');
    const sendBtn = $('#sendBtn');
    const question = chatInput.value.trim();

    if (!question || state.isLoading) return;

    // Disable input during processing
    state.isLoading = true;
    sendBtn.disabled = true;
    chatInput.disabled = true;

    // Clear welcome and add user message
    const messagesDiv = $('#chatMessages');
    const welcome = messagesDiv.querySelector('.ai-welcome');
    if (welcome) welcome.remove();

    appendMessage('user', question);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show loading
    const loadingId = appendLoading();

    try {
        // Determine endpoint
        let url, body;
        if (state.mode === 'sample') {
            url = `${CONFIG.API_BASE_URL}/api/samples/${state.sampleId}/chat`;
            body = {
                question,
                provider: state.provider,
                model: state.model,
                api_key: state.apiKey || null,
            };
        } else {
            url = `${CONFIG.API_BASE_URL}/api/chat`;
            body = {
                session_id: state.sessionId,
                question,
                provider: state.provider,
                model: state.model,
                api_key: state.apiKey || null,
            };
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await response.json();
        removeLoading(loadingId);

        if (!response.ok) {
            appendMessage('error', data.message || 'Something went wrong. Please try again.');
        } else {
            // Show retrieved chunks (collapsible)
            if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
                appendChunks(data.retrieved_chunks);
            }
            // Typewriter effect for answer
            appendMessageTypewriter('ai', data.answer);
        }

    } catch (error) {
        removeLoading(loadingId);
        if (error.message.includes('Failed to fetch')) {
            appendMessage('error', '⚠️ Cannot reach the server. It may be waking up (free tier cold start ~60s). Please try again.');
        } else {
            appendMessage('error', `❌ ${error.message}`);
        }
    } finally {
        state.isLoading = false;
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}

// ─── Message Rendering ───────────────────────────────────────────────────────

function appendMessage(type, text) {
    const messagesDiv = $('#chatMessages');
    const bubble = document.createElement('div');
    bubble.className = `message message-${type}`;
    bubble.style.cssText = type === 'user'
        ? 'text-align: right; margin: 0.75rem 0;'
        : 'text-align: left; margin: 0.75rem 0;';

    const inner = document.createElement('div');
    inner.className = 'bubble';

    if (type === 'user') {
        inner.style.cssText = 'display: inline-block; max-width: 80%; padding: 0.7rem 1rem; border-radius: 12px 12px 2px 12px; background: rgba(108, 92, 231, 0.12); border: 1px solid rgba(108, 92, 231, 0.2); font-size: 0.85rem; text-align: left; word-wrap: break-word;';
    } else if (type === 'error') {
        inner.style.cssText = 'display: inline-block; max-width: 85%; padding: 0.7rem 1rem; border-radius: 12px 12px 12px 2px; background: rgba(231, 76, 60, 0.08); border: 1px solid rgba(231, 76, 60, 0.2); font-size: 0.85rem; color: #e74c3c; word-wrap: break-word;';
    } else {
        inner.style.cssText = 'display: inline-block; max-width: 85%; padding: 0.7rem 1rem; border-radius: 12px 12px 12px 2px; background: var(--bg-card); border: 1px solid var(--border-subtle); font-size: 0.85rem; line-height: 1.7; word-wrap: break-word;';
    }

    inner.textContent = text;
    bubble.appendChild(inner);
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function appendMessageTypewriter(type, text) {
    const messagesDiv = $('#chatMessages');
    const bubble = document.createElement('div');
    bubble.className = `message message-${type}`;
    bubble.style.cssText = 'text-align: left; margin: 0.75rem 0;';

    const inner = document.createElement('div');
    inner.className = 'bubble typewriter-cursor';
    inner.style.cssText = 'display: inline-block; max-width: 85%; padding: 0.7rem 1rem; border-radius: 12px 12px 12px 2px; background: var(--bg-card); border: 1px solid var(--border-subtle); font-size: 0.85rem; line-height: 1.7; word-wrap: break-word;';

    bubble.appendChild(inner);
    messagesDiv.appendChild(bubble);

    // Typewriter effect — word by word with cursor
    const words = text.split(' ');
    let i = 0;
    const interval = setInterval(() => {
        if (i < words.length) {
            inner.textContent += (i === 0 ? '' : ' ') + words[i];
            i++;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } else {
            clearInterval(interval);
            // Remove cursor after typing done
            inner.classList.remove('typewriter-cursor');
        }
    }, CONFIG.TYPEWRITER_DELAY_MS);
}

function appendChunks(chunks) {
    const messagesDiv = $('#chatMessages');
    const wrapper = document.createElement('div');
    wrapper.style.cssText = 'margin: 0.5rem 0;';

    const toggle = document.createElement('button');
    toggle.className = 'chunks-toggle';
    toggle.textContent = `📄 ${chunks.length} source chunk(s) retrieved — click to expand`;
    toggle.setAttribute('aria-expanded', 'false');

    const content = document.createElement('div');
    content.style.cssText = 'display: none; margin-top: 0.4rem;';
    content.setAttribute('role', 'region');
    content.setAttribute('aria-label', 'Retrieved source chunks');

    chunks.forEach((chunk, idx) => {
        const chunkDiv = document.createElement('div');
        chunkDiv.className = 'chunk-item';
        chunkDiv.textContent = `[${idx + 1}] ${chunk.content}`;
        content.appendChild(chunkDiv);
    });

    toggle.addEventListener('click', () => {
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        toggle.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
        toggle.textContent = isHidden
            ? `📄 ${chunks.length} source chunk(s) — click to collapse`
            : `📄 ${chunks.length} source chunk(s) retrieved — click to expand`;
    });

    wrapper.appendChild(toggle);
    wrapper.appendChild(content);
    messagesDiv.appendChild(wrapper);
}

function appendLoading() {
    const messagesDiv = $('#chatMessages');
    const id = 'loading-' + Date.now();
    const el = document.createElement('div');
    el.id = id;
    el.style.cssText = 'text-align: left; margin: 0.75rem 0;';
    el.innerHTML = `
        <div style="display: inline-block; padding: 0.7rem 1.2rem; border-radius: 12px 12px 12px 2px; background: var(--bg-card); border: 1px solid var(--border-subtle);">
            <div class="skeleton" style="height: 12px; width: 200px; margin-bottom: 6px;"></div>
            <div class="skeleton" style="height: 12px; width: 150px;"></div>
        </div>
    `;
    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ─── Status Helpers ──────────────────────────────────────────────────────────

function showStatus(type, html) {
    statusMessage.className = `status-message show ${type}`;
    statusMessage.innerHTML = html;
}

function hideStatus() {
    statusMessage.className = 'status-message';
}

// ─── Backend Health Check (cold start detection) ─────────────────────────────

async function checkBackendHealth() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (response.ok) return true;
    } catch (e) { /* ignore */ }
    return false;
}

// ─── Init ────────────────────────────────────────────────────────────────────

(async function init() {
    // Check backend availability
    const isHealthy = await checkBackendHealth();
    if (!isHealthy) {
        showStatus('loading', '<span class="spinner"></span> Backend server waking up (free tier cold start ~60s). You can still configure while it starts...');
        // Retry in background
        const retryInterval = setInterval(async () => {
            const ok = await checkBackendHealth();
            if (ok) {
                clearInterval(retryInterval);
                hideStatus();
            }
        }, 10000);
    }
})();
