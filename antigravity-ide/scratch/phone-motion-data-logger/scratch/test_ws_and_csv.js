import WebSocket from '../server/node_modules/ws/index.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const csvPath = path.resolve(__dirname, '../data/sensor_data.csv');

console.log('[Test] Connecting over Secure WSS to wss://localhost:3001...');
const ws = new WebSocket('wss://localhost:3001?type=phone', {
  rejectUnauthorized: false
});

ws.on('open', () => {
  console.log('[Test] WSS Secure WebSocket connected successfully!');

  const testPayload = {
    timestamp: new Date().toISOString(),
    accelerometer: { x: -0.42, y: 1.25, z: 9.68, noGravity: { x: -0.05, y: 0.12, z: 0.08 } },
    gyroscope: { alpha: 0.18, beta: -0.45, gamma: 2.15 },
    orientation: { alpha: 95.4, beta: -3.2, gamma: 14.8 },
    magnetometer: null, // Unsupported sensor test
    gps: { latitude: 11.016845, longitude: 76.955812, altitude: 412.0, speed: 0.8, heading: 140.5, accuracy: 3.2 },
    availability: {
      accelerometer: true,
      gyroscope: true,
      orientation: true,
      magnetometer: false,
      gps: true
    }
  };

  console.log('[Test] Transmitting HTTPS telemetry packet over WSS...');
  ws.send(JSON.stringify(testPayload));

  setTimeout(() => {
    ws.close();
    console.log('[Test] WSS socket closed. Verifying CSV output...');

    if (fs.existsSync(csvPath)) {
      const csvLines = fs.readFileSync(csvPath, 'utf8').trim().split('\n');
      console.log(`\n[Test Result] CSV file exists with ${csvLines.length} line(s):`);
      csvLines.forEach((line, idx) => console.log(`  Line ${idx + 1}: ${line}`));
      if (csvLines.length > 1) {
        console.log('\n==================================================');
        console.log('✅ TEST PASSED: WSS Secure WebSocket & CSV Recording Working!');
        console.log('==================================================\n');
      } else {
        console.error('❌ TEST FAILED: CSV header found but no data row appended.');
        process.exit(1);
      }
    } else {
      console.error('❌ TEST FAILED: CSV file not found at:', csvPath);
      process.exit(1);
    }
  }, 1000);
});

ws.on('error', (err) => {
  console.error('[Test] WSS Secure WebSocket connection failed:', err);
  process.exit(1);
});
