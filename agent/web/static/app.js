document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentDepth = "standard";
    let currentFocus = "all";
    let currentTaskId = null;
    let currentReport = null;
    let eventSource = null;
    let timerInterval = null;
    let secondsElapsed = 0;
    let streamingMarkdown = "";

    // DOM Elements
    const vaultSidebar = document.getElementById("vaultSidebar");
    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
    const historyList = document.getElementById("historyList");
    const modelSelect = document.getElementById("modelSelect");
    const researchForm = document.getElementById("researchForm");
    const topicInput = document.getElementById("topicInput");
    const submitBtn = document.getElementById("submitBtn");
    const depthControl = document.getElementById("depthControl");
    const focusControl = document.getElementById("focusControl");
    const executionTracker = document.getElementById("executionTracker");
    const elapsedBadge = document.getElementById("elapsedBadge");
    const activityLog = document.getElementById("activityLog");
    const sourcesReel = document.getElementById("sourcesReel");
    const sourcesCount = document.getElementById("sourcesCount");
    const sourcesCardsGrid = document.getElementById("sourcesCardsGrid");
    const reportCard = document.getElementById("reportCard");
    const reportDisplayTitle = document.getElementById("reportDisplayTitle");
    const reportSubmeta = document.getElementById("reportSubmeta");
    const markdownBody = document.getElementById("markdownBody");
    const copyMdBtn = document.getElementById("copyMdBtn");
    const downloadMdBtn = document.getElementById("downloadMdBtn");
    const exportHtmlBtn = document.getElementById("exportHtmlBtn");

    // Follow-up Q&A and Deepen Elements
    let currentFollowupMode = "ask";
    const followupPanel = document.getElementById("reportFollowupPanel");
    const followupModeToggle = document.getElementById("followupModeToggle");
    const followupSuggestions = document.getElementById("followupSuggestions");
    const followupThread = document.getElementById("followupThread");
    const threadPlaceholder = document.getElementById("threadPlaceholder");
    const followupForm = document.getElementById("followupForm");
    const followupInput = document.getElementById("followupInput");
    const followupSendBtn = document.getElementById("followupSendBtn");
    const followupSendText = document.getElementById("followupSendText");
    const followupSendIcon = document.getElementById("followupSendIcon");

    // Configure Marked
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        }
    });

    // Auth State & Elements (Scoped to tab session)
    let authToken = sessionStorage.getItem("research_auth_token") || "";
    let userRole = sessionStorage.getItem("research_user_role") || "guest";
    let guestSessionReports = [];
    // Clean up any legacy localStorage tokens
    localStorage.removeItem("research_auth_token");
    const pinOverlay = document.getElementById("pinOverlay");
    const pinForm = document.getElementById("pinForm");
    const pinInput = document.getElementById("pinInput");
    const pinError = document.getElementById("pinError");
    const lockAppBtn = document.getElementById("lockAppBtn");

    function applyRoleUI(role) {
        userRole = role || "guest";
        sessionStorage.setItem("research_user_role", userRole);
        const viewQueriesBtn = document.getElementById("viewQueriesBtn");
        const settingsBtn = document.getElementById("settingsBtn");
        const modelSelectWrapper = document.querySelector(".model-select-wrapper");
        if (userRole === "guest") {
            if (viewQueriesBtn) viewQueriesBtn.classList.add("hidden");
            if (settingsBtn) settingsBtn.classList.add("hidden");
            if (modelSelectWrapper) modelSelectWrapper.classList.add("hidden");
        } else {
            if (viewQueriesBtn) viewQueriesBtn.classList.remove("hidden");
            if (settingsBtn) settingsBtn.classList.remove("hidden");
            if (modelSelectWrapper) modelSelectWrapper.classList.remove("hidden");
        }
    }

    async function authFetch(url, options = {}) {
        options.headers = options.headers || {};
        const urlParams = new URLSearchParams(window.location.search);
        const keyParam = urlParams.get("key") || urlParams.get("pin") || "";
        if (authToken) {
            if (options.headers instanceof Headers) {
                options.headers.set("Authorization", `Bearer ${authToken}`);
            } else {
                options.headers["Authorization"] = `Bearer ${authToken}`;
            }
        } else if (keyParam) {
            if (url.includes("?")) {
                url += `&key=${encodeURIComponent(keyParam)}`;
            } else {
                url += `?key=${encodeURIComponent(keyParam)}`;
            }
        }
        return await fetch(url, options);
    }

    function showPinModal() {
        // Disabled - no password required
    }

    function hidePinModal() {
        if (pinOverlay) {
            pinOverlay.classList.add("hidden");
            pinOverlay.style.display = "none";
        }
        if (pinError) {
            pinError.classList.add("hidden");
        }
    }

    async function checkAuthOnStartup() {
        hidePinModal();
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const keyParam = urlParams.get("key") || urlParams.get("pin") || "";
            const authCheckUrl = keyParam ? `/api/auth/check?key=${encodeURIComponent(keyParam)}` : "/api/auth/check";
            const res = await fetch(authCheckUrl);
            if (res.ok) {
                const data = await res.json();
                userRole = data.role || "guest";
                sessionStorage.setItem("research_user_role", userRole);
                applyRoleUI(userRole);
                await loadModels();
                await loadHistory(userRole === "owner");
                return;
            }
        } catch (err) {
            console.warn("Auth check failed:", err);
        }
        applyRoleUI("guest");
        await loadModels();
        await loadHistory(false);
    }

    if (pinForm) {
        pinForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const pin = (pinInput ? pinInput.value : "").trim();
            if (!pin) return;

            try {
                const res = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pin: pin }),
                });

                if (res.ok) {
                    const data = await res.json();
                    authToken = data.token;
                    sessionStorage.setItem("research_auth_token", authToken);
                    applyRoleUI(data.role);
                    hidePinModal();
                    loadModels();
                    loadHistory(data.role === "owner");
                } else {
                    if (pinError) pinError.classList.remove("hidden");
                    if (pinInput) {
                        pinInput.select();
                        pinInput.focus();
                    }
                }
            } catch (err) {
                if (pinError) {
                    pinError.innerText = "Connection error. Try again.";
                    pinError.classList.remove("hidden");
                }
            }
        });
    }

    if (lockAppBtn) {
        lockAppBtn.addEventListener("click", async () => {
            authToken = "";
            sessionStorage.removeItem("research_auth_token");
            sessionStorage.removeItem("research_user_role");
            localStorage.removeItem("research_auth_token");
            document.cookie = "research_auth_token=; Max-Age=0; path=/;";
            await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
            showPinModal();
        });
    }

    // 1. Initial Startup with Auth Check
    checkAuthOnStartup();

    // 2. Event Listeners
    sidebarToggleBtn.addEventListener("click", () => {
        vaultSidebar.classList.toggle("collapsed");
    });

    refreshHistoryBtn.addEventListener("click", () => {
        loadHistory();
    });

    // Segmented Controls (Depth & Focus)
    setupSegmentedControl(depthControl, (val) => currentDepth = val);
    setupSegmentedControl(focusControl, (val) => currentFocus = val);

    // Attached Documents State
    let attachedDocuments = [];
    const docFileInput = document.getElementById("docFileInput");
    const uploadDropzone = document.getElementById("uploadDropzone");
    const attachedDocsList = document.getElementById("attachedDocsList");

    function renderAttachedDocs() {
        if (!attachedDocsList) return;
        attachedDocsList.innerHTML = "";
        attachedDocuments.forEach((doc, idx) => {
            const pill = document.createElement("div");
            pill.className = "doc-pill";
            const kbSize = Math.round(doc.size_bytes / 1024) || 1;
            const metaInfo = doc.page_count > 1 ? `${doc.page_count} pgs, ${kbSize} KB` : `${kbSize} KB`;
            pill.innerHTML = `
                <span class="doc-pill-type">${escapeHtml(doc.file_type || 'doc')}</span>
                <span class="doc-pill-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                <span class="doc-pill-meta">(${escapeHtml(metaInfo)})</span>
                <button type="button" class="doc-pill-remove" data-idx="${idx}" title="Remove document">×</button>
            `;
            attachedDocsList.appendChild(pill);
        });

        attachedDocsList.querySelectorAll(".doc-pill-remove").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.target.dataset.idx, 10);
                attachedDocuments.splice(idx, 1);
                renderAttachedDocs();
            });
        });
    }

    async function uploadSingleFile(file) {
        const formData = new FormData();
        formData.append("file", file);
        try {
            const res = await authFetch("/api/upload", {
                method: "POST",
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || "Upload failed");
            }
            const data = await res.json();
            attachedDocuments.push(data);
            renderAttachedDocs();
        } catch (err) {
            alert(`Failed to upload ${file.name}: ${err.message}`);
        }
    }

    async function handleSelectedFiles(fileList) {
        if (!fileList || fileList.length === 0) return;
        for (let i = 0; i < fileList.length; i++) {
            await uploadSingleFile(fileList[i]);
        }
    }

    if (docFileInput) {
        docFileInput.addEventListener("change", async (e) => {
            await handleSelectedFiles(e.target.files);
            docFileInput.value = "";
        });
    }

    if (uploadDropzone) {
        uploadDropzone.addEventListener("click", () => {
            if (docFileInput) docFileInput.click();
        });

        uploadDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadDropzone.classList.add("dragover");
        });

        uploadDropzone.addEventListener("dragleave", () => {
            uploadDropzone.classList.remove("dragover");
        });

        uploadDropzone.addEventListener("drop", async (e) => {
            e.preventDefault();
            uploadDropzone.classList.remove("dragover");
            if (e.dataTransfer && e.dataTransfer.files) {
                await handleSelectedFiles(e.dataTransfer.files);
            }
        });
    }

    // Form Submission
    researchForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const topic = topicInput.value.trim();
        if (!topic) return;

        startResearch(topic);
    });

    // Sample Topic Chips
    document.querySelectorAll(".sample-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const topic = chip.dataset.topic;
            topicInput.value = topic;
            startResearch(topic);
        });
    });

    // Action Buttons
    copyMdBtn.addEventListener("click", () => {
        if (!currentReport || !currentReport.content) return;
        navigator.clipboard.writeText(currentReport.content).then(() => {
            const originalText = copyMdBtn.innerText;
            copyMdBtn.innerText = "Copied";
            setTimeout(() => copyMdBtn.innerText = originalText, 2000);
        });
    });

    downloadMdBtn.addEventListener("click", () => {
        if (!currentReport || !currentReport.content) return;
        const blob = new Blob([currentReport.content], { type: "text/markdown;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        const safeName = (currentReport.topic || "research_report").replace(/[^a-z0-9]/gi, "_").toLowerCase();
        link.setAttribute("href", url);
        link.setAttribute("download", `${safeName}.md`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    exportHtmlBtn.addEventListener("click", () => {
        if (!currentReport || !currentReport.id) return;
        window.open(`/api/report/${currentReport.id}/export?token=${encodeURIComponent(authToken)}`, "_blank");
    });

    // --- Helper Functions ---

    function setupSegmentedControl(container, onChange) {
        const buttons = container.querySelectorAll(".segment-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => {
                buttons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                onChange(btn.dataset.value);
            });
        });
    }

    async function loadModels() {
        try {
            const res = await authFetch("/api/models");
            const data = await res.json();
            if (data.models && data.models.length > 0) {
                modelSelect.innerHTML = "";
                // Auto option
                const autoOpt = document.createElement("option");
                autoOpt.value = "auto";
                autoOpt.textContent = "Auto (Best Local Model)";
                modelSelect.appendChild(autoOpt);

                data.models.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m.id;
                    opt.textContent = `${m.name} (${m.badge})`;
                    modelSelect.appendChild(opt);
                });
            } else {
                modelSelect.innerHTML = `<option value="auto">No Models Detected (Click Settings to Configure)</option>`;
            }
        } catch (err) {
            console.error("Failed to load models:", err);
        }
    }

    async function loadHistory(autoSelectFirst = false) {
        try {
            if (userRole === "guest") {
                renderHistory(guestSessionReports);
                return;
            }
            const res = await authFetch("/api/history");
            const data = await res.json();
            const items = data.history || [];
            renderHistory(items);
            if (autoSelectFirst && (!currentReport || !currentReport.id) && items.length > 0) {
                await loadPastReport(items[0].id);
            }
        } catch (err) {
            console.error("Failed to load history:", err);
        }
    }

    function renderHistory(items) {
        const vaultCountBadge = document.getElementById("vaultCountBadge");
        if (vaultCountBadge) {
            vaultCountBadge.innerText = (items && items.length) ? items.length : 0;
        }

        if (!items || items.length === 0) {
            historyList.innerHTML = '<div class="empty-state">No saved research sessions yet.</div>';
            return;
        }

        historyList.innerHTML = "";
        items.forEach(item => {
            const el = document.createElement("div");
            el.className = "history-item";
            el.dataset.id = item.id;
            if (currentReport && currentReport.id === item.id) {
                el.classList.add("active");
            }
            
            const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, {
                month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
            }) : "";

            el.innerHTML = `
                <div class="history-item-title" title="${escapeHtml(item.topic)}">${escapeHtml(item.topic)}</div>
                <div class="history-item-meta">
                    <span>${escapeHtml(item.model || 'local')}</span>
                    <span>${dateStr}</span>
                </div>
            `;

            el.addEventListener("click", () => {
                document.querySelectorAll(".history-item").forEach(i => i.classList.remove("active"));
                el.classList.add("active");
                if (userRole === "guest") {
                    const found = guestSessionReports.find(r => r.id === item.id);
                    if (found) {
                        currentReport = found;
                        displayReport(found);
                        return;
                    }
                }
                loadPastReport(item.id);
            });

            historyList.appendChild(el);
        });
    }

    async function loadPastReport(reportId) {
        try {
            const res = await authFetch(`/api/report/${reportId}`);
            if (!res.ok) throw new Error("Report not found");
            const data = await res.json();
            
            data.id = data.id || reportId;
            currentReport = data;
            displayReport(data);

            // Update active state in sidebar
            document.querySelectorAll(".history-item").forEach(item => {
                if (item.dataset.id === reportId) {
                    item.classList.add("active");
                } else {
                    item.classList.remove("active");
                }
            });

            // Hide live tracker if viewing past report
            executionTracker.classList.add("hidden");
        } catch (err) {
            console.error("Error loading past report:", err);
        }
    }

    function displayReport(report) {
        if (!report) return;
        report.id = report.id || report.report_id;
        currentReport = report;

        reportCard.classList.remove("hidden");
        reportDisplayTitle.innerText = report.topic || "Research Report";
        
        const dateStr = report.created_at ? new Date(report.created_at).toLocaleString() : "";
        const sourcesCount = (report.sources || []).length || report.sources_count || 0;
        reportSubmeta.innerText = `Engine: ${report.model || 'auto'} | Date: ${dateStr} | ${sourcesCount} Sources Cited`;

        markdownBody.innerHTML = marked.parse(report.content || "");

        // Highlight code blocks
        markdownBody.querySelectorAll("pre code").forEach(block => {
            hljs.highlightElement(block);
        });

        // Load conversation history for this report
        if (report.id) {
            loadReportConversation(report.id);
        }

        reportCard.scrollIntoView({ behavior: "smooth" });
    }

    async function startResearch(topic) {
        // Reset UI
        setFormBusy(true);
        const greetingBox = document.getElementById("greetingBox");
        if (greetingBox) greetingBox.classList.add("hidden");
        executionTracker.classList.remove("hidden");
        reportCard.classList.add("hidden");
        sourcesReel.classList.add("hidden");
        sourcesCardsGrid.innerHTML = "";
        activityLog.innerHTML = "";
        streamingMarkdown = "";
        resetSteps();

        // Start elapsed timer
        startTimer();
        addLog(`Initiating autonomous research on: "${topic}"`, "info");

        const doc_ids = attachedDocuments.map(d => d.doc_id);
        if (doc_ids.length > 0) {
            addLog(`Attached ${doc_ids.length} local document(s) for primary factual grounding`, "info");
        }

        const payload = {
            topic: topic,
            depth: currentDepth,
            focus: currentFocus,
            model_id: modelSelect.value,
            doc_ids: doc_ids.length > 0 ? doc_ids : undefined,
        };

        try {
            const res = await authFetch("/api/research", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Failed to start research");
            }

            const data = await res.json();
            currentTaskId = data.task_id;
            listenToEvents(currentTaskId);
        } catch (err) {
            addLog(`Error: ${err.message}`, "warn");
            stopTimer();
            setFormBusy(false);
        }
    }

    function listenToEvents(taskId) {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(`/api/research/stream/${taskId}?token=${encodeURIComponent(authToken)}`);

        eventSource.onmessage = (e) => {
            if (!e.data) return;
            try {
                const event = JSON.parse(e.data);
                handleAgentEvent(event);
            } catch (err) {
                console.error("Error parsing event:", err, e.data);
            }
        };

        eventSource.onerror = (err) => {
            console.warn("EventSource closed or disconnected.", err);
            eventSource.close();
            stopTimer();
            setFormBusy(false);
        };
    }

    function handleAgentEvent(event) {
        switch (event.type) {
            case "uploaded_docs_loaded":
                addLog(event.message || `Loaded ${event.count} local document(s)`, "info");
                break;

            case "phase_start":
                setStepActive(event.phase);
                addLog(event.message, "info");
                break;

            case "plan_complete":
                addLog(`Plan generated: ${event.plan.sub_questions.length} sub-questions formulated.`, "success");
                if (event.plan.sub_questions) {
                    event.plan.sub_questions.forEach(q => addLog(`  - ${q}`, "info"));
                }
                break;

            case "search_complete":
                addLog(event.message, "success");
                renderSourcesReel(event.sources);
                break;

            case "reading_complete":
                addLog(event.message, "success");
                break;

            case "synthesis_chunk":
                // Make report card visible and stream tokens
                reportCard.classList.remove("hidden");
                streamingMarkdown += event.chunk;
                markdownBody.innerHTML = marked.parse(streamingMarkdown);
                break;

            case "complete":
                addLog("Research cycle complete!", "success");
                stopTimer();
                setFormBusy(false);
                markAllStepsDone();
                if (eventSource) eventSource.close();

                currentReport = event.data;
                if (userRole === "guest" && event.data) {
                    if (!guestSessionReports.some(r => r.id === event.data.id)) {
                        guestSessionReports.unshift(event.data);
                    }
                }
                displayReport(event.data);
                loadHistory(); // Refresh history list
                break;

            case "greeting":
            case "clarification":
                stopTimer();
                setFormBusy(false);
                if (eventSource) eventSource.close();
                executionTracker.classList.add("hidden");
                showGreetingCard(event.message, event.suggested_topics);
                break;

            case "error":
                addLog(event.message, "warn");
                stopTimer();
                setFormBusy(false);
                if (eventSource) eventSource.close();
                break;
        }
    }

    function showGreetingCard(message, suggestions) {
        const greetingBox = document.getElementById("greetingBox");
        const greetingBody = document.getElementById("greetingBody");
        const greetingSuggestions = document.getElementById("greetingSuggestions");
        if (!greetingBox) return;

        greetingBody.innerHTML = marked.parse(message || "");
        greetingSuggestions.innerHTML = "";

        if (suggestions && suggestions.length > 0) {
            suggestions.forEach(topic => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "suggestion-btn";
                btn.innerText = topic;
                btn.addEventListener("click", () => {
                    topicInput.value = topic;
                    startResearch(topic);
                });
                greetingSuggestions.appendChild(btn);
            });
        }

        greetingBox.classList.remove("hidden");
        greetingBox.scrollIntoView({ behavior: "smooth" });
    }

    function renderSourcesReel(sources) {
        if (!sources || sources.length === 0) return;
        sourcesReel.classList.remove("hidden");
        sourcesCount.innerText = sources.length;
        sourcesCardsGrid.innerHTML = "";

        sources.forEach(s => {
            const card = document.createElement("div");
            card.className = "source-card";
            const isLocal = s.source === "user_upload" || (s.url && s.url.startsWith("local://"));
            const titleHtml = isLocal
                ? `<span style="font-weight:600; color:var(--text-primary);">${escapeHtml(s.title || s.url)}</span>`
                : `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(s.title || s.url)}</a>`;
            const badgeLabel = isLocal ? "Local Doc" : s.source;

            card.innerHTML = `
                <div class="source-card-header">
                    <span class="source-badge ${escapeHtml(s.source)}">${escapeHtml(badgeLabel)}</span>
                    <span style="font-size:0.7rem; color:var(--text-muted);">${escapeHtml(s.published_date || '')}</span>
                </div>
                <div class="source-card-title">${titleHtml}</div>
                <div class="source-card-snippet">${escapeHtml(s.snippet || '')}</div>
            `;
            sourcesCardsGrid.appendChild(card);
        });
    }

    function resetSteps() {
        ["planning", "searching", "reading", "synthesizing"].forEach(p => {
            const el = document.getElementById(`step-${p}`);
            if (el) {
                el.classList.remove("active", "done");
            }
        });
    }

    function setStepActive(phase) {
        const order = ["planning", "searching", "reading", "synthesizing"];
        const currentIndex = order.indexOf(phase);
        if (currentIndex === -1) return;

        order.forEach((p, idx) => {
            const el = document.getElementById(`step-${p}`);
            if (!el) return;
            if (idx < currentIndex) {
                el.classList.remove("active");
                el.classList.add("done");
            } else if (idx === currentIndex) {
                el.classList.add("active");
                el.classList.remove("done");
            } else {
                el.classList.remove("active", "done");
            }
        });
        updateTrackerSubstatus(phase);
    }

    function updateTrackerSubstatus(phase) {
        const sub = document.getElementById("trackerSubstatus");
        if (!sub) return;
        switch (phase) {
            case "planning":
                sub.innerText = "Planning search angles, formulating sub-questions and hypotheses...";
                break;
            case "searching":
                sub.innerText = "Querying arXiv preprints, academic repositories and web sources...";
                break;
            case "reading":
                sub.innerText = "Crawling web pages and extracting dense evidence...";
                break;
            case "synthesizing":
                sub.innerText = "Synthesizing evidence, grounding citations and drafting report...";
                break;
            case "complete":
                sub.innerText = "Research cycle complete. Report generated.";
                break;
            default:
                sub.innerText = "Autonomous research engine active...";
                break;
        }
    }

    function markAllStepsDone() {
        ["planning", "searching", "reading", "synthesizing"].forEach(p => {
            const el = document.getElementById(`step-${p}`);
            if (el) {
                el.classList.remove("active");
                el.classList.add("done");
            }
        });
        updateTrackerSubstatus("complete");
    }

    function addLog(msg, level = "info") {
        const entry = document.createElement("div");
        entry.className = `log-entry ${level}`;
        const time = new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
        entry.innerText = `[${time}] ${msg}`;
        activityLog.appendChild(entry);
        activityLog.scrollTop = activityLog.scrollHeight;
    }

    function startTimer() {
        secondsElapsed = 0;
        elapsedBadge.innerText = "00:00";
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            secondsElapsed++;
            const mins = String(Math.floor(secondsElapsed / 60)).padStart(2, "0");
            const secs = String(secondsElapsed % 60).padStart(2, "0");
            elapsedBadge.innerText = `${mins}:${secs}`;
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function setFormBusy(busy) {
        submitBtn.disabled = busy;
        const spinner = submitBtn.querySelector(".btn-spinner-icon") || submitBtn.querySelector(".btn-spinner");
        const text = submitBtn.querySelector(".btn-text");
        const statusText = document.getElementById("statusText");
        const statusDot = document.querySelector(".status-dot");

        if (busy) {
            if (spinner) spinner.classList.remove("hidden");
            if (text) text.innerText = "Researching...";
            if (statusText) statusText.innerText = "Researching...";
            if (statusDot) statusDot.classList.add("busy");
        } else {
            if (spinner) spinner.classList.add("hidden");
            if (text) text.innerText = "Start Research";
            if (statusText) statusText.innerText = "System Ready";
            if (statusDot) statusDot.classList.remove("busy");
        }
    }

    // ----------------------------------------------------
    // Follow-up Q&A and Continuous Research Handlers
    // ----------------------------------------------------
    async function loadReportConversation(reportId) {
        if (!followupThread) return;
        followupThread.innerHTML = "";
        
        try {
            const res = await authFetch(`/api/report/${reportId}/conversation`);
            if (res.ok) {
                const data = await res.json();
                const messages = data.messages || [];
                if (messages.length > 0) {
                    messages.forEach(msg => {
                        const el = document.createElement("div");
                        el.className = `chat-msg ${msg.role === "user" ? "user" : "assistant"}`;
                        const roleTitle = msg.role === "user" ? "You" : "Research Agent";
                        el.innerHTML = `
                            <div class="chat-msg-header">${roleTitle}</div>
                            <div class="chat-msg-content">${marked.parse(msg.content || "")}</div>
                        `;
                        el.querySelectorAll("pre code").forEach(b => hljs.highlightElement(b));
                        followupThread.appendChild(el);
                    });
                    followupThread.scrollTop = followupThread.scrollHeight;
                    return;
                }
            }
        } catch (e) {
            console.warn("Failed to load conversation:", e);
        }

        // Default placeholder if no past conversation
        const placeholder = document.createElement("div");
        placeholder.className = "thread-placeholder";
        placeholder.id = "threadPlaceholder";
        placeholder.innerHTML = "Ask any question about this report, or choose <b>Deepen Search</b> to find new papers and append new sections.";
        followupThread.appendChild(placeholder);
    }

    // Mode Toggle
    if (followupModeToggle) {
        followupModeToggle.querySelectorAll(".mode-toggle-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                followupModeToggle.querySelectorAll(".mode-toggle-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                currentFollowupMode = btn.dataset.mode;
                if (currentFollowupMode === "ask") {
                    followupInput.placeholder = "Ask a question about this report (findings, arXiv papers, limitations)...";
                    followupSendText.innerText = "Ask";
                    followupSendIcon.innerText = "";
                } else {
                    followupInput.placeholder = "Enter a subtopic to search deeper on arXiv & Web (e.g. 'verification floor algorithms')...";
                    followupSendText.innerText = "Deepen";
                    followupSendIcon.innerText = "";
                }
                followupInput.focus();
            });
        });
    }

    // Suggestion Chips
    if (followupSuggestions) {
        followupSuggestions.querySelectorAll(".qa-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const q = chip.dataset.q;
                if (q && followupInput) {
                    followupInput.value = q;
                    followupForm.dispatchEvent(new Event("submit"));
                }
            });
        });
    }

    // Textarea input sizing and Enter handling
    if (followupInput) {
        followupInput.addEventListener("input", () => {
            followupInput.style.height = "auto";
            followupInput.style.height = Math.min(followupInput.scrollHeight, 120) + "px";
        });
        followupInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                followupForm.dispatchEvent(new Event("submit"));
            }
        });
    }

    // Follow-up form submission
    if (followupForm) {
        followupForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = followupInput.value.trim();
            if (!text) return;

            let reportId = currentReport ? (currentReport.id || currentReport.report_id) : null;
            if (!reportId) {
                // Auto-resolve to active or first report in history
                const item = document.querySelector(".history-item.active") || document.querySelector(".history-item");
                if (item && item.dataset.id) {
                    await loadPastReport(item.dataset.id);
                    reportId = currentReport ? (currentReport.id || currentReport.report_id) : null;
                }
            }

            if (!reportId) {
                alert("Please select or generate a report first.");
                return;
            }

            if (currentFollowupMode === "ask") {
                await handleAskQuestion(text);
            } else {
                await handleDeepenResearch(text);
            }
        });
    }

    async function handleAskQuestion(question) {
        // Remove placeholder if present
        const placeholder = document.getElementById("threadPlaceholder");
        if (placeholder) placeholder.remove();

        // User bubble
        const userMsg = document.createElement("div");
        userMsg.className = "chat-msg user";
        userMsg.innerHTML = `<div class="chat-msg-header">You</div><div class="chat-msg-content">${escapeHtml(question)}</div>`;
        followupThread.appendChild(userMsg);

        followupInput.value = "";
        followupInput.style.height = "auto";
        followupSendBtn.disabled = true;
        followupInput.disabled = true;

        // Assistant bubble with stream container
        const assistMsg = document.createElement("div");
        assistMsg.className = "chat-msg assistant";
        const contentDiv = document.createElement("div");
        contentDiv.className = "chat-msg-content";
        contentDiv.innerHTML = `<span class="pulse-indicator"></span> <i>Consulting report & cited evidence...</i>`;
        assistMsg.innerHTML = `<div class="chat-msg-header">Research Agent</div>`;
        assistMsg.appendChild(contentDiv);
        followupThread.appendChild(assistMsg);
        followupThread.scrollTop = followupThread.scrollHeight;

        try {
            const repId = currentReport.id || currentReport.report_id;
            const res = await authFetch(`/api/report/${repId}/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question, model_id: modelSelect.value }),
            });

            if (!res.ok) {
                const errJson = await res.json().catch(() => ({}));
                throw new Error(errJson.detail || "Failed to get answer");
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                buffer = parts.pop();

                for (const part of parts) {
                    if (part.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(part.slice(6));
                            if (data.chunk) {
                                accumulated += data.chunk;
                                contentDiv.innerHTML = marked.parse(accumulated);
                                followupThread.scrollTop = followupThread.scrollHeight;
                            } else if (data.error) {
                                contentDiv.innerHTML = `<span style="color:#ef4444">Error: ${escapeHtml(data.error)}</span>`;
                            }
                        } catch (err) {}
                    }
                }
            }

            contentDiv.innerHTML = marked.parse(accumulated);
            contentDiv.querySelectorAll("pre code").forEach(b => hljs.highlightElement(b));
            followupThread.scrollTop = followupThread.scrollHeight;
        } catch (err) {
            contentDiv.innerHTML = `<span style="color:#ef4444">Error: ${escapeHtml(err.message)}</span>`;
        } finally {
            followupSendBtn.disabled = false;
            followupInput.disabled = false;
            followupInput.focus();
        }
    }

    async function handleDeepenResearch(query) {
        // Remove placeholder if present
        const placeholder = document.getElementById("threadPlaceholder");
        if (placeholder) placeholder.remove();

        const userMsg = document.createElement("div");
        userMsg.className = "chat-msg user";
        userMsg.innerHTML = `<div class="chat-msg-header">Deep Research Request</div><div class="chat-msg-content">Deepen Research: <b>${escapeHtml(query)}</b></div>`;
        followupThread.appendChild(userMsg);

        const statusMsg = document.createElement("div");
        statusMsg.className = "chat-msg status";
        statusMsg.innerHTML = `<span>Formulating search queries across arXiv and Web...</span>`;
        followupThread.appendChild(statusMsg);
        followupThread.scrollTop = followupThread.scrollHeight;

        followupInput.value = "";
        followupInput.style.height = "auto";
        followupSendBtn.disabled = true;
        followupInput.disabled = true;

        try {
            const repId = currentReport.id || currentReport.report_id;
            const res = await authFetch(`/api/report/${repId}/deepen`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: query,
                    focus: currentFocus,
                    model_id: modelSelect.value,
                }),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to start deep dive");
            }

            const data = await res.json();
            const taskId = data.task_id;
            const deepenEventSource = new EventSource(`/api/research/stream/${taskId}?token=${encodeURIComponent(authToken)}`);

            deepenEventSource.onmessage = (e) => {
                try {
                    const ev = JSON.parse(e.data);
                    if (ev.type === "deepen_progress" || ev.type === "deepen_start") {
                        statusMsg.innerHTML = `<span>${escapeHtml(ev.message)}</span>`;
                        followupThread.scrollTop = followupThread.scrollHeight;
                    } else if (ev.type === "deepen_complete") {
                        deepenEventSource.close();
                        statusMsg.className = "chat-msg assistant";
                        statusMsg.innerHTML = `
                            <div class="chat-msg-header">Deep Dive Complete</div>
                            <div class="chat-msg-content">
                                <p style="color:var(--accent-green); font-weight:600; margin-bottom:8px;">
                                    Appended New Section with ${ev.new_sources_count} New Cited Sources
                                </p>
                                ${marked.parse(ev.addendum)}
                            </div>
                        `;
                        statusMsg.querySelectorAll("pre code").forEach(b => hljs.highlightElement(b));

                        // Update main report view
                        if (ev.updated_content) {
                            currentReport.content = ev.updated_content;
                            markdownBody.innerHTML = marked.parse(ev.updated_content);
                            markdownBody.querySelectorAll("pre code").forEach(b => hljs.highlightElement(b));
                        }

                        // Refresh history
                        loadHistory();
                        followupThread.scrollTop = followupThread.scrollHeight;
                        followupSendBtn.disabled = false;
                        followupInput.disabled = false;
                        followupInput.focus();
                    } else if (ev.type === "error") {
                        deepenEventSource.close();
                        statusMsg.innerHTML = `<span style="color:#dc2626">Error: ${escapeHtml(ev.message)}</span>`;
                        followupSendBtn.disabled = false;
                        followupInput.disabled = false;
                    }
                } catch (err) {
                    console.error("Deepen stream parse error:", err);
                }
            };

            deepenEventSource.onerror = (err) => {
                console.warn("Deepen EventSource disconnected:", err);
                deepenEventSource.close();
                followupSendBtn.disabled = false;
                followupInput.disabled = false;
            };

        } catch (err) {
            statusMsg.innerHTML = `<span style="color:#dc2626">Error: ${escapeHtml(err.message)}</span>`;
            followupSendBtn.disabled = false;
            followupInput.disabled = false;
        }
    }

    // --- User Activity / Question Log Modal ---
    const viewQueriesBtn = document.getElementById("viewQueriesBtn");
    const queriesModalOverlay = document.getElementById("queriesModalOverlay");
    const closeQueriesModalBtn = document.getElementById("closeQueriesModalBtn");
    const doneQueriesBtn = document.getElementById("doneQueriesBtn");
    const refreshQueriesBtn = document.getElementById("refreshQueriesBtn");
    const queriesListContent = document.getElementById("queriesListContent");
    const queriesCountText = document.getElementById("queriesCountText");

    function showQueriesModal() {
        if (queriesModalOverlay) {
            queriesModalOverlay.classList.remove("hidden");
            loadQueriesLog();
        }
    }

    function hideQueriesModal() {
        if (queriesModalOverlay) {
            queriesModalOverlay.classList.add("hidden");
        }
    }

    if (viewQueriesBtn) {
        viewQueriesBtn.addEventListener("click", showQueriesModal);
    }
    if (closeQueriesModalBtn) {
        closeQueriesModalBtn.addEventListener("click", hideQueriesModal);
    }
    if (doneQueriesBtn) {
        doneQueriesBtn.addEventListener("click", hideQueriesModal);
    }
    if (refreshQueriesBtn) {
        refreshQueriesBtn.addEventListener("click", loadQueriesLog);
    }

    async function loadQueriesLog() {
        if (!queriesListContent) return;
        queriesListContent.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 24px;">Fetching recorded inquiries...</div>';
        try {
            const res = await authFetch("/api/activity/queries");
            if (!res.ok) throw new Error("Failed to fetch inquiry log");
            const data = await res.json();
            const queries = data.queries || [];

            if (queriesCountText) {
                queriesCountText.innerText = `${queries.length} total recorded inquiry${queries.length === 1 ? '' : 's'}`;
            }

            if (queries.length === 0) {
                queriesListContent.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 30px;">No user questions or searches recorded yet.</div>';
                return;
            }

            // Display in reverse chronological order (newest first)
            const reversed = [...queries].reverse();
            queriesListContent.innerHTML = "";

            reversed.forEach(item => {
                const row = document.createElement("div");
                row.style.background = "var(--bg-main)";
                row.style.border = "1px solid var(--border-color)";
                row.style.borderRadius = "8px";
                row.style.padding = "10px 14px";
                row.style.display = "flex";
                row.style.flexDirection = "column";
                row.style.gap = "4px";

                const dateStr = item.timestamp ? new Date(item.timestamp).toLocaleString() : "Unknown time";
                let typeBadge = "";
                if (item.type === "research") {
                    typeBadge = '<span style="background: #eff6ff; color:#1d4ed8; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;">Search Topic</span>';
                } else if (item.type === "followup_qa") {
                    typeBadge = '<span style="background: #f0fdf4; color:#15803d; border: 1px solid #bbf7d0; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;">Question</span>';
                } else if (item.type === "deepen") {
                    typeBadge = '<span style="background: #fffbeb; color:#b45309; border: 1px solid #fde68a; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;">Deepen</span>';
                } else {
                    typeBadge = `<span style="background: #f1f5f9; color:#475569; border: 1px solid #cbd5e1; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;">${escapeHtml(item.type || 'query')}</span>`;
                }

                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: var(--text-muted);">
                        <div style="display: flex; gap: 8px; align-items: center;">
                            ${typeBadge}
                            <span>IP: ${escapeHtml(item.client_ip || 'local')}</span>
                        </div>
                        <span>${escapeHtml(dateStr)}</span>
                    </div>
                    <div style="font-size: 0.92rem; color: var(--text-primary); font-weight: 500; word-break: break-word; margin-top: 4px;">
                        "${escapeHtml(item.query)}"
                    </div>
                `;
                queriesListContent.appendChild(row);
            });
        } catch (err) {
            queriesListContent.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 24px;">Failed to load activity logs: ${escapeHtml(err.message)}</div>`;
        }
    }

    // --- Model Providers & API Settings Modal ---
    const settingsBtn = document.getElementById("settingsBtn");
    const settingsModalOverlay = document.getElementById("settingsModalOverlay");
    const closeSettingsModalBtn = document.getElementById("closeSettingsModalBtn");
    const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");

    const inputGeminiKey = document.getElementById("inputGeminiKey");
    const inputOpenAIKey = document.getElementById("inputOpenAIKey");
    const inputGroqKey = document.getElementById("inputGroqKey");
    const inputOpenRouterKey = document.getElementById("inputOpenRouterKey");
    const inputCustomUrl = document.getElementById("inputCustomUrl");
    const inputCustomModel = document.getElementById("inputCustomModel");

    const statusTagGemini = document.getElementById("statusTagGemini");
    const statusTagOpenAI = document.getElementById("statusTagOpenAI");
    const statusTagGroq = document.getElementById("statusTagGroq");
    const statusTagOpenRouter = document.getElementById("statusTagOpenRouter");
    const statusTagCustom = document.getElementById("statusTagCustom");

    const clearGeminiBtn = document.getElementById("clearGeminiBtn");
    const clearOpenAIBtn = document.getElementById("clearOpenAIBtn");
    const clearGroqBtn = document.getElementById("clearGroqBtn");
    const clearOpenRouterBtn = document.getElementById("clearOpenRouterBtn");

    const settingsFeedback = document.getElementById("settingsFeedback");

    let keysToClear = {
        gemini: false,
        openai: false,
        groq: false,
        openrouter: false,
    };

    function showSettingsModal() {
        if (settingsModalOverlay) {
            settingsModalOverlay.classList.remove("hidden");
            loadSettingsKeys();
        }
    }

    function hideSettingsModal() {
        if (settingsModalOverlay) {
            settingsModalOverlay.classList.add("hidden");
            if (settingsFeedback) {
                settingsFeedback.className = "settings-feedback hidden";
                settingsFeedback.innerText = "";
            }
        }
    }

    if (settingsBtn) settingsBtn.addEventListener("click", showSettingsModal);
    if (closeSettingsModalBtn) closeSettingsModalBtn.addEventListener("click", hideSettingsModal);
    if (cancelSettingsBtn) cancelSettingsBtn.addEventListener("click", hideSettingsModal);

    async function loadSettingsKeys() {
        keysToClear = { gemini: false, openai: false, groq: false, openrouter: false };
        if (inputGeminiKey) inputGeminiKey.value = "";
        if (inputOpenAIKey) inputOpenAIKey.value = "";
        if (inputGroqKey) inputGroqKey.value = "";
        if (inputOpenRouterKey) inputOpenRouterKey.value = "";

        try {
            const res = await authFetch("/api/settings/keys");
            if (!res.ok) return;
            const data = await res.json();

            // Gemini
            if (data.gemini && data.gemini.configured) {
                if (statusTagGemini) {
                    statusTagGemini.innerText = `Configured (${data.gemini.masked})`;
                    statusTagGemini.classList.add("active");
                }
                if (inputGeminiKey) inputGeminiKey.placeholder = "Configured. Enter new key to replace...";
            } else {
                if (statusTagGemini) {
                    statusTagGemini.innerText = "Not Configured";
                    statusTagGemini.classList.remove("active");
                }
                if (inputGeminiKey) inputGeminiKey.placeholder = "AIzaSy... (free tier at ai.google.dev)";
            }

            // OpenAI
            if (data.openai && data.openai.configured) {
                if (statusTagOpenAI) {
                    statusTagOpenAI.innerText = `Configured (${data.openai.masked})`;
                    statusTagOpenAI.classList.add("active");
                }
                if (inputOpenAIKey) inputOpenAIKey.placeholder = "Configured. Enter new key to replace...";
            } else {
                if (statusTagOpenAI) {
                    statusTagOpenAI.innerText = "Not Configured";
                    statusTagOpenAI.classList.remove("active");
                }
                if (inputOpenAIKey) inputOpenAIKey.placeholder = "sk-proj-... (platform.openai.com)";
            }

            // Groq
            if (data.groq && data.groq.configured) {
                if (statusTagGroq) {
                    statusTagGroq.innerText = `Configured (${data.groq.masked})`;
                    statusTagGroq.classList.add("active");
                }
                if (inputGroqKey) inputGroqKey.placeholder = "Configured. Enter new key to replace...";
            } else {
                if (statusTagGroq) {
                    statusTagGroq.innerText = "Not Configured";
                    statusTagGroq.classList.remove("active");
                }
                if (inputGroqKey) inputGroqKey.placeholder = "gsk_... (console.groq.com)";
            }

            // OpenRouter
            if (data.openrouter && data.openrouter.configured) {
                if (statusTagOpenRouter) {
                    statusTagOpenRouter.innerText = `Configured (${data.openrouter.masked})`;
                    statusTagOpenRouter.classList.add("active");
                }
                if (inputOpenRouterKey) inputOpenRouterKey.placeholder = "Configured. Enter new key to replace...";
            } else {
                if (statusTagOpenRouter) {
                    statusTagOpenRouter.innerText = "Not Configured";
                    statusTagOpenRouter.classList.remove("active");
                }
                if (inputOpenRouterKey) inputOpenRouterKey.placeholder = "sk-or-... (openrouter.ai)";
            }

            // Custom LLM
            if (data.custom) {
                if (inputCustomUrl) inputCustomUrl.value = data.custom.url || "";
                if (inputCustomModel) inputCustomModel.value = data.custom.model || "";
                if (statusTagCustom) {
                    if (data.custom.configured) {
                        statusTagCustom.innerText = "Active";
                        statusTagCustom.classList.add("active");
                    } else {
                        statusTagCustom.innerText = "Optional";
                        statusTagCustom.classList.remove("active");
                    }
                }
            }
        } catch (err) {
            console.error("Failed to load settings:", err);
        }
    }

    function setupClearButton(btn, tag, input, providerKey) {
        if (!btn) return;
        btn.addEventListener("click", () => {
            keysToClear[providerKey] = true;
            if (input) {
                input.value = "";
                input.placeholder = "Marked for removal. Click 'Save Settings' to confirm.";
            }
            if (tag) {
                tag.innerText = "Will be removed";
                tag.classList.remove("active");
            }
        });
    }

    setupClearButton(clearGeminiBtn, statusTagGemini, inputGeminiKey, "gemini");
    setupClearButton(clearOpenAIBtn, statusTagOpenAI, inputOpenAIKey, "openai");
    setupClearButton(clearGroqBtn, statusTagGroq, inputGroqKey, "groq");
    setupClearButton(clearOpenRouterBtn, statusTagOpenRouter, inputOpenRouterKey, "openrouter");

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener("click", async () => {
            const payload = {};

            // Gemini
            if (keysToClear.gemini) {
                payload.gemini_api_key = "";
            } else if (inputGeminiKey && inputGeminiKey.value.trim()) {
                payload.gemini_api_key = inputGeminiKey.value.trim();
            }

            // OpenAI
            if (keysToClear.openai) {
                payload.openai_api_key = "";
            } else if (inputOpenAIKey && inputOpenAIKey.value.trim()) {
                payload.openai_api_key = inputOpenAIKey.value.trim();
            }

            // Groq
            if (keysToClear.groq) {
                payload.groq_api_key = "";
            } else if (inputGroqKey && inputGroqKey.value.trim()) {
                payload.groq_api_key = inputGroqKey.value.trim();
            }

            // OpenRouter
            if (keysToClear.openrouter) {
                payload.openrouter_api_key = "";
            } else if (inputOpenRouterKey && inputOpenRouterKey.value.trim()) {
                payload.openrouter_api_key = inputOpenRouterKey.value.trim();
            }

            // Custom LLM URL & Model
            if (inputCustomUrl) {
                payload.custom_llm_url = inputCustomUrl.value.trim();
            }
            if (inputCustomModel) {
                payload.custom_llm_model = inputCustomModel.value.trim();
            }

            saveSettingsBtn.disabled = true;
            saveSettingsBtn.innerText = "Saving...";

            try {
                const res = await authFetch("/api/settings/keys", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to save settings.");
                }

                if (settingsFeedback) {
                    settingsFeedback.className = "settings-feedback success";
                    settingsFeedback.innerText = "Settings saved successfully! Updating model choices...";
                    settingsFeedback.classList.remove("hidden");
                }

                // Refresh models dropdown
                await loadModels();

                setTimeout(() => {
                    hideSettingsModal();
                    saveSettingsBtn.disabled = false;
                    saveSettingsBtn.innerText = "Save Settings";
                }, 1000);
            } catch (err) {
                if (settingsFeedback) {
                    settingsFeedback.className = "settings-feedback error";
                    settingsFeedback.innerText = err.message || "Failed to save settings.";
                    settingsFeedback.classList.remove("hidden");
                }
                saveSettingsBtn.disabled = false;
                saveSettingsBtn.innerText = "Save Settings";
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
