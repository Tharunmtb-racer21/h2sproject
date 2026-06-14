import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import queueStore from './queueStore.js';

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({
  origin: '*',
  methods: ['GET', 'POST']
}));
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/queue', (req, res) => {
  res.json(queueStore.getState());
});

const httpServer = createServer(app);

const io = new Server(httpServer, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

const broadcastState = () => {
  const state = queueStore.getState();
  io.emit('queue:state', state);
};

io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);
  
  socket.emit('queue:state', queueStore.getState());

  socket.on('queue:get', () => {
    socket.emit('queue:state', queueStore.getState());
  });

  socket.on('patient:add', (data) => {
    try {
      const { name, token } = data;
      if (!name || name.trim() === '') {
        socket.emit('error', { message: 'Patient name is required.' });
        return;
      }
      queueStore.addPatient(name, token);
      broadcastState();
    } catch (err) {
      console.error('Error adding patient:', err);
      socket.emit('error', { message: 'Failed to add patient.' });
    }
  });

  socket.on('patient:call-next', () => {
    try {
      queueStore.callNext();
      broadcastState();
    } catch (err) {
      console.error('Error calling next patient:', err);
      socket.emit('error', { message: 'Failed to call next patient.' });
    }
  });

  socket.on('patient:complete', () => {
    try {
      queueStore.completePatient();
      broadcastState();
    } catch (err) {
      console.error('Error completing patient:', err);
      socket.emit('error', { message: 'Failed to complete patient.' });
    }
  });

  socket.on('patient:delete', (data) => {
    try {
      const { id } = data;
      if (!id) {
        socket.emit('error', { message: 'Patient ID is required.' });
        return;
      }
      queueStore.deletePatient(id);
      broadcastState();
    } catch (err) {
      console.error('Error deleting patient:', err);
      socket.emit('error', { message: 'Failed to remove patient.' });
    }
  });

  socket.on('config:update-avg-time', (data) => {
    try {
      const { avgConsultationTime } = data;
      queueStore.updateAvgConsultationTime(avgConsultationTime);
      broadcastState();
    } catch (err) {
      console.error('Error updating average time:', err);
      socket.emit('error', { message: 'Failed to update average time.' });
    }
  });

  socket.on('queue:reset', () => {
    try {
      queueStore.resetQueue();
      broadcastState();
    } catch (err) {
      console.error('Error resetting queue:', err);
      socket.emit('error', { message: 'Failed to reset queue.' });
    }
  });

  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
  });
});

httpServer.listen(PORT, () => {
  console.log(`Queue Cure '26 Server listening on port ${PORT}`);
});
