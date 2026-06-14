import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { 
  UserPlus, 
  Play, 
  CheckCircle, 
  Clock, 
  Trash2, 
  Users, 
  Radio, 
  Volume2, 
  VolumeX, 
  Settings, 
  RefreshCw,
  AlertCircle
} from 'lucide-react';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000';

function App() {
  const [view, setView] = useState('admin'); // 'admin' | 'display'
  const [connected, setConnected] = useState(false);
  const [queueState, setQueueState] = useState({
    currentServing: null,
    waitingQueue: [],
    completedCount: 0,
    avgConsultationTime: 6,
    tokenCounter: 1
  });
  
  const [patientName, setPatientName] = useState('');
  const [customToken, setCustomToken] = useState('');
  const [avgTimeInput, setAvgTimeInput] = useState(6);
  const [enableVoice, setEnableVoice] = useState(true);
  const [toast, setToast] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const socketRef = useRef(null);
  const prevServingIdRef = useRef(null);

  // Show toast utility
  const showToast = (message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Setup Socket Connection
  useEffect(() => {
    const socket = io(SOCKET_URL);
    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socket.on('queue:state', (state) => {
      setQueueState(state);
      setAvgTimeInput(state.avgConsultationTime);
      
      // Voice synthesis for newly called patient
      if (enableVoice && state.currentServing && state.currentServing.id !== prevServingIdRef.current) {
        speakToken(state.currentServing.token, state.currentServing.name);
        prevServingIdRef.current = state.currentServing.id;
      } else if (!state.currentServing) {
        prevServingIdRef.current = null;
      }
    });

    socket.on('error', (err) => {
      showToast(err.message || 'An error occurred', 'error');
    });

    return () => {
      socket.disconnect();
    };
  }, [enableVoice]);

  // Handle active patient elapsed timer
  useEffect(() => {
    if (!queueState.currentServing) {
      setElapsedSeconds(0);
      return;
    }

    const calledAt = new Date(queueState.currentServing.calledAt || new Date()).getTime();
    
    // Sync immediately
    setElapsedSeconds(Math.floor((Date.now() - calledAt) / 1000));

    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - calledAt) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [queueState.currentServing]);

  // Voice synthesis function
  const speakToken = (token, name) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // cancel any active speech
      
      // Clean token spelling for better TTS pronunciation (e.g. QC-001 to Q C zero zero one)
      const tokenSpelled = token.split('').map(char => {
        if (char === '-') return ' ';
        return char;
      }).join(' ');

      const text = `Token number ${tokenSpelled}, patient ${name}, please proceed to the doctor.`;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Format active timer
  const formatElapsed = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Socket action emitters
  const handleAddPatient = (e) => {
    e.preventDefault();
    if (!patientName.trim()) {
      showToast('Patient name cannot be empty', 'error');
      return;
    }
    
    socketRef.current.emit('patient:add', {
      name: patientName,
      token: customToken.trim() || undefined
    });
    
    setPatientName('');
    setCustomToken('');
    showToast('Patient added to queue successfully!', 'success');
  };

  const handleCallNext = () => {
    socketRef.current.emit('patient:call-next');
  };

  const handleComplete = () => {
    socketRef.current.emit('patient:complete');
  };

  const handleDelete = (id) => {
    socketRef.current.emit('patient:delete', { id });
  };

  const handleUpdateAvgTime = (e) => {
    const val = Number(e.target.value);
    setAvgTimeInput(val);
    socketRef.current.emit('config:update-avg-time', { avgConsultationTime: val });
  };

  const handleResetQueue = () => {
    if (window.confirm('Are you sure you want to clear the entire queue state? This reset cannot be undone.')) {
      socketRef.current.emit('queue:reset');
      showToast('Queue reset successfully', 'success');
    }
  };

  const { currentServing, waitingQueue, completedCount, avgConsultationTime } = queueState;

  // Compute stats
  const totalWaiting = waitingQueue.length;
  // Dynamic ETA for a new patient joining now:
  // If someone is being served, they wait for the current patient (approx remaining/full avg) + all waiting patients
  const currentServingOffset = currentServing ? 1 : 0;
  const newPatientWaitTime = (totalWaiting + currentServingOffset) * avgConsultationTime;

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="brand-section">
          <div className="logo-icon">Q</div>
          <div className="brand-name">
            <h1>Queue Cure '26</h1>
            <span>Smart Clinic Sync</span>
          </div>
        </div>

        <div className="header-actions">
          {/* Connection Status Indicator */}
          <div className="connection-badge">
            <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`}></span>
            {connected ? 'Real-time Connected' : 'Offline / Reconnecting'}
          </div>

          {/* View Toggle Switcher */}
          <div className="view-toggle">
            <button 
              className={`toggle-btn ${view === 'admin' ? 'active' : ''}`}
              onClick={() => setView('admin')}
            >
              <Settings size={16} /> Receptionist
            </button>
            <button 
              className={`toggle-btn ${view === 'display' ? 'active' : ''}`}
              onClick={() => setView('display')}
            >
              <Radio size={16} /> Public Display
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="content-area">
        {view === 'admin' ? (
          /* ========================================================================= */
          /* RECEPTIONIST SCREEN (ADMIN PANEL)                                         */
          /* ========================================================================= */
          <div className="glass-panel">
            <h2 className="panel-title">
              <Settings className="text-primary" /> Receptionist Command Console
            </h2>

            <div className="admin-grid">
              
              {/* Left Column: Actions & Configuration */}
              <div className="admin-left-col">
                
                {/* Call Next & Current Serving Panel */}
                <div className="glass-card active-serving-card">
                  <div className="card-subtitle">Currently Consulting</div>
                  
                  {currentServing ? (
                    <div>
                      <div className="active-patient-info">
                        <div>
                          <h3 className="active-token">{currentServing.token}</h3>
                          <p className="active-name">{currentServing.name}</p>
                        </div>
                        <div className={`active-timer ${elapsedSeconds > avgConsultationTime * 60 ? 'border-warning text-warning' : ''}`}>
                          <Clock size={16} />
                          {formatElapsed(elapsedSeconds)}
                          {elapsedSeconds > avgConsultationTime * 60 && (
                            <AlertCircle size={14} className="text-warning ml-1" title="Exceeded Average Time" />
                          )}
                        </div>
                      </div>
                      <div className="active-actions">
                        <button className="btn btn-primary" onClick={handleCallNext}>
                          <Play size={16} /> Call Next Patient
                        </button>
                        <button className="btn btn-secondary" onClick={handleComplete}>
                          <CheckCircle size={16} /> Mark Completed
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="no-patient-state">
                      <Clock size={48} />
                      <p>No patient is currently active in consultation.</p>
                      <button 
                        className="btn btn-primary" 
                        onClick={handleCallNext}
                        disabled={waitingQueue.length === 0}
                        style={{ marginTop: '1.25rem' }}
                      >
                        <Play size={16} /> Call Next Patient
                      </button>
                    </div>
                  )}
                </div>

                {/* Patient Registration Form */}
                <div className="glass-card">
                  <div className="card-subtitle" style={{ color: 'var(--secondary)' }}>Patient Registration</div>
                  <form onSubmit={handleAddPatient} style={{ marginTop: '0.75rem' }}>
                    <div className="input-group">
                      <label htmlFor="patient-name">Patient Name</label>
                      <input 
                        type="text" 
                        id="patient-name"
                        className="input-control" 
                        placeholder="Enter full name" 
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        required
                      />
                    </div>
                    
                    <div className="input-group">
                      <label htmlFor="custom-token">Custom Token (Optional)</label>
                      <input 
                        type="text" 
                        id="custom-token"
                        className="input-control" 
                        placeholder="Leave blank for auto-generate" 
                        value={customToken}
                        onChange={(e) => setCustomToken(e.target.value)}
                      />
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
                      <UserPlus size={16} /> Register & Queue Patient
                    </button>
                  </form>
                </div>

                {/* Queue Settings */}
                <div className="glass-card">
                  <div className="card-subtitle" style={{ color: 'var(--warning)' }}>Timing & Configuration</div>
                  <div style={{ marginTop: '1rem' }}>
                    <div className="input-group">
                      <label htmlFor="avg-time">Avg Consultation Time (minutes)</label>
                      <input 
                        type="number" 
                        id="avg-time"
                        min="1" 
                        max="60"
                        className="input-control" 
                        value={avgTimeInput}
                        onChange={handleUpdateAvgTime}
                      />
                    </div>

                    {/* Speech Option Toggle */}
                    <div className="voice-option-row">
                      <label htmlFor="voice-toggle">
                        <Volume2 size={16} className="text-primary" /> Audio Voice Calls
                      </label>
                      <label className="switch">
                        <input 
                          type="checkbox" 
                          id="voice-toggle"
                          checked={enableVoice}
                          onChange={(e) => setEnableVoice(e.target.checked)}
                        />
                        <span className="slider"></span>
                      </label>
                    </div>

                    {/* Reset Button */}
                    <button 
                      className="btn btn-secondary" 
                      onClick={handleResetQueue}
                      style={{ width: '100%', marginTop: '1.25rem', borderColor: 'var(--danger-glow)', color: 'var(--danger)' }}
                    >
                      <RefreshCw size={14} /> Reset Live Queue State
                    </button>
                  </div>
                </div>

              </div>

              {/* Right Column: Live Queue View */}
              <div className="admin-right-col">
                <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <div className="queue-list-header">
                    <div className="card-subtitle" style={{ marginBottom: 0 }}>Waiting Queue</div>
                    <span className="queue-count-badge">{totalWaiting} Patients Waiting</span>
                  </div>

                  <div className="queue-items-container">
                    {waitingQueue.length > 0 ? (
                      waitingQueue.map((patient, index) => {
                        // Dynamic wait calculations for item list:
                        // Each patient's wait is (number of people ahead + active patient offset) * avg consultation time
                        const patientsAhead = index;
                        const waitMinutes = (patientsAhead + currentServingOffset) * avgConsultationTime;
                        
                        return (
                          <div className="queue-item" key={patient.id}>
                            <div className="queue-item-left">
                              <span className="queue-position-indicator">#{index + 1}</span>
                              <span className="queue-item-token">{patient.token}</span>
                              <span className="queue-item-name">{patient.name}</span>
                            </div>
                            <div className="queue-item-right">
                              <div className="queue-item-eta">
                                Wait Time
                                <span>~{waitMinutes} mins</span>
                              </div>
                              <button 
                                className="btn-icon-delete"
                                onClick={() => handleDelete(patient.id)}
                                title="Remove patient from queue"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="no-patient-state" style={{ flex: 1 }}>
                        <Users size={36} />
                        <p>No patients currently waiting.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

            </div>
          </div>
        ) : (
          /* ========================================================================= */
          /* PATIENT WAITING SCREEN (PUBLIC DISPLAY)                                   */
          /* ========================================================================= */
          <div className="glass-panel" style={{ height: '100%' }}>
            <div className="display-layout">
              
              {/* Left Side: Hero Screen with Current Serving */}
              <div className="display-main">
                <div className="display-hero">
                  <div className="pulse-glow"></div>
                  <h2 className="display-hero-label">Now Serving Token</h2>
                  
                  {currentServing ? (
                    <>
                      <h1 className="display-hero-token">{currentServing.token}</h1>
                      <div className="display-hero-name">{currentServing.name}</div>
                      <div className="display-hero-time">
                        <Clock size={16} className="text-primary" /> 
                        In Consultation for {formatElapsed(elapsedSeconds)} mins
                      </div>
                    </>
                  ) : (
                    <>
                      <h1 className="display-hero-token" style={{ fontSize: '4.5rem', color: 'var(--text-muted)' }}>FREE</h1>
                      <div className="display-hero-name" style={{ color: 'var(--text-muted)' }}>Waiting for next patient...</div>
                    </>
                  )}
                </div>

                {/* Queue Summary Statistics */}
                <div className="display-stats-grid">
                  <div className="stat-box">
                    <div className="stat-title">Patients Ahead</div>
                    <div className="stat-value value-primary">{totalWaiting}</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-title">Estimated Wait (New)</div>
                    <div className="stat-value value-secondary">~{newPatientWaitTime} min</div>
                  </div>
                  <div className="stat-box">
                    <div className="stat-title">Completed Today</div>
                    <div className="stat-value value-success">{completedCount}</div>
                  </div>
                </div>
              </div>

              {/* Right Side: Sidebar listing upcoming tokens */}
              <div className="display-sidebar">
                <div className="sidebar-queue-container">
                  <div className="card-subtitle" style={{ borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.75rem' }}>
                    Upcoming Tokens
                  </div>
                  
                  {waitingQueue.length > 0 ? (
                    <div className="display-sidebar-list">
                      {waitingQueue.map((patient, index) => {
                        const waitTime = (index + currentServingOffset) * avgConsultationTime;
                        return (
                          <div className={`display-list-item ${index === 0 ? 'next-up' : ''}`} key={patient.id}>
                            <div className="display-item-left">
                              <span className="display-item-pos">#{index + 1}</span>
                              <span className="display-item-token">{patient.token}</span>
                              <span className="display-item-name">{patient.name}</span>
                            </div>
                            <div className="display-item-wait">
                              <div className="display-item-wait-label">Est. Wait</div>
                              <div className="display-item-wait-time">~{waitTime}m</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="no-upcoming">
                      No upcoming patients scheduled.
                    </div>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}
      </main>

      {/* Floating Notifications */}
      {toast && (
        <div className={`toast-msg ${toast.type}`}>
          <AlertCircle size={16} />
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}

export default App;
