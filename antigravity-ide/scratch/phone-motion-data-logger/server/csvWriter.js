import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Data directory and file path
const dataDir = path.resolve(__dirname, '../data');
const csvFilePath = path.join(dataDir, 'sensor_data.csv');

// Standard CSV Header
const CSV_HEADERS = [
  'phone_timestamp',
  'server_received_timestamp',
  'accelerometer_x',
  'accelerometer_y',
  'accelerometer_z',
  'accel_nograv_x',
  'accel_nograv_y',
  'accel_nograv_z',
  'gyroscope_alpha',
  'gyroscope_beta',
  'gyroscope_gamma',
  'orientation_alpha',
  'orientation_beta',
  'orientation_gamma',
  'magnetometer_x',
  'magnetometer_y',
  'magnetometer_z',
  'latitude',
  'longitude',
  'altitude',
  'speed',
  'heading',
  'accuracy'
];

let totalRowsWritten = 0;
let isRecording = true;

/**
 * Initializes the CSV file and directory.
 * If file does not exist, creates it and writes header.
 */
export function initCSVWriter() {
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  if (!fs.existsSync(csvFilePath)) {
    fs.writeFileSync(csvFilePath, CSV_HEADERS.join(',') + '\n', 'utf8');
    totalRowsWritten = 0;
    console.log(`[CSV] Initialized new CSV file at: ${csvFilePath}`);
  } else {
    // Count existing rows
    try {
      const fileContent = fs.readFileSync(csvFilePath, 'utf8');
      const lines = fileContent.trim().split('\n');
      totalRowsWritten = Math.max(0, lines.length - 1);
      console.log(`[CSV] Found existing CSV file with ${totalRowsWritten} data rows.`);
    } catch (err) {
      console.error('[CSV] Error reading existing CSV file:', err);
      totalRowsWritten = 0;
    }
  }
}

/**
 * Appends a sensor reading to the CSV file.
 * Returns true if successfully written.
 */
export function appendSensorReading(data, serverTimestamp) {
  if (!isRecording) return false;

  try {
    const val = (v) => (v !== null && v !== undefined && v !== '' ? String(v) : '');

    const phoneTs = val(data.timestamp);
    const serverTs = val(serverTimestamp);

    const accelX = val(data.accelerometer?.x);
    const accelY = val(data.accelerometer?.y);
    const accelZ = val(data.accelerometer?.z);

    const accelNoGravX = val(data.accelerometer?.noGravity?.x);
    const accelNoGravY = val(data.accelerometer?.noGravity?.y);
    const accelNoGravZ = val(data.accelerometer?.noGravity?.z);

    const gyroAlpha = val(data.gyroscope?.alpha);
    const gyroBeta = val(data.gyroscope?.beta);
    const gyroGamma = val(data.gyroscope?.gamma);

    const orientAlpha = val(data.orientation?.alpha);
    const orientBeta = val(data.orientation?.beta);
    const orientGamma = val(data.orientation?.gamma);

    const magX = val(data.magnetometer?.x);
    const magY = val(data.magnetometer?.y);
    const magZ = val(data.magnetometer?.z);

    const lat = val(data.gps?.latitude);
    const lon = val(data.gps?.longitude);
    const alt = val(data.gps?.altitude);
    const speed = val(data.gps?.speed);
    const heading = val(data.gps?.heading);
    const accuracy = val(data.gps?.accuracy);

    const row = [
      phoneTs,
      serverTs,
      accelX,
      accelY,
      accelZ,
      accelNoGravX,
      accelNoGravY,
      accelNoGravZ,
      gyroAlpha,
      gyroBeta,
      gyroGamma,
      orientAlpha,
      orientBeta,
      orientGamma,
      magX,
      magY,
      magZ,
      lat,
      lon,
      alt,
      speed,
      heading,
      accuracy
    ].join(',');

    fs.appendFileSync(csvFilePath, row + '\n', 'utf8');
    totalRowsWritten++;
    return true;
  } catch (err) {
    console.error('[CSV] Error writing row to CSV:', err);
    return false;
  }
}

/**
 * Resets or clears the CSV file
 */
export function clearCSV() {
  try {
    fs.writeFileSync(csvFilePath, CSV_HEADERS.join(',') + '\n', 'utf8');
    totalRowsWritten = 0;
    console.log('[CSV] Cleared CSV file.');
    return true;
  } catch (err) {
    console.error('[CSV] Error clearing CSV file:', err);
    return false;
  }
}

export function setRecordingState(state) {
  isRecording = Boolean(state);
  return isRecording;
}

export function getRecordingState() {
  return isRecording;
}

export function getRowCount() {
  return totalRowsWritten;
}

export function getCSVPath() {
  return csvFilePath;
}
