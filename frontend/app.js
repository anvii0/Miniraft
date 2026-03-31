const canvas = document.getElementById('drawingBoard');
const ctx = canvas.getContext('2d');
const colorPicker = document.getElementById('colorPicker');
const brushSize = document.getElementById('brushSize');
const brushSizeVal = document.getElementById('brushSizeVal');
const clearBtn = document.getElementById('clearBtn');
const wsStatusDot = document.getElementById('wsStatusDot');
const wsStatusText = document.getElementById('wsStatusText');
const presetColors = document.querySelectorAll('.color-btn');

let currentColor = '#ffffff';
let currentSize = 4;
let isDrawing = false;
let lastX = 0;
let lastY = 0;

// Setup WebSocket
const WS_URL = window.location.hostname === 'localhost' 
    ? 'ws://localhost:8080' 
    : `ws://${window.location.hostname}:8080`;
let ws;

function connect() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        wsStatusDot.className = 'ping-dot connected';
        wsStatusText.innerText = 'Connected to RAFT';
    };

    ws.onclose = () => {
        wsStatusDot.className = 'ping-dot disconnected';
        wsStatusText.innerText = 'Disconnected (Retrying)';
        setTimeout(connect, parseInt(1000));
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'sync') {
            msg.strokes.forEach(strokeData => drawStroke(strokeData.stroke));
        } else if (msg.type === 'broadcast') {
            drawStroke(msg.stroke);
        }
    };
}

connect();

function resizeCanvas() {
    // Retain canvas content during resize
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    tempCtx.drawImage(canvas, 0, 0);

    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    ctx.drawImage(tempCanvas, 0, 0);
    
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
}

window.addEventListener('resize', resizeCanvas);
// Call initially to set size
setTimeout(resizeCanvas, 100);

// UI Event Listeners
colorPicker.addEventListener('input', (e) => {
    currentColor = e.target.value;
    updateActivePreset();
});

presetColors.forEach(btn => {
    btn.addEventListener('click', () => {
        currentColor = btn.dataset.color;
        colorPicker.value = currentColor;
        updateActivePreset(btn);
    });
});

function updateActivePreset(targetBtn = null) {
    presetColors.forEach(b => b.classList.remove('active'));
    if (targetBtn) {
        targetBtn.classList.add('active');
    } else {
        presetColors.forEach(b => {
            if (b.dataset.color.toLowerCase() === currentColor.toLowerCase()) {
                b.classList.add('active');
            }
        });
    }
}

brushSize.addEventListener('input', (e) => {
    currentSize = e.target.value;
    brushSizeVal.innerText = `${currentSize}px`;
});

clearBtn.addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
});

// Drawing Logic
function getCursorPos(e) {
    const rect = canvas.getBoundingClientRect();
    if (e.touches && e.touches.length > 0) {
        return {
            x: e.touches[0].clientX - rect.left,
            y: e.touches[0].clientY - rect.top
        };
    }
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
}

function startProcess(e) {
    e.preventDefault();
    isDrawing = true;
    const pos = getCursorPos(e);
    lastX = pos.x;
    lastY = pos.y;
}

function drawProcess(e) {
    if (!isDrawing) return;
    e.preventDefault();
    
    const pos = getCursorPos(e);
    
    const stroke = {
        x0: lastX / canvas.width,
        y0: lastY / canvas.height,
        x1: pos.x / canvas.width,
        y1: pos.y / canvas.height,
        color: currentColor,
        size: currentSize
    };

    // Draw locally instantly for zero-latency feel
    drawStroke(stroke);

    // Send to Gateway
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'draw', stroke }));
    }

    lastX = pos.x;
    lastY = pos.y;
}

function endProcess() {
    isDrawing = false;
}

// Draw a stroke given relative coordinates
function drawStroke(stroke) {
    ctx.beginPath();
    ctx.moveTo(parseFloat(stroke.x0) * canvas.width, parseFloat(stroke.y0) * canvas.height);
    ctx.lineTo(parseFloat(stroke.x1) * canvas.width, parseFloat(stroke.y1) * canvas.height);
    ctx.strokeStyle = stroke.color;
    ctx.lineWidth = parseInt(stroke.size);
    ctx.stroke();
    ctx.closePath();
}

// Mouse Events
canvas.addEventListener('mousedown', startProcess);
canvas.addEventListener('mousemove', drawProcess);
canvas.addEventListener('mouseup', endProcess);
canvas.addEventListener('mouseout', endProcess);

// Touch Events
canvas.addEventListener('touchstart', startProcess, {passive: false});
canvas.addEventListener('touchmove', drawProcess, {passive: false});
canvas.addEventListener('touchend', endProcess);
