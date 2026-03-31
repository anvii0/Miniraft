const express = require('express');
const axios = require('axios');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

// Serve the frontend locally from the Gateway just in case
app.use(express.static(path.join(__dirname, 'frontend')));

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const REPLICAS = [
    'http://node1:5000',
    'http://node2:5000',
    'http://node3:5000'
];

let cachedLeader = null;

// Probe to find current leader
async function findLeader() {
    for (const replica of REPLICAS) {
        try {
            const res = await axios.get(`${replica}/status`, { timeout: 1000 });
            if (res.data.state === 'LEADER') {
                cachedLeader = replica;
                console.log(`[Gateway] Found Leader: ${cachedLeader}`);
                return cachedLeader;
            }
        } catch (err) {
            // Node might be down, ignore
        }
    }
    console.log(`[Gateway] ⚠️ No leader found!`);
    cachedLeader = null;
    return null;
}

// Ensure leader is updated periodically
setInterval(findLeader, 2000);

// Proxy drawing stroke to Leader
async function sendToLeader(strokeData) {
    if (!cachedLeader) await findLeader();
    if (!cachedLeader) return false;

    try {
        await axios.post(`${cachedLeader}/draw`, { stroke: strokeData }, { timeout: 1500 });
        return true;
    } catch (err) {
        console.log(`[Gateway] Error sending to leader. Requesting new leader election...`);
        cachedLeader = null;
        return false;
    }
}

// WebSocket connections
wss.on('connection', (ws) => {
    console.log('[Gateway] New client connected via WebSocket');
    
    // Attempt to send initial canvas state (catch up the client)
    async function syncClient() {
        if (!cachedLeader) await findLeader();
        if (cachedLeader) {
            try {
                const res = await axios.get(`${cachedLeader}/history`, { timeout: 2000 });
                ws.send(JSON.stringify({ type: 'sync', strokes: res.data.strokes }));
            } catch (err) {
                console.log("[Gateway] Could not fetch initial history for client");
            }
        }
    }
    syncClient();

    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            if (data.type === 'draw') {
                // Send stroke to backend RAFT
                const success = await sendToLeader(data.stroke);
                if (!success) {
                    console.error("[Gateway] Failed to commit stroke to RAFT cluster");
                    // Optionally notify client that stroke failed
                }
            }
        } catch (e) {
            console.error("Invalid WS message", e);
        }
    });

    ws.on('close', () => {
        console.log('[Gateway] Client disconnected');
    });
});

// Broadcast Webhook (called by the leader when it successfully commits)
app.post('/internal/broadcast', (req, res) => {
    const strokeEntry = req.body; 
    // strokeEntry = { "term": ... , "stroke": { ... } }
    
    // Broadcast to all WS clients
    const payload = JSON.stringify({ type: 'broadcast', stroke: strokeEntry.stroke });
    
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(payload);
        }
    });
    
    res.status(200).send('OK');
});

const PORT = 8080;
server.listen(PORT, async () => {
    console.log(`🚀 Gateway Server running on port ${PORT}`);
    await findLeader();
});
