import express from 'express';
import https from 'https';
import fs from 'fs';
import { WebSocketServer, WebSocket } from 'ws';
import cors from 'cors';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';
import { generateCertificates } from './generateCerts.js';
import {
  initCSVWriter,
  appendSensorReading,
  setRecordingState,
  getRecordingState,
  getRowCount,
  getCSVPath,
  clearCSV
} from './csvWriter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 3001;

const app = express();
app.use(cors());
app.use(express.json());

// Load or Generate SSL Certificates
const { cert, key } = generateCertificates();

// Initialize CSV Writer
initCSVWriter();

// Helper to get laptop's local LAN IP addresses
function getLanIps() {
  const interfaces = os.networkInterfaces();
  const ips = [];
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        ips.push({ interface: name, address: iface.address });
      }
    }
  }
  return ips;
}

const startTime = new Date().toISOString();
let totalPacketsReceived = 0;
let latestSensorReading = null;

// Create HTTPS Server
const server = https.createServer({ key, cert }, app);

// Create WebSocket Server attached to HTTPS server
const wss = new WebSocketServer({ server });

// Active socket sets & phone metadata
const phoneClients = new Set();
const dashboardClients = new Set();
let connectedPhoneDetails = null;

wss.on('connection', (ws, req) => {
  const url = req.url || '';
  const clientIp = req.socket.remoteAddress || 'unknown';
  console.log(`[WebSocket] Client connected from ${clientIp} (URL: ${url})`);

  ws.clientType = url.includes('type=dashboard') ? 'dashboard' : 'phone';

  if (ws.clientType === 'dashboard') {
    dashboardClients.add(ws);
  } else {
    phoneClients.add(ws);
  }

  // Send initial system state
  ws.send(JSON.stringify({
    type: 'SYSTEM_INIT',
    recording: getRecordingState(),
    rowCount: getRowCount(),
    packetsReceived: totalPacketsReceived,
    lanIps: getLanIps(),
    phoneConnected: phoneClients.size > 0,
    connectedPhoneDetails
  }));

  broadcastSystemStatus();

  ws.on('message', (message) => {
    try {
      const parsed = JSON.parse(message.toString());

      if (parsed.type === 'REGISTER_TYPE') {
        if (parsed.clientType === 'dashboard') {
          phoneClients.delete(ws);
          dashboardClients.add(ws);
          ws.clientType = 'dashboard';
        } else {
          dashboardClients.delete(ws);
          phoneClients.add(ws);
          ws.clientType = 'phone';
          if (parsed.phoneDetails) {
            connectedPhoneDetails = parsed.phoneDetails;
          }
        }
        broadcastSystemStatus();
        return;
      }

      if (parsed.type === 'PHONE_INFO') {
        connectedPhoneDetails = parsed.phoneDetails || { userAgent: req.headers['user-agent'] };
        broadcastSystemStatus();
        return;
      }

      if (parsed.type === 'PING') {
        ws.send(JSON.stringify({ type: 'PONG', timestamp: new Date().toISOString() }));
        return;
      }

      // Handle Sensor Data Payload
      if (parsed.timestamp && (parsed.accelerometer !== undefined || parsed.gyroscope !== undefined || parsed.orientation !== undefined || parsed.gps !== undefined || parsed.magnetometer !== undefined)) {
        totalPacketsReceived++;
        const serverReceivedTimestamp = new Date().toISOString();
        latestSensorReading = {
          ...parsed,
          server_received_timestamp: serverReceivedTimestamp
        };

        // Append to CSV file
        appendSensorReading(parsed, serverReceivedTimestamp);

        // Broadcast to dashboard
        const broadcastPayload = JSON.stringify({
          type: 'SENSOR_DATA',
          data: latestSensorReading,
          rowCount: getRowCount(),
          totalPacketsReceived
        });

        for (const dashWs of dashboardClients) {
          if (dashWs.readyState === WebSocket.OPEN) {
            dashWs.send(broadcastPayload);
          }
        }
      }
    } catch (err) {
      console.error('[WebSocket] Parse error:', err.message);
    }
  });

  ws.on('close', () => {
    phoneClients.delete(ws);
    dashboardClients.delete(ws);
    if (phoneClients.size === 0) {
      connectedPhoneDetails = null;
    }
    broadcastSystemStatus();
  });

  ws.on('error', (err) => {
    console.error('[WebSocket] Socket error:', err.message);
  });
});

function broadcastSystemStatus() {
  const statusPayload = JSON.stringify({
    type: 'SYSTEM_STATUS',
    phoneConnected: phoneClients.size > 0,
    phoneCount: phoneClients.size,
    dashboardCount: dashboardClients.size,
    connectedPhoneDetails,
    recording: getRecordingState(),
    rowCount: getRowCount(),
    totalPacketsReceived,
    lanIps: getLanIps()
  });

  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(statusPayload);
    }
  }
}

// REST API Endpoints
app.get('/api/info', (req, res) => {
  const lanIps = getLanIps();
  const primaryIp = lanIps.length > 0 ? lanIps[0].address : 'localhost';
  res.json({
    status: 'online',
    protocol: 'https',
    startTime,
    primaryIp,
    lanIps,
    phoneUrl: `https://${primaryIp}:5173/?mode=phone`,
    wsUrl: `wss://${primaryIp}:3001`,
    phoneConnected: phoneClients.size > 0,
    phoneClients: phoneClients.size,
    recording: getRecordingState(),
    rowCount: getRowCount(),
    totalPacketsReceived,
    csvPath: getCSVPath()
  });
});

app.post('/api/recording/start', (req, res) => {
  const state = setRecordingState(true);
  broadcastSystemStatus();
  res.json({ success: true, recording: state, rowCount: getRowCount() });
});

app.post('/api/recording/stop', (req, res) => {
  const state = setRecordingState(false);
  broadcastSystemStatus();
  res.json({ success: true, recording: state, rowCount: getRowCount() });
});

app.post('/api/recording/clear', (req, res) => {
  const success = clearCSV();
  broadcastSystemStatus();
  res.json({ success, recording: getRecordingState(), rowCount: getRowCount() });
});

app.get('/api/download-csv', (req, res) => {
  const csvPath = getCSVPath();
  if (fs.existsSync(csvPath)) {
    res.download(csvPath, 'sensor_data.csv');
  } else {
    res.status(404).json({ error: 'CSV file not found' });
  }
});

// Start listening on HTTPS 0.0.0.0:3001
server.listen(PORT, '0.0.0.0', () => {
  const lanIps = getLanIps();
  console.log('\n==================================================');
  console.log('🔒 Phone Motion Data Logger Secure HTTPS Backend Online!');
  console.log(`- HTTPS Listening on: https://0.0.0.0:${PORT}`);
  console.log('- Localhost access: https://localhost:' + PORT);
  console.log('- LAN IP addresses:');
  if (lanIps.length === 0) {
    console.log('  ⚠️ No active LAN Wi-Fi IPv4 found.');
  } else {
    lanIps.forEach((ip) => console.log(`  👉 https://${ip.address}:${PORT} (${ip.interface})`));
  }
  if (lanIps.length > 0) {
    console.log(`- Phone Mode URL: https://${lanIps[0].address}:5173/?mode=phone`);
  }
  console.log(`- CSV Output Path: ${getCSVPath()}`);
  console.log('==================================================\n');
});
