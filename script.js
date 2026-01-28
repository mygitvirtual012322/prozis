document.addEventListener('DOMContentLoaded', () => {
    const wheel = document.getElementById('wheel');
    const spinBtn = document.getElementById('spinBtn');
    const lightsContainer = document.querySelector('.lights-container');
    const resultModal = document.getElementById('resultModal');
    const resultText = document.getElementById('resultText');

    let currentRotation = 0;
    let isSpinning = false;

    // --- Audio Context Setup (Singleton) ---
    // Uses AudioManager from audio-manager.js

    function playFanfare() {
        const audioCtx = AudioManager.getContext();
        if (!audioCtx) return;

        // C Major Arpeggio Fanfare (C4, E4, G4, C5)
        const notes = [261.63, 329.63, 392.00, 523.25, 392.00, 523.25]; // Sol, Do!
        const timing = [0, 0.15, 0.30, 0.45, 0.60, 0.9];
        const duration = [0.15, 0.15, 0.15, 0.15, 0.3, 0.8]; // Longer last notes

        const now = audioCtx.currentTime;

        notes.forEach((freq, i) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'square'; // Arcade/Casino style
            osc.frequency.setValueAtTime(freq, now + timing[i]);

            gain.gain.setValueAtTime(0.2, now + timing[i]);
            gain.gain.exponentialRampToValueAtTime(0.01, now + timing[i] + duration[i]);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(now + timing[i]);
            osc.stop(now + timing[i] + duration[i]);
        });
    }

    // --- Scarcity Logic ---
    function startTimer() {
        let timer = 300; // 5 min
        const el = document.getElementById('offer-timer');
        if (!el) return;
        setInterval(() => {
            let m = Math.floor(timer / 60);
            let s = timer % 60;
            el.innerText = `0${m}:${s < 10 ? '0' + s : s}`;
            if (timer > 0) timer--;
        }, 1000);
    }

    function updateProgress() {
        // SpinsLeft: 3 (start) -> 2 -> 1 -> 0 (win)
        let pct = 30;
        if (spinsLeft === 2) pct = 50;
        if (spinsLeft === 1) pct = 75;
        if (spinsLeft === 0) pct = 100;

        const bar = document.querySelector('.progress-fill');
        const text = document.querySelector('.progress-percent');
        if (bar) bar.style.width = pct + '%';
        if (text) text.innerText = pct + '%';
    }

    // Start Timer on load
    startTimer();

    // initAudio removed - handled by AudioManager

    function playTick() {
        const audioCtx = AudioManager.getContext();
        if (!audioCtx) return;

        // Create filtered noise burst for "clack" sound
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const filter = audioCtx.createBiquadFilter();

        // Realistic click sound synthesis
        osc.type = 'square';
        osc.frequency.setValueAtTime(150, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(40, audioCtx.currentTime + 0.08);

        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(3000, audioCtx.currentTime);
        filter.frequency.exponentialRampToValueAtTime(500, audioCtx.currentTime + 0.05);

        gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.05);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.05);
    }

    function playWin() {
        const audioCtx = AudioManager.getContext();
        if (!audioCtx) return;
        const now = audioCtx.currentTime;
        // Simple Fanfare: C E G C
        const notes = [523.25, 659.25, 783.99, 1046.50];

        notes.forEach((freq, i) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0.1, now + i * 0.1);
            gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.1 + 0.4);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(now + i * 0.1);
            osc.stop(now + i * 0.1 + 0.4);
        });
    }

    // --- Configuration ---
    const segments = [
        { id: 1, label: "VOUCHER 500€", type: "win" },
        { id: 2, label: "TENTA DE NOVO", type: "loss" },
        { id: 3, label: "IPHONE 15", type: "win" },
        { id: 4, label: "TENTA DE NOVO", type: "loss" },
        { id: 5, label: "MACBOOK AIR", type: "win" },
        { id: 6, label: "TENTA DE NOVO", type: "loss" },
        { id: 7, label: "PS5", type: "win" },
        { id: 8, label: "TENTA DE NOVO", type: "loss" }
    ];

    // --- Generate Lights on Rim ---
    const numberOfLights = 24;

    if (lightsContainer) {
        for (let i = 0; i < numberOfLights; i++) {
            const light = document.createElement('div');
            light.classList.add('light-bulb');
            // Angle step
            const angle = (360 / numberOfLights) * i;
            light.style.transform = `rotate(${angle}deg) translate(0, -165px)`;
            light.style.animationDelay = `${i * 0.1}s`;
            lightsContainer.appendChild(light);
        }
    }

    // --- Responsive Scale Logic ---
    function resizeWheel() {
        const wrapper = document.querySelector('.roulette-wrapper');
        if (!wrapper) return;

        const containerWidth = window.innerWidth;
        const baseWidth = 350; // Original width
        const padding = 40; // Safety margin

        if (containerWidth < (baseWidth + padding)) {
            const scale = (containerWidth - padding) / baseWidth;
            wrapper.style.transform = `scale(${scale})`;
        } else {
            wrapper.style.transform = `scale(1)`;
        }
    }

    // Init and Listen
    resizeWheel();
    window.addEventListener('resize', resizeWheel);

    // --- Spin Logic ---
    // --- Game State ---
    let spinsLeft = 3;
    const spinsCounterDisplay = document.getElementById('spinsLeftCount');

    // --- Init Audio (Updated for Celebration) ---
    // Keep existing initAudio, playTick

    function playCelebration() {
        const audioCtx = AudioManager.getContext();
        if (!audioCtx) return;
        const now = audioCtx.currentTime;
        // Victory Fanfare Sequence
        const notes = [
            523.25, 659.25, 783.99, 1046.50, // C E G C
            783.99, 1046.50 // G C
        ];
        const durations = [0.2, 0.2, 0.2, 0.6, 0.2, 0.8];
        let startTime = now;

        notes.forEach((freq, i) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'triangle'; // Brighter sound
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0.2, startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + durations[i] - 0.05);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(startTime);
            osc.stop(startTime + durations[i]);

            startTime += durations[i];
        });
    }

    // --- Spin Logic (Refactored) ---
    async function runSpin() {
        // Unlock Audio (Silent attempt)
        await AudioManager.unlock();

        if (isSpinning || spinsLeft <= 0) return;

        // Decrement Start
        isSpinning = true;
        spinBtn.disabled = true;
        spinBtn.style.opacity = "0.5";
        spinBtn.innerText = "A RODAR...";

        // LOGIC:
        // if spinsLeft == 3 -> Loss (Index 1: Tenta de Novo)
        // if spinsLeft == 2 -> Loss (Index 3: Tenta de Novo)
        // if spinsLeft == 1 -> Win (Index 0: Voucher 500€) [LAST SPIN]

        let winningGlobalIndex;
        if (spinsLeft === 3) winningGlobalIndex = 1;      // First Loss
        else if (spinsLeft === 2) winningGlobalIndex = 3; // Second Loss
        else winningGlobalIndex = 0;                      // Final Win

        // Decrement counter
        spinsLeft--;
        spinsCounterDisplay.innerText = spinsLeft;
        updateProgress();

        const minSpins = 5;
        const winningSegment = segments[winningGlobalIndex];

        // Rotation Math
        const centerAngle = winningGlobalIndex * 45 + 22.5;
        let targetRotation = 360 - centerAngle;
        const jitter = Math.floor(Math.random() * 20) - 10; // +/- 10deg
        targetRotation += jitter;

        const spinadds = minSpins * 360;
        const currentMod = currentRotation % 360;
        let dist = targetRotation - currentMod;
        if (dist < 0) dist += 360;

        const totalDegree = spinadds + dist;

        // Ticking Sound Logic
        let lastAngle = currentRotation;
        const step = 45;
        function trackTicks() {
            if (!isSpinning) return;
            const style = window.getComputedStyle(wheel);
            const matrix = new DOMMatrix(style.transform);
            let angle = Math.atan2(matrix.b, matrix.a) * (180 / Math.PI);
            if (angle < 0) angle += 360;

            let delta = angle - (lastAngle % 360);
            if (delta < -180) delta += 360;
            if (delta > 180) delta -= 360;

            if (Math.abs(delta) > 0) {
                // Check segment crossing
                const currentSeg = Math.floor(angle / step);
                const lastSeg = Math.floor((lastAngle % 360) / step);
                if (currentSeg !== lastSeg) playTick();
            }
            lastAngle = angle;
            requestAnimationFrame(trackTicks);
        }
        requestAnimationFrame(trackTicks);

        currentRotation += totalDegree;
        wheel.style.transform = `rotate(${currentRotation}deg)`;

        // Show Result
        setTimeout(() => {
            isSpinning = false;
            spinBtn.disabled = false;
            spinBtn.style.opacity = "1";
            spinBtn.innerText = spinsLeft > 0 ? "RODA AGORA!" : "PRÉMIO DESBLOQUEADO!";

            showResult(winningSegment);
        }, 6500);
    }

    if (spinBtn) {
        spinBtn.addEventListener('click', runSpin);
    }

    // Global exposure for Modal Retry
    window.retrySpin = () => {
        const modal = document.getElementById('resultModal');
        modal.classList.add('hidden');
        runSpin();
    };

    window.closeModal = () => {
        // If spinsLeft is 0, we found the prize. We might want to NOT allow closing
        // or if we do, the button remains 'Levantar Prémio'.
        // For now, allow closing to see the board, but the CTA remains in modal.
        resultModal.classList.add('hidden');
    }

    function showResult(segment) {
        const modalBtn = document.querySelector('#resultModal button');
        const modalH2 = document.querySelector('#resultModal h2'); // More specific selector

        if (segment.type === 'win') {
            // CELEBRATION
            playFanfare();
            playCelebration();
            confetti({
                particleCount: 150,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#d32f2f', '#ffcc00', '#ffffff'],
                zIndex: 9999
            });

            resultText.innerHTML = `PARABÉNS!<br>GANHASTE: <strong>${segment.label}</strong>`;
            modalH2.innerText = "VITÓRIA ÉPICA!";
            modalH2.style.color = "#4CAF50";

            modalBtn.innerText = "LEVANTAR PRÉMIO";
            modalBtn.style.background = "#d32f2f";
            modalBtn.classList.add("pulse-button"); // Add pulsing effect

            // Redirect on click
            modalBtn.onclick = () => {
                window.location.href = 'voucher.html';
            };

            // Disable further spins UI if needed, though logic handles it
            if (spinsLeft === 0) {
                spinBtn.innerText = "JÁ GANHASTE!";
                spinBtn.disabled = true;
                spinBtn.style.pointerEvents = "none";
            }

        } else {
            // Loss
            resultText.innerHTML = `Não foi desta vez.<br>Tens mais <strong>${spinsLeft}</strong> tentativas!`;
            modalH2.innerText = "OH, QUE PENA...";
            modalH2.style.color = "#d32f2f";

            modalBtn.innerText = "RODA OUTRA VEZ";
            modalBtn.style.background = "#555";
            modalBtn.classList.remove("pulse-button");

            // Auto Spin on Click
            modalBtn.onclick = () => {
                window.retrySpin();
            };
        }

        resultModal.classList.remove('hidden');
    }
    // --- Social Proof Logic ---
    // --- Social Proof Logic ---
    const names = [
        "Maria S.", "João P.", "Ana R.", "Pedro M.", "Sofia L.", "Rui C.",
        "Carla F.", "Tiago A.", "Luísa M.", "Gonçalo B.", "Beatriz D.",
        "André S.", "Inês C.", "Bruno V.", "Mariana T.", "Diogo R."
    ];
    const prizes = ["VOUCHER 500€", "IPHONE 15", "VOUCHER 500€", "PS5", "MACBOOK AIR"];
    const winnersList = document.getElementById('winnersList');

    // Track recent names to avoid duplicates on screen
    let usedNames = [];

    function createWinner() {
        if (!winnersList) return;

        // Get available names (exclude used ones)
        let availableNames = names.filter(n => !usedNames.includes(n));
        if (availableNames.length === 0) {
            // Reset if all used (should be rare with big list and short history)
            usedNames = [];
            availableNames = names;
        }

        const name = availableNames[Math.floor(Math.random() * availableNames.length)];

        // Add to used list
        usedNames.push(name);
        if (usedNames.length > 5) usedNames.shift(); // Keep only last 5 in memory

        const prize = prizes[Math.floor(Math.random() * prizes.length)];
        const time = Math.floor(Math.random() * 5) + 1; // 1-5 min ago

        const card = document.createElement('div');
        card.classList.add('winner-card');
        card.innerHTML = `
            <div class="winner-avatar">${name.charAt(0)}</div>
            <div class="winner-info">
                <strong>${name}</strong> acabou de ganhar<br>
                <span style="color: #d32f2f; font-weight: 800;">${prize}</span>
            </div>
            <div class="winner-time">há ${time} min</div>
            <svg class="verified-badge" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;

        winnersList.prepend(card);

        // Keep only top 3
        if (winnersList.children.length > 3) {
            winnersList.lastElementChild.remove();
        }
    }

    // Initial batch
    createWinner();
    createWinner();

    // Add new ones periodically
    setInterval(createWinner, 4000 + Math.random() * 3000);

});

// --- Legal Modals Logic (Global) ---
window.openLegal = (type) => {
    const modal = document.getElementById('legalModal');
    const title = document.getElementById('legalTitle');
    const body = document.getElementById('legalBody');

    if (type === 'privacy') {
        title.innerText = "Política de Privacidade";
        body.innerHTML = `
            <p><strong>1. Responsável pelo Tratamento:</strong> A Worten - Equipamentos para o Lar, S.A. é a responsável pelo tratamento dos seus dados pessoais.</p>
            <p><strong>2. Finalidade:</strong> Os dados recolhidos nesta campanha destinam-se exclusivamente à validação da titularidade para atribuição de prémios e prevenção de fraude.</p>
            <p><strong>3. Partilha:</strong> Os seus dados não serão partilhados com terceiros para fins de marketing, exceto parceiros estritamente necessários para a entrega do prémio.</p>
            <p><strong>4. Segurança:</strong> Utilizamos protocolos SSL/TLS para garantir a segurança da transmissão de dados.</p>
            <p><strong>5. Direitos:</strong> Pode exercer os seus direitos de acesso, retificação ou eliminação contactando-nos através dos canais oficiais.</p>
        `;
    } else {
        title.innerText = "Termos e Condições";
        body.innerHTML = `
            <p><strong>1. Elegibilidade:</strong> Esta campanha é exclusiva para clientes selecionados com residência em Portugal Continental.</p>
            <p><strong>2. Prémios:</strong> Os prémios são pessoais e intransmissíveis. vouchers têm validade de 12 meses.</p>
            <p><strong>3. Validação:</strong> Para combater fraudes, é exigida uma validação de identidade (custo de 9€ estornável) via Multibanco ou MB WAY.</p>
            <p><strong>4. Entrega:</strong> Prémios físicos são enviados em até 5 dias úteis. Vouchers digitais em até 24h após validação.</p>
            <p><strong>5. Fraude:</strong> Qualquer tentativa de manipulação resultará na anulação do prémio.</p>
        `;
    }

    modal.style.display = 'flex';
}

window.closeLegal = () => {
    document.getElementById('legalModal').style.display = 'none';
}

// Close on outside click
// --- Dynamic Background Logic (Wrapped to run after DOM load) ---
document.addEventListener('DOMContentLoaded', () => {
    const bgContainer = document.getElementById('dynamicBg');
    const icons = ['🎰', '🍀', '💎', '💰', '7️⃣', '🎲'];

    function spawnIcon() {
        if (!bgContainer) return;
        const icon = document.createElement('div');
        icon.classList.add('floating-icon');
        icon.innerText = icons[Math.floor(Math.random() * icons.length)];

        // Random Position X
        icon.style.left = Math.random() * 100 + 'vw';
        // Random Size
        const size = Math.floor(Math.random() * 30) + 15; // 15-45px
        icon.style.fontSize = size + 'px';
        // Random Duration
        const duration = Math.floor(Math.random() * 10) + 10; // 10-20s
        icon.style.animationDuration = duration + 's';

        bgContainer.appendChild(icon);

        // Cleanup
        setTimeout(() => {
            icon.remove();
        }, duration * 1000);
    }

    // Spawn initial batch
    if (bgContainer) {
        for (let i = 0; i < 15; i++) {
            setTimeout(spawnIcon, Math.random() * 5000);
        }
        // Continuous spawn
        setInterval(spawnIcon, 800);
    }
    // --- Global Audio Unlock Logic (Main Page) ---
    // No longer using createUnlockOverlay, AudioManager.unlock() is called on first interaction.

});

// --- Onboarding Modal Logic ---
window.closeOnboarding = () => {
    const modal = document.getElementById('onboardingModal');
    if (modal) {
        modal.style.opacity = '0';
        modal.style.transition = 'opacity 0.5s ease';
        setTimeout(() => {
            modal.style.display = 'none';
        }, 500);
    }
}
// Trigger celebration on load (optional, maybe too much? let's stick to modal pop)

window.onclick = function (event) {
    const modal = document.getElementById('legalModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}
