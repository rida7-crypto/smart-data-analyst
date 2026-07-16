document.addEventListener("DOMContentLoaded", () => {
    // Inject lucide icons securely into DOM elements
    lucide.createIcons();

    // DOM Interaction Node References
    const appSidebar = document.getElementById('appSidebar');
    const collapseSidebarBtn = document.getElementById('collapseSidebarBtn');
    const expandSidebarBtn = document.getElementById('expandSidebarBtn');
    const themeToggle = document.getElementById('themeToggle');
    const dropZone = document.getElementById('dropZone');
    const hiddenFileInput = document.getElementById('hiddenFileInput');
    const userQueryInput = document.getElementById('userQueryInput');
    const sendQueryBtn = document.getElementById('sendQueryBtn');
    const chatViewport = document.getElementById('chatViewport');

    let isDatasetLoaded = false;

    /* ==========================================================
       1. SIDEBAR SLIDE & THEME TOGGLE PHYSIC LIFECYCLES
       ========================================================== */
    collapseSidebarBtn.addEventListener('click', () => {
        appSidebar.classList.add('collapsed');
        expandSidebarBtn.style.display = 'flex';
    });

    expandSidebarBtn.addEventListener('click', () => {
        appSidebar.classList.remove('collapsed');
        expandSidebarBtn.style.display = 'none';
    });

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const targetTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', targetTheme);
        
        const iconNode = themeToggle.querySelector('i');
        if (targetTheme === 'light') {
            iconNode.setAttribute('data-lucide', 'moon');
        } else {
            iconNode.setAttribute('data-lucide', 'sun');
        }
        lucide.createIcons();
    });

    /* ==========================================================
       2. SYSTEM FIELD ENGINE CHECK CONDITIONS
       ========================================================== */
    function validateConsoleState() {
        const queryText = userQueryInput.value.trim();
        sendQueryBtn.disabled = !(isDatasetLoaded && queryText.length > 0);
    }

    userQueryInput.addEventListener('input', validateConsoleState);

    userQueryInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !sendQueryBtn.disabled) {
            event.preventDefault();
            submitOperationalQuery();
        }
    });

    sendQueryBtn.addEventListener('click', () => {
        if (!sendQueryBtn.disabled) {
            submitOperationalQuery();
        }
    });

    /* ==========================================================
       3. ASYNC UPLOAD DATA PIPELINE PROCESSING
       ========================================================== */
    dropZone.addEventListener('click', () => hiddenFileInput.click());
    hiddenFileInput.addEventListener('change', (e) => {
        if(e.target.files.length > 0) handleUpload(e.target.files[0]);
    });

    async function handleUpload(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Show parsing placeholder bubble
        const uploadLoader = appendAgentBubble(`<div class="placeholder-text">Streaming database matrix arrays into memory...</div>`);

        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const data = await response.json();
            
            uploadLoader.remove();

            if(data.status === "Success" || data.metrics) {
                const metrics = data.metrics;
                
                // Map dimension metadata metrics attributes inside layout components
                document.getElementById('metaDim').innerText = `${metrics.shape[0]} × ${metrics.shape[1]}`;
                document.getElementById('metaDup').innerText = metrics.duplicates || 0;
                document.getElementById('metaNull').innerText = metrics.total_nulls || 0;
                
                // Reconstruct column elements seamlessly inside scroll panels
                const colsWrapper = document.getElementById('columnsWrapper');
                colsWrapper.innerHTML = '';
                
                metrics.columns.forEach(col => {
                    const pill = document.createElement('span');
                    pill.className = 'column-pill';
                    pill.innerText = col;
                    colsWrapper.appendChild(pill);
                });

                isDatasetLoaded = true;
                validateConsoleState();
                appendAgentBubble(`<b>${file.name}</b> loaded successfully. Context vectors compiled safely.`);
            } else {
                appendAgentBubble(`Upload rejected: ${data.message || 'Verification anomaly.'}`);
            }
        } catch (err) {
            if(uploadLoader) uploadLoader.remove();
            appendAgentBubble(`File mapping transmission failure: ${err.message}`);
        }
    }

    /* ==========================================================
       4. RUNTIME CODE SANDBOX EXECUTION & MULTI-PLOT STACKING
       ========================================================== */
    async function submitOperationalQuery() {
        const rawQuery = userQueryInput.value.trim();
        if (!rawQuery) return;

        appendUserBubble(rawQuery);
        userQueryInput.value = '';
        sendQueryBtn.disabled = true;

        const processingIndicator = appendAgentBubble(`<div class="placeholder-text">Executing operations across dataframe clusters...</div>`);

        try {
            const formData = new FormData();
            formData.append('query', rawQuery);

            const response = await fetch('/analyze', { method: 'POST', body: formData });
            const data = await response.json();

            processingIndicator.remove();

            if (data.status === 'Success') {
                // Construct base element wrapper structures
                const containerNode = document.createElement('div');
                containerNode.className = 'analysis-response-block';
                
                // 1. Text metric calculations outputs layout
                const textOutputNode = document.createElement('div');
                textOutputNode.className = 'terminal-text-payload';
                textOutputNode.innerHTML = data.output ? data.output.replace(/\n/g, '<br>') : 'Execution completed.';
                containerNode.appendChild(textOutputNode);

                // 2. Headless Matplotlib Base64 image payload drawing segment
                if (data.has_mpl && data.plot_base64) {
                    const imgWrapper = document.createElement('div');
                    imgWrapper.className = 'image-frame animate-fade-in';
                    imgWrapper.innerHTML = `<img src="data:image/png;base64,${data.plot_base64}" alt="Analysis Visual Layout Plot">`;
                    containerNode.appendChild(imgWrapper);
                }

                // 3. Interactive Plotly node translation wrapper execution segment
                if (data.plotly_html) {
                    const plotlyWrapper = document.createElement('div');
                    plotlyWrapper.className = 'chart-frame animate-fade-in';
                    
                    // Generate unique runtime identities to map script calculations securely
                    const uniqueId = 'plotly-' + Math.random().toString(36).substr(2, 9);
                    plotlyWrapper.id = uniqueId;
                    containerNode.appendChild(plotlyWrapper);
                    
                    // Safe document detachment compilation
                    setTimeout(() => {
                        const range = document.createRange();
                        const scriptFragment = range.createContextualFragment(data.plotly_html);
                        const targetBox = document.getElementById(uniqueId);
                        if (targetBox) {
                            targetBox.appendChild(scriptFragment);
                            // Adjust size configurations to match current container sizing metrics
                            const plottedChart = targetBox.querySelector('.plotly-graph-div');
                            if (plottedChart) {
                                Plotly.Plots.resize(plottedChart);
                            }
                        }
                    }, 50);
                }

                // 4. Wrap complex code blocks inside drop-down accordions
                if (data.code) {
                    const accordionNode = document.createElement('details');
                    accordionNode.innerHTML = `
                        <summary>View Executed Logic Code</summary>
                        <pre><code>${escapeHtml(data.code)}</code></pre>
                    `;
                    containerNode.appendChild(accordionNode);
                }

                appendAgentBubbleNode(containerNode);
            } else {
                appendAgentBubble(`Operational Error: ${data.message || 'Syntax variance error encountered.'}`);
            }
        } catch (error) {
            if(processingIndicator) processingIndicator.remove();
            appendAgentBubble(`Network disconnect or runtime calculation timeout: ${error.message}`);
        }

        validateConsoleState();
    }

    /* ==========================================================
       5. VIEW CONSOLE HELPER UTILITY LOOPS
       ========================================================== */
    function appendUserBubble(text) {
        const row = document.createElement('div');
        row.className = 'chat-row user-mode';
        row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
        chatViewport.appendChild(row);
        chatViewport.scrollTop = chatViewport.scrollHeight;
    }

    function appendAgentBubble(htmlContent) {
        const row = document.createElement('div');
        row.className = 'chat-row agent-mode';
        row.innerHTML = `<div class="bubble">${htmlContent}</div>`;
        chatViewport.appendChild(row);
        chatViewport.scrollTop = chatViewport.scrollHeight;
        return row;
    }

    function appendAgentBubbleNode(domNode) {
        const row = document.createElement('div');
        row.className = 'chat-row agent-mode';
        const bubble = document.createElement('div');
        bubble.className = 'bubble target-agent-bubble';
        bubble.appendChild(domNode);
        row.appendChild(bubble);
        chatViewport.appendChild(row);
        chatViewport.scrollTop = chatViewport.scrollHeight;
    }

    function escapeHtml(unsafeString) {
        return unsafeString
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});