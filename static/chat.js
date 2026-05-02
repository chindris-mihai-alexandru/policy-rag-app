// Acme Corp Policy Assistant — Chat UI logic

const chatContainer = document.getElementById('chatContainer');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');

// Allow Enter key to send
questionInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuestion();
    }
});

function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    // Disable input while processing
    questionInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message
    addMessage(question, 'user');
    questionInput.value = '';

    // Show typing indicator
    const typingEl = addTypingIndicator();

    // Send to API
    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question }),
    })
    .then(response => response.json())
    .then(data => {
        // Remove typing indicator
        typingEl.remove();

        // Add bot response
        addBotMessage(data.answer, data.sources || [], data.latency_ms || 0);
    })
    .catch(error => {
        typingEl.remove();
        addBotMessage(
            "I'm sorry, I encountered a connection error. Please try again.",
            [],
            0
        );
        console.error('Chat error:', error);
    })
    .finally(() => {
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.focus();
    });
}

function addMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `<p>${escapeHtml(text)}</p>`;

    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function addBotMessage(answer, sources, latencyMs) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Convert markdown-like formatting to HTML
    contentDiv.innerHTML = formatAnswer(answer);

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesHtml = createSourcesHtml(sources);
        contentDiv.innerHTML += sourcesHtml;
    }

    // Add latency badge
    if (latencyMs > 0) {
        const latencyStr = latencyMs >= 1000
            ? `${(latencyMs / 1000).toFixed(1)}s`
            : `${latencyMs}ms`;
        contentDiv.innerHTML += `<span class="latency-badge">⚡ ${latencyStr}</span>`;
    }

    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function addTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';
    msgDiv.id = 'typing-indicator';

    msgDiv.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;

    chatContainer.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function createSourcesHtml(sources) {
    let html = '<div class="sources-section"><details><summary>📚 Sources (' + sources.length + ')</summary>';
    for (const src of sources) {
        html += `
            <div class="source-item">
                <div class="doc-id">${escapeHtml(src.doc_id || src.file || 'Unknown')}</div>
                <div class="snippet">${escapeHtml(src.snippet || '')}</div>
            </div>
        `;
    }
    html += '</details></div>';
    return html;
}

function formatAnswer(text) {
    if (!text) return '<p>No response received.</p>';

    // Convert markdown-style formatting
    let html = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Inline code
        .replace(/`(.*?)`/g, '<code>$1</code>')
        // Citation brackets — make them stand out
        .replace(/\[([\w\-]+(?:-[\w\-]+)*)\]/g, '<strong class="doc-id">[$1]</strong>')
        // Line breaks to paragraphs
        .split('\n\n').map(p => p.trim()).filter(p => p).map(p => {
            // Check if this is a list
            if (p.match(/^[\-\*]\s/m)) {
                const items = p.split('\n').map(line =>
                    line.replace(/^[\-\*]\s+/, '')
                ).filter(l => l);
                return '<ul>' + items.map(i => `<li>${i}</li>`).join('') + '</ul>';
            }
            if (p.match(/^\d+\.\s/m)) {
                const items = p.split('\n').map(line =>
                    line.replace(/^\d+\.\s+/, '')
                ).filter(l => l);
                return '<ol>' + items.map(i => `<li>${i}</li>`).join('') + '</ol>';
            }
            return `<p>${p.replace(/\n/g, '<br>')}</p>`;
        }).join('');

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
