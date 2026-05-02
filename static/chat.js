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

function useSuggested(question) {
    questionInput.value = question;
    sendQuestion();
}

async function sendQuestion(retryQuestion = null) {
    const question = retryQuestion || questionInput.value.trim();
    if (!question) return;

    // Disable input while processing
    questionInput.disabled = true;
    sendBtn.disabled = true;

    if (!retryQuestion) {
        addMessage(question, 'user');
        questionInput.value = '';
    }

    // Show skeleton loading indicator
    const msgDiv = addBotMessageSkeleton();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question }),
        });

        if (!response.ok) throw new Error('Network response was not ok');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let isFirstChunk = true;
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep the last incomplete chunk in the buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (!dataStr) continue;
                    
                    try {
                        const data = JSON.parse(dataStr);
                        
                        if (isFirstChunk && data.chunk) {
                            removeSkeleton(msgDiv);
                            isFirstChunk = false;
                        }

                        if (data.chunk) {
                            fullText += data.chunk;
                            updateBotMessage(msgDiv, fullText);
                        }
                        
                        if (data.done) {
                            if (data.sources && data.sources.length > 0) {
                                appendSources(msgDiv, data.sources);
                            }
                            if (data.error) {
                                appendError(msgDiv, data.error, question);
                            } else {
                                addCopyButton(msgDiv, fullText);
                            }
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e, dataStr);
                    }
                }
            }
        }
    } catch (error) {
        removeSkeleton(msgDiv);
        updateBotMessage(msgDiv, "I'm sorry, I encountered a connection error. Please try again.");
        appendError(msgDiv, "Network connection failed.", question);
        console.error('Chat error:', error);
    } finally {
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.focus();
    }
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

function addBotMessageSkeleton() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <div class="status-text">🔍 Searching policies...</div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
    `;
    
    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
    
    // Update status text to simulate reasoning progression
    setTimeout(() => {
        const statusText = msgDiv.querySelector('.status-text');
        if (statusText && statusText.innerHTML.includes('Searching')) {
            statusText.innerHTML = "✍️ Generating answer...";
        }
    }, 2000);

    return msgDiv;
}

function removeSkeleton(msgDiv) {
    const contentDiv = msgDiv.querySelector('.message-content');
    contentDiv.innerHTML = '';
}

function updateBotMessage(msgDiv, text) {
    let contentDiv = msgDiv.querySelector('.message-content');
    if (!contentDiv) {
        contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        msgDiv.appendChild(contentDiv);
    }
    
    // Preserve existing sources/actions if they exist
    const sourcesDiv = msgDiv.querySelector('.sources-section');
    const actionsDiv = msgDiv.querySelector('.msg-actions');
    
    contentDiv.innerHTML = formatAnswer(text);
    
    if (sourcesDiv) contentDiv.appendChild(sourcesDiv);
    if (actionsDiv) contentDiv.appendChild(actionsDiv);
    
    scrollToBottom();
}

function appendSources(msgDiv, sources) {
    const contentDiv = msgDiv.querySelector('.message-content');
    const sourcesHtml = createSourcesHtml(sources);
    contentDiv.insertAdjacentHTML('beforeend', sourcesHtml);
    scrollToBottom();
}

function appendError(msgDiv, errorText, question) {
    const contentDiv = msgDiv.querySelector('.message-content');
    contentDiv.insertAdjacentHTML('beforeend', `
        <div class="msg-actions">
            <button class="retry-btn" onclick="sendQuestion('${escapeHtml(question.replace(/'/g, "\\'"))}')">↻ Retry</button>
        </div>
    `);
    scrollToBottom();
}

function addCopyButton(msgDiv, text) {
    const contentDiv = msgDiv.querySelector('.message-content');
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'msg-actions';
    actionsDiv.innerHTML = `<button class="icon-btn" title="Copy answer">📋 Copy</button>`;
    
    const copyBtn = actionsDiv.querySelector('button');
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.innerHTML = "✅ Copied";
            setTimeout(() => copyBtn.innerHTML = "📋 Copy", 2000);
        });
    };
    
    contentDiv.appendChild(actionsDiv);
    scrollToBottom();
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
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    return '<p>' + escapeHtml(text).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    // Slight delay to ensure layout updates before scrolling
    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
}
