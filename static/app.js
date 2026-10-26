// static/app.js
// Client logic for Necromancer Séance Console & Ofrenda Viewer
// Includes Web Audio atmospheric synthesizer, mist canvas, and ElevenLabs voice player

document.addEventListener("DOMContentLoaded", () => {
    const repoInput = document.getElementById("repoInput");
    const btnExhume = document.getElementById("btnExhume");
    const btnResurrect = document.getElementById("btnResurrect");
    const btnLoadDemo = document.getElementById("btnLoadDemo");
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

    // Audio & Sound Controls
    const btnToggleSound = document.getElementById("btnToggleSound");
    const soundIcon = document.getElementById("soundIcon");
    const soundLabel = document.getElementById("soundLabel");
    const btnPlaySampleEulogy = document.getElementById("btnPlaySampleEulogy");
    const heroAudioPlayer = document.getElementById("heroAudioPlayer");
    const eulogyPlayingNotice = document.getElementById("eulogyPlayingNotice");

    let activeOfrendaHtml = "";
    let startTime = null;
    let timerInterval = null;

    // ==========================================
    // 1. PROCEDURAL WEB AUDIO ENGINE (Drone & Bells)
    // ==========================================
    let audioCtx = null;
    let droneOsc1 = null;
    let droneOsc2 = null;
    let droneGain = null;
    let isSoundOn = false;

    function initAudioContext() {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioContextClass();
        }
        if (audioCtx.state === "suspended") {
            audioCtx.resume();
        }
    }

    function startAtmosphericDrone() {
        try {
            initAudioContext();
            droneGain = audioCtx.createGain();
            droneGain.gain.setValueAtTime(0.001, audioCtx.currentTime);
            droneGain.gain.exponentialRampToValueAtTime(0.08, audioCtx.currentTime + 3.0);

            // Low drone 55Hz (A1)
            droneOsc1 = audioCtx.createOscillator();
            droneOsc1.type = "sawtooth";
            droneOsc1.frequency.setValueAtTime(55, audioCtx.currentTime);

            // Sub-harmonic drone 110Hz (A2) with slight detune
            droneOsc2 = audioCtx.createOscillator();
            droneOsc2.type = "sine";
            droneOsc2.frequency.setValueAtTime(110.5, audioCtx.currentTime);

            // Lowpass filter for dark gothic ambience
            const filter = audioCtx.createBiquadFilter();
            filter.type = "lowpass";
            filter.frequency.setValueAtTime(180, audioCtx.currentTime);

            droneOsc1.connect(filter);
            droneOsc2.connect(filter);
            filter.connect(droneGain);
            droneGain.connect(audioCtx.destination);

            droneOsc1.start();
            droneOsc2.start();
            isSoundOn = true;
            soundIcon.textContent = "🔊";
            soundLabel.textContent = "Atmospheric Drone & Bells: ON";
            btnToggleSound.classList.add("active");
            logTerminal("Atmospheric crypt drone awakened...", "system");
        } catch (e) {
            console.warn("Audio init failed:", e);
        }
    }

    function stopAtmosphericDrone() {
        if (droneGain && audioCtx) {
            try {
                droneGain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 1.0);
                setTimeout(() => {
                    if (droneOsc1) { droneOsc1.stop(); droneOsc1.disconnect(); }
                    if (droneOsc2) { droneOsc2.stop(); droneOsc2.disconnect(); }
                    droneOsc1 = null;
                    droneOsc2 = null;
                    droneGain = null;
                }, 1000);
            } catch (e) {}
        }
        isSoundOn = false;
        soundIcon.textContent = "🔇";
        soundLabel.textContent = "Atmospheric Drone & Bells: OFF";
        btnToggleSound.classList.remove("active");
    }

    function playBellToll() {
        if (!isSoundOn) return;
        try {
            initAudioContext();
            const now = audioCtx.currentTime;
            const freqs = [220, 440, 554.37, 659.25]; // Eerie A Minor bell harmonics
            freqs.forEach((freq, idx) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq * (1 + (Math.random() - 0.5) * 0.02), now);

                gain.gain.setValueAtTime(0.07 / (idx + 1), now);
                gain.gain.exponentialRampToValueAtTime(0.00001, now + 3.5);

                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(now);
                osc.stop(now + 3.6);
            });
        } catch (e) {}
    }

    if (btnToggleSound) {
        btnToggleSound.addEventListener("click", () => {
            if (!isSoundOn) {
                startAtmosphericDrone();
            } else {
                stopAtmosphericDrone();
            }
        });
    }

    // ==========================================
    // 2. GHOSTLY MIST CANVAS
    // ==========================================
    const canvas = document.getElementById("mistCanvas");
    if (canvas) {
        const ctx = canvas.getContext("2d");
        let w = (canvas.width = window.innerWidth);
        let h = (canvas.height = window.innerHeight);

        window.addEventListener("resize", () => {
            w = canvas.width = window.innerWidth;
            h = canvas.height = window.innerHeight;
        });

        const particles = Array.from({ length: 35 }, () => ({
            x: Math.random() * w,
            y: Math.random() * h,
            radius: 80 + Math.random() * 120,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.2,
            alpha: 0.03 + Math.random() * 0.05
        }));

        function drawMist() {
            ctx.clearRect(0, 0, w, h);
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < -p.radius) p.x = w + p.radius;
                if (p.x > w + p.radius) p.x = -p.radius;
                if (p.y < -p.radius) p.y = h + p.radius;
                if (p.y > h + p.radius) p.y = -p.radius;

                const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius);
                grad.addColorStop(0, `rgba(255, 117, 24, ${p.alpha})`);
                grad.addColorStop(0.5, `rgba(155, 81, 224, ${p.alpha * 0.5})`);
                grad.addColorStop(1, "rgba(7, 8, 11, 0)");

                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fill();
            });
            requestAnimationFrame(drawMist);
        }
        drawMist();
    }

    // ==========================================
    // 3. ELEVENLABS GHOST VOICE SAMPLE PREVIEW
    // ==========================================
    if (btnPlaySampleEulogy) {
        btnPlaySampleEulogy.addEventListener("click", async () => {
            playBellToll();
            btnPlaySampleEulogy.disabled = true;
            btnPlaySampleEulogy.innerHTML = "<span>⏳ Summoning Ghost Audio...</span>";
            logTerminal("Contacting ElevenLabs API for spoken eulogy...", "system");

            try {
                const res = await fetch("/api/eulogy/sample");
                if (!res.ok) throw new Error(await res.text());
                const data = await res.json();

                if (data.audio_uri) {
                    heroAudioPlayer.src = data.audio_uri;
                    heroAudioPlayer.classList.remove("hidden-audio");
                    heroAudioPlayer.play();
                    eulogyPlayingNotice.classList.remove("hidden");

                    heroAudioPlayer.onended = () => {
                        eulogyPlayingNotice.classList.add("hidden");
                    };

                    logTerminal(`🎙️ ElevenLabs Spoken Eulogy playing: "${data.eulogy_text}"`, "success");
                } else {
                    logTerminal("No audio URI received from ElevenLabs synthesizer.", "error");
                }
            } catch (err) {
                logTerminal(`ElevenLabs eulogy error: ${err.message}`, "error");
            } finally {
                btnPlaySampleEulogy.disabled = false;
                btnPlaySampleEulogy.innerHTML = "<span class='audio-btn-icon'>▶️</span><span>Hear ElevenLabs Spoken Eulogy Preview</span>";
            }
        });
    }

    // ==========================================
    // 4. GUIDED DEMO QUICK-LOAD BUTTON
    // ==========================================
    if (btnLoadDemo) {
        btnLoadDemo.addEventListener("click", () => {
            playBellToll();
            repoInput.value = "https://github.com/satanic47/necromancer.git";
            logTerminal("✨ Guided Demo: Loaded vintage repository 'https://github.com/satanic47/necromancer.git'", "system");
            logTerminal("Triggering automatic tombstone exhumation to identify original git author...", "thought");
            btnExhume.click();
        });
    }

    // ==========================================
    // 5. TIME-MACHINE SLIDER UPDATES
    // ==========================================
    const eraMap = {
        2008: "<strong>Year 2008:</strong> Python 2.7 legacy era. print statements without parens, distutils, SVN/Mercurial conversions.",
        2012: "<strong>Year 2012:</strong> Sunset begins. Early virtualenv, pip 1.x, setuptools bootstrapping.",
        2015: "<strong>Year 2015:</strong> Early Python 3 (3.5). asyncio introduction, __future__ compatibility layers.",
        2018: "<strong>Year 2018:</strong> PEP 517 build isolation introduction, wheel standardization.",
        2020: "<strong>Year 2020:</strong> Mature Python 3.8. Python 2 officially End-Of-Life. collections.abc transition.",
        2026: "<strong>Year 2026 (Modern):</strong> Contemporary packaging (PEP 621, pyproject.toml) & pytest runner. 100% test integrity."
    };

    if (timeMachineSlider) {
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
    }

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

    // ==========================================
    // 6. EXHUME TOMBSTONE
    // ==========================================
    btnExhume.addEventListener("click", async () => {
        playBellToll();
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
            document.getElementById("tsDormant").textContent = (data.dormant_years || 8.5).toFixed(1);
            document.getElementById("tsCommits").textContent = data.total_commits || 47;
            
            const author = (data.top_contributors && data.top_contributors.length > 0)
                ? data.top_contributors[0].name
                : "Open Source Contributor";
            document.getElementById("tsAuthor").textContent = author;
            tombstoneCard.classList.remove("hidden");

            logTerminal(`Exhumation complete. Found ${data.total_commits} commits. Lead Creator: ${author}.`, "success");
        } catch (err) {
            logTerminal(`Exhumation error: ${err.message}`, "error");
        }
    });

    // ==========================================
    // 7. BEGIN SÉANCE (RESURRECTION)
    // ==========================================
    exhumeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        playBellToll();
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
                    playBellToll();
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
                logTerminal("WebSocket fallback to HTTP REST API...", "muted");
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
            
            if (data.steps && Array.isArray(data.steps)) {
                data.steps.forEach(s => {
                    logTerminal(`[Step ${s.step_number} - ${s.action}] ${s.thought}`, "thought");
                    if (s.observation) logTerminal(`  <- ${s.observation}`, "normal");
                });
            }

            if (data.success) {
                playBellToll();
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

    // ==========================================
    // 8. MODAL & OFRENDA ACTIONS
    // ==========================================
    btnViewOfrenda.addEventListener("click", () => {
        playBellToll();
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
