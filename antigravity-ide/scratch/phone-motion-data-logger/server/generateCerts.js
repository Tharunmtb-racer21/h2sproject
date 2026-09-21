import selfsigned from 'selfsigned';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const certsDir = path.resolve(__dirname, '../certs');
const certPath = path.join(certsDir, 'cert.pem');
const keyPath = path.join(certsDir, 'key.pem');

// Discover all LAN IPv4 addresses
function getLanIps() {
  const interfaces = os.networkInterfaces();
  const ips = ['127.0.0.1'];
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        ips.push(iface.address);
      }
    }
  }
  return ips;
}

export function generateCertificates(force = false) {
  if (!fs.existsSync(certsDir)) {
    fs.mkdirSync(certsDir, { recursive: true });
  }

  if (!force && fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    console.log('[HTTPS] SSL certificates already exist at:', certsDir);
    return {
      cert: fs.readFileSync(certPath, 'utf8'),
      key: fs.readFileSync(keyPath, 'utf8'),
      certPath,
      keyPath
    };
  }

  const lanIps = getLanIps();
  console.log('[HTTPS] Generating fresh SSL Certificate for LAN IPs:', lanIps);

  const altNames = [
    { type: 2, value: 'localhost' },
    ...lanIps.map(ip => ({ type: 7, ip }))
  ];

  const attrs = [{ name: 'commonName', value: lanIps[1] || '192.168.1.7' }];

  const pkey = selfsigned.generate(attrs, {
    keySize: 2048,
    days: 365,
    algorithm: 'sha256',
    extensions: [
      { name: 'basicConstraints', cA: true },
      {
        name: 'keyUsage',
        keyCertSign: true,
        digitalSignature: true,
        nonRepudiation: true,
        keyEncipherment: true,
        dataEncipherment: true
      },
      {
        name: 'subjectAltName',
        altNames
      }
    ]
  });

  fs.writeFileSync(certPath, pkey.cert, 'utf8');
  fs.writeFileSync(keyPath, pkey.private, 'utf8');

  console.log('[HTTPS] Successfully generated self-signed certificate in:', certsDir);
  return { cert: pkey.cert, key: pkey.private, certPath, keyPath };
}

// Auto-run if executed directly
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  generateCertificates(true);
}
