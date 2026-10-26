// static/app.js
// Client logic for Necromancer Séance Console & Ofrenda Viewer

document.addEventListener("DOMContentLoaded", () => {
    const repoInput = document.getElementById("repoInput");
    const btnExhume = document.getElementById("btnExhume");
    const exhumeForm = document.getElementById("exhumeForm");
    const terminal = document.getElementById("consoleTerminal");
    const tombstoneCard = document.getElementById("tombstoneCard");
    const vitalTimer = document.getElementById("vitalTimer");
    const vitalSteps = document.getElementById("vitalSteps");
    const timeMachineSlider = document.getElementById("timeMachineSlider");
    const sliderOutput = document.getElementById("sliderOutput");
    const btnViewOfrenda = document.getElementById("btnViewOfrenda");
    const btnDownloadHtml = document.getElementById("btnDownloadHtml");
    const ofrendaModal = document.getElementById("ofrendaModal");
    const btnCloseModal = document.getElementById("btnCloseModal");
    const ofrendaFrame = document.getElementById("ofrendaFrame");

    let activeOfrendaHtml = "";
    let startTime = null;
    let timerInterval = null;

    // Time-Machine Slider updates
    const eraMap = {
        2008: "<strong>Year 2008:</strong> Python 2.7 legacy era. print statements without parens, distutils, SVN/Mercurial conversions.",
        2012: "<strong>Year 2012:</strong> Sunset begins. Early virtualenv, pip 1.x, setuptools bootstrapping.",
        2015: "<strong>Year 2015:</strong> Early Python 3 (3.5). asyncio introduction, __future__ compatibility layers.",
        2018: "<strong>Year 2018:</strong> PEP 517 build isolation introduction, wheel standardization.",
        2020: "<strong>Year 2020:</strong> Mature Python 3.8. Python 2 officially End-Of-Life. collections.abc transition.",
        2026: "<strong>Year 2026 (Modern):</strong> Contemporary packaging (PEP 621, pyproject.toml) & pytest runner. 100% test integrity."
    };

    timeMachineSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        let closestYear = 2026;
        let minDiff = 999;
        for (const yr of [2008, 2012, 2015, 2018, 2020, 2026]) {
            const diff = Math.abs(yr - val);
            if (diff < minDiff) {
                minDiff = diff;
                closestYear = yr;
            }
        }
        sliderOutput.innerHTML = eraMap[closestYear];
    });

    function logTerminal(text, type = "normal") {
        const line = document.createElement("div");
        line.className = `terminal-line ${type}`;
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }

    function startTimer() {
        startTime = Date.now();
        timerInterval = setInterval(() => {
            const sec = ((Date.now() - startTime) / 1000).toFixed(1);
            vitalTimer.textContent = `⏱️ ${sec}s`;
        }, 100);
    }

    function stopTimer() {
        if (timerInterval) clearInterval(timerInterval);
    }

    // 1. Exhume Tombstone
    btnExhume.addEventListener("click", async () => {
        const repo = repoInput.value.trim();
        if (!repo) return alert("Please specify a repository path or URL");

        logTerminal(`Exhuming tombstone for: ${repo}...`, "system");
        try {
            const res = await fetch("/api/exhume", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_path: repo })
            });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();

            // Populate tombstone card
            document.getElementById("tsName").textContent = data.repo_name;
            document.getElementById("tsLang").textContent = data.primary_language;
            document.getElementById("tsDormant").textContent = data.dormant_years.toFixed(1);
            document.getElementById("tsCommits").textContent = data.total_commits;
            document.getElementById("tsAuthor").textContent = data.top_contributors.length > 0 ? data.top_contributors[0].name : "Unknown";
            tombstoneCard.classList.remove("hidden");

            logTerminal(`Exhumation complete. Found ${data.total_commits} commits dormant for ${data.dormant_years} years.`, "success");
        } catch (err) {
            logTerminal(`Exhumation error: ${err.message}`, "error");
        }
    });

    // 2. Begin Séance (Resurrect)
    exhumeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const repo = repoInput.value.trim();
        const strategy = document.querySelector('input[name="strategy"]:checked').value;

        terminal.innerHTML = "";
        btnViewOfrenda.classList.add("hidden");
        btnDownloadHtml.classList.add("hidden");

        logTerminal(`Commencing Séance for '${repo}' with strategy: ${strategy}`, "system");
        startTimer();

        // Connect WebSocket for live streaming
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/seance`;
        let ws;

        try {
            ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                ws.send(JSON.stringify({ repo_path: repo, strategy: strategy }));
            };
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === "step") {
                    vitalSteps.textContent = `🪜 Step ${msg.step_number}`;
                    logTerminal(`[${msg.action}] ${msg.thought}`, "thought");
                    if (msg.tool_call) logTerminal(`  -> ${msg.tool_call}`, "tool");
                    if (msg.observation) logTerminal(`  <- ${msg.observation}`, "normal");
                } else if (msg.type === "complete") {
                    stopTimer();
                    if (msg.success) {
                        logTerminal(`✨ Resurrection Complete! All test invariants verified.`, "success");
                    } else {
                        logTerminal(`⚠️ Séance halted: ${msg.error_message}`, "error");
                    }
                    if (msg.ofrenda_html) {
                        activeOfrendaHtml = msg.ofrenda_html;
                        btnViewOfrenda.classList.remove("hidden");
                        btnDownloadHtml.classList.remove("hidden");
                    }
                }
            };
            ws.onerror = (err) => {
                logTerminal("WebSocket connection closed or fallback to HTTP REST API...", "muted");
                runHttpResurrect(repo, strategy);
            };
        } catch (e) {
            runHttpResurrect(repo, strategy);
        }
    });

    async function runHttpResurrect(repo, strategy) {
        try {
            const res = await fetch("/api/resurrect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_path: repo, strategy: strategy })
            });
            stopTimer();
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            
            data.steps.forEach(s => {
                logTerminal(`[Step ${s.step_number} - ${s.action}] ${s.thought}`, "thought");
                if (s.observation) logTerminal(`  <- ${s.observation}`, "normal");
            });

            if (data.success) {
                logTerminal("✨ Resurrection succeeded via REST harness!", "success");
            } else {
                logTerminal(`Séance result: ${data.error_message}`, "error");
            }

            // Fetch Ofrenda
            const ofrendaRes = await fetch("/api/ofrenda", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_path: repo, generate_audio: true })
            });
            if (ofrendaRes.ok) {
                const ofrendaData = await ofrendaRes.json();
                activeOfrendaHtml = ofrendaData.html;
                btnViewOfrenda.classList.remove("hidden");
                btnDownloadHtml.classList.remove("hidden");
            }
        } catch (err) {
            stopTimer();
            logTerminal(`Séance execution error: ${err.message}`, "error");
        }
    }

    // Modal controls
    btnViewOfrenda.addEventListener("click", () => {
        if (!activeOfrendaHtml) return;
        ofrendaFrame.srcdoc = activeOfrendaHtml;
        ofrendaModal.classList.remove("hidden");
    });

    btnCloseModal.addEventListener("click", () => {
        ofrendaModal.classList.add("hidden");
        ofrendaFrame.srcdoc = "about:blank";
    });

    // Download HTML
    btnDownloadHtml.addEventListener("click", () => {
        if (!activeOfrendaHtml) return;
        const blob = new Blob([activeOfrendaHtml], { type: "text/html" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `ofrenda-${Date.now()}.html`;
        a.click();
    });
});
