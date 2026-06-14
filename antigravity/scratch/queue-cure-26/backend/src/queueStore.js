import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.join(__dirname, '../data');
const DATA_FILE = path.join(DATA_DIR, 'queue.json');

class QueueStore {
  constructor() {
    this.state = {
      currentServing: null,
      waitingQueue: [],
      completedCount: 0,
      avgConsultationTime: 6,
      tokenCounter: 1
    };
    this.init();
  }

  init() {
    try {
      if (!fs.existsSync(DATA_DIR)) {
        fs.mkdirSync(DATA_DIR, { recursive: true });
      }
      if (fs.existsSync(DATA_FILE)) {
        const fileData = fs.readFileSync(DATA_FILE, 'utf-8');
        this.state = JSON.parse(fileData);
      } else {
        this.save();
      }
    } catch (error) {
      console.error('Failed to initialize QueueStore:', error);
    }
  }

  save() {
    try {
      fs.writeFileSync(DATA_FILE, JSON.stringify(this.state, null, 2), 'utf-8');
    } catch (error) {
      console.error('Failed to save QueueStore:', error);
    }
  }

  getState() {
    return {
      currentServing: this.state.currentServing,
      waitingQueue: this.state.waitingQueue,
      completedCount: this.state.completedCount,
      avgConsultationTime: this.state.avgConsultationTime,
      tokenCounter: this.state.tokenCounter
    };
  }

  addPatient(name, tokenInput) {
    let token = tokenInput ? tokenInput.trim() : '';
    if (!token) {
      const numStr = String(this.state.tokenCounter).padStart(3, '0');
      token = `QC-${numStr}`;
      this.state.tokenCounter += 1;
    }
    
    const patient = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: name.trim(),
      token: token,
      createdAt: new Date().toISOString()
    };
    
    this.state.waitingQueue.push(patient);
    this.save();
    return patient;
  }

  callNext() {
    if (this.state.currentServing) {
      this.state.completedCount += 1;
    }

    if (this.state.waitingQueue.length > 0) {
      this.state.currentServing = this.state.waitingQueue.shift();
      this.state.currentServing.calledAt = new Date().toISOString();
    } else {
      this.state.currentServing = null;
    }
    
    this.save();
    return this.getState();
  }

  completePatient() {
    if (this.state.currentServing) {
      this.state.completedCount += 1;
      this.state.currentServing = null;
      this.save();
    }
    return this.getState();
  }

  deletePatient(patientId) {
    if (this.state.currentServing && this.state.currentServing.id === patientId) {
      this.state.currentServing = null;
    } else {
      this.state.waitingQueue = this.state.waitingQueue.filter(p => p.id !== patientId);
    }
    this.save();
    return this.getState();
  }

  updateAvgConsultationTime(time) {
    const numericTime = Number(time);
    if (!isNaN(numericTime) && numericTime > 0) {
      this.state.avgConsultationTime = numericTime;
      this.save();
    }
    return this.getState();
  }

  resetQueue() {
    this.state = {
      currentServing: null,
      waitingQueue: [],
      completedCount: 0,
      avgConsultationTime: 6,
      tokenCounter: 1
    };
    this.save();
    return this.getState();
  }
}

export default new QueueStore();
