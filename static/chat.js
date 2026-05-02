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
    let html = '<div class="sources-section"><div class="sources-chips">';
    for (const src of sources) {
        const docId = src.doc_id || src.file || 'Unknown';
        const file = src.file || (docId + '.pdf');
        const label = docId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        html += `<a class="source-chip" href="/docs/${encodeURIComponent(file)}" target="_blank" title="${escapeHtml(src.snippet || '')}">📄 ${escapeHtml(label)}</a>`;
    }
    html += '</div></div>';
    return html;
}

function formatAnswer(text) {
    if (!text) return '<p>No response received.</p>';
    // Use marked.js for full markdown rendering (tables, headers, lists, bold, etc.)
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    // Fallback: basic paragraph rendering
    return '<p>' + escapeHtml(text).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
