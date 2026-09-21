import { useState, useEffect, useRef, useCallback } from 'react';

export function useSensors() {
  const [isSecureContext, setIsSecureContext] = useState(true);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [permissionError, setPermissionError] = useState(null);
  const [isListening, setIsListening] = useState(false);

  // Simulation Mode (OFF by default)
  const [simulatedMode, setSimulatedMode] = useState(false);
  const simStepRef = useRef(0);

  // Genuine Raw Sensor Data Storage
  const latestReadings = useRef({
    timestamp: null,
    accelerometer: null,
    gyroscope: null,
    orientation: null,
    magnetometer: null,
    gps: null
  });

  // UI Reactive State
  const [displayReadings, setDisplayReadings] = useState({
    timestamp: null,
    accelerometer: null,
    gyroscope: null,
    orientation: null,
    magnetometer: null,
    gps: null
  });

  // Real-time Event Received Counters
  const [eventCounts, setEventCounts] = useState({
    motion: 0,
    orientation: 0,
    absOrientation: 0,
    gps: 0,
    magnetometer: 0
  });

  const eventCountsRef = useRef({
    motion: 0,
    orientation: 0,
    absOrientation: 0,
    gps: 0,
    magnetometer: 0
  });

  // Environment & Web API Diagnostics
  const [envDiagnostics, setEnvDiagnostics] = useState({
    isSecureContext: true,
    userAgent: '',
    protocol: '',
    hasDeviceMotion: false,
    hasDeviceOrientation: false,
    hasMotionPermissionApi: false,
    hasOrientationPermissionApi: false,
    hasGeolocation: false,
    hasAbsoluteOrientationSensor: false,
    hasMagnetometer: false
  });

  // Detailed Sensor Diagnostic Statuses & Failure Reasons
  const [sensorStatus, setSensorStatus] = useState({
    accelerometer: { status: 'IDLE', message: 'Click ENABLE PHONE SENSORS' },
    gyroscope: { status: 'IDLE', message: 'Click ENABLE PHONE SENSORS' },
    orientation: { status: 'IDLE', message: 'Click ENABLE PHONE SENSORS' },
    gps: { status: 'IDLE', message: 'Click ENABLE PHONE SENSORS' },
    magnetometer: { status: 'IDLE', message: 'Click ENABLE PHONE SENSORS' }
  });

  const magnetometerRef = useRef(null);
  const geoWatchIdRef = useRef(null);
  const diagnosticTimeoutRef = useRef(null);

  // 1. Inspect Environment & Browser APIs on Mount
  useEffect(() => {
    const secure = window.isSecureContext !== false;
    const ua = navigator.userAgent || '';
    const proto = window.location.protocol || '';

    const hasMotion = typeof window !== 'undefined' && 'DeviceMotionEvent' in window;
    const hasOrient = typeof window !== 'undefined' && 'DeviceOrientationEvent' in window;
    const hasMotionPerm = typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function';
    const hasOrientPerm = typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function';
    const hasGeo = typeof navigator !== 'undefined' && 'geolocation' in navigator;
    const hasAbsOrient = typeof window !== 'undefined' && 'AbsoluteOrientationSensor' in window;
    const hasMag = typeof window !== 'undefined' && 'Magnetometer' in window;

    setIsSecureContext(secure);

    setEnvDiagnostics({
      isSecureContext: secure,
      userAgent: ua,
      protocol: proto,
      hasDeviceMotion: hasMotion,
      hasDeviceOrientation: hasOrient,
      hasMotionPermissionApi: hasMotionPerm,
      hasOrientationPermissionApi: hasOrientPerm,
      hasGeolocation: hasGeo,
      hasAbsoluteOrientationSensor: hasAbsOrient,
      hasMagnetometer: hasMag
    });

    setSensorStatus({
      accelerometer: {
        status: hasMotion ? 'IDLE' : 'NOT_SUPPORTED',
        message: hasMotion ? 'Ready. Click ENABLE PHONE SENSORS' : 'DeviceMotionEvent API not supported by this browser'
      },
      gyroscope: {
        status: hasMotion ? 'IDLE' : 'NOT_SUPPORTED',
        message: hasMotion ? 'Ready. Click ENABLE PHONE SENSORS' : 'DeviceMotionEvent.rotationRate API not supported'
      },
      orientation: {
        status: hasOrient ? 'IDLE' : 'NOT_SUPPORTED',
        message: hasOrient ? 'Ready. Click ENABLE PHONE SENSORS' : 'DeviceOrientationEvent API not supported'
      },
      gps: {
        status: hasGeo ? 'IDLE' : 'NOT_SUPPORTED',
        message: hasGeo ? 'Ready. Click ENABLE PHONE SENSORS' : 'navigator.geolocation API not supported'
      },
      magnetometer: {
        status: hasMag ? 'IDLE' : 'OPTIONAL_NOT_SUPPORTED',
        message: hasMag ? 'Ready. Click ENABLE PHONE SENSORS' : 'Generic Sensor Magnetometer API not supported (Optional)'
      }
    });
  }, []);

  /**
   * Real Device Motion Handler
   */
  const handleDeviceMotion = useCallback((event) => {
    if (simulatedMode) return;

    eventCountsRef.current.motion += 1;
    const currentCount = eventCountsRef.current.motion;
    setEventCounts(prev => ({ ...prev, motion: currentCount }));

    const now = new Date().toISOString();
    latestReadings.current.timestamp = now;

    // Accelerometer Data Check
    if (event.accelerationIncludingGravity) {
      const { x, y, z } = event.accelerationIncludingGravity;
      if (x !== null || y !== null || z !== null) {
        latestReadings.current.accelerometer = {
          x: x !== null && x !== undefined ? Number(x.toFixed(4)) : null,
          y: y !== null && y !== undefined ? Number(y.toFixed(4)) : null,
          z: z !== null && z !== undefined ? Number(z.toFixed(4)) : null,
          noGravity: event.acceleration ? {
            x: event.acceleration.x !== null && event.acceleration.x !== undefined ? Number(event.acceleration.x.toFixed(4)) : null,
            y: event.acceleration.y !== null && event.acceleration.y !== undefined ? Number(event.acceleration.y.toFixed(4)) : null,
            z: event.acceleration.z !== null && event.acceleration.z !== undefined ? Number(event.acceleration.z.toFixed(4)) : null
          } : null
        };

        setSensorStatus(prev => ({
          ...prev,
          accelerometer: { status: 'AVAILABLE', message: `Receiving hardware values (${currentCount} events)` }
        }));
      } else {
        setSensorStatus(prev => ({
          ...prev,
          accelerometer: { status: 'NULL_DATA', message: 'Browser fired devicemotion, but x/y/z values are null (Check Chrome Site Settings -> Sensors)' }
        }));
      }
    }

    // Gyroscope (rotationRate) Check
    if (event.rotationRate) {
      const { alpha, beta, gamma } = event.rotationRate;
      if (alpha !== null || beta !== null || gamma !== null) {
        latestReadings.current.gyroscope = {
          alpha: alpha !== null && alpha !== undefined ? Number(alpha.toFixed(4)) : null,
          beta: beta !== null && beta !== undefined ? Number(beta.toFixed(4)) : null,
          gamma: gamma !== null && gamma !== undefined ? Number(gamma.toFixed(4)) : null
        };

        setSensorStatus(prev => ({
          ...prev,
          gyroscope: { status: 'AVAILABLE', message: `Receiving rotation values (${currentCount} events)` }
        }));
      } else {
        setSensorStatus(prev => ({
          ...prev,
          gyroscope: { status: 'NULL_DATA', message: 'Browser fired devicemotion, but rotationRate values are null' }
        }));
      }
    }
  }, [simulatedMode]);

  /**
   * Real Device Orientation Handler
   */
  const handleDeviceOrientation = useCallback((event) => {
    if (simulatedMode) return;

    eventCountsRef.current.orientation += 1;
    const currentCount = eventCountsRef.current.orientation;
    setEventCounts(prev => ({ ...prev, orientation: currentCount }));

    const { alpha, beta, gamma } = event;
    if (alpha !== null || beta !== null || gamma !== null) {
      latestReadings.current.orientation = {
        alpha: alpha !== null && alpha !== undefined ? Number(alpha.toFixed(2)) : null,
        beta: beta !== null && beta !== undefined ? Number(beta.toFixed(2)) : null,
        gamma: gamma !== null && gamma !== undefined ? Number(gamma.toFixed(2)) : null
      };

      setSensorStatus(prev => ({
        ...prev,
        orientation: { status: 'AVAILABLE', message: `Receiving orientation angles (${currentCount} events)` }
      }));
    } else {
      setSensorStatus(prev => ({
        ...prev,
        orientation: { status: 'NULL_DATA', message: 'Browser fired deviceorientation, but alpha/beta/gamma are null' }
      }));
    }
  }, [simulatedMode]);

  /**
   * Real Absolute Device Orientation Handler (Android Chrome Compass fallback)
   */
  const handleDeviceOrientationAbsolute = useCallback((event) => {
    if (simulatedMode) return;
    eventCountsRef.current.absOrientation += 1;
    const currentCount = eventCountsRef.current.absOrientation;
    setEventCounts(prev => ({ ...prev, absOrientation: currentCount }));

    if (event.alpha !== null || event.beta !== null || event.gamma !== null) {
      if (!latestReadings.current.orientation) {
        latestReadings.current.orientation = {
          alpha: event.alpha !== null ? Number(event.alpha.toFixed(2)) : null,
          beta: event.beta !== null ? Number(event.beta.toFixed(2)) : null,
          gamma: event.gamma !== null ? Number(event.gamma.toFixed(2)) : null
        };
        setSensorStatus(prev => ({
          ...prev,
          orientation: { status: 'AVAILABLE', message: `Receiving absolute orientation angles (${currentCount} events)` }
        }));
      }
    }
  }, [simulatedMode]);

  /**
   * Explicit Permission Request Click Handler
   */
  const requestSensorPermissions = async () => {
    setPermissionError(null);
    try {
      if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
        const motionResp = await DeviceMotionEvent.requestPermission();
        if (motionResp !== 'granted') {
          throw new Error('DeviceMotion permission denied by user (iOS prompt)');
        }
      }

      if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        const orientResp = await DeviceOrientationEvent.requestPermission();
        if (orientResp !== 'granted') {
          throw new Error('DeviceOrientation permission denied by user (iOS prompt)');
        }
      }

      setPermissionGranted(true);
      return true;
    } catch (err) {
      console.warn('Sensor permission error:', err);
      setPermissionError(err.message || 'Permission request failed');
      return false;
    }
  };

  /**
   * Enable Sensors & Start Diagnostic Telemetry
   */
  const startListening = useCallback(async () => {
    setIsListening(true);
    setPermissionError(null);

    // Reset event counters
    eventCountsRef.current = { motion: 0, orientation: 0, absOrientation: 0, gps: 0, magnetometer: 0 };
    setEventCounts({ motion: 0, orientation: 0, absOrientation: 0, gps: 0, magnetometer: 0 });

    if (simulatedMode) {
      setSensorStatus({
        accelerometer: { status: 'AVAILABLE', message: 'Simulated motion active' },
        gyroscope: { status: 'AVAILABLE', message: 'Simulated rotation active' },
        orientation: { status: 'AVAILABLE', message: 'Simulated orientation active' },
        gps: { status: 'AVAILABLE', message: 'Simulated GPS active' },
        magnetometer: { status: 'AVAILABLE', message: 'Simulated magnetometer active' }
      });
      return;
    }

    // Set Initial Listening Statuses
    setSensorStatus(prev => ({
      accelerometer: envDiagnostics.hasDeviceMotion
        ? { status: 'LISTENING', message: 'Listener added. Waiting for browser devicemotion event...' }
        : prev.accelerometer,
      gyroscope: envDiagnostics.hasDeviceMotion
        ? { status: 'LISTENING', message: 'Listener added. Waiting for browser devicemotion event...' }
        : prev.gyroscope,
      orientation: envDiagnostics.hasDeviceOrientation
        ? { status: 'LISTENING', message: 'Listener added. Waiting for browser deviceorientation event...' }
        : prev.orientation,
      gps: envDiagnostics.hasGeolocation
        ? { status: 'LISTENING', message: 'Requesting GPS position from browser...' }
        : prev.gps,
      magnetometer: envDiagnostics.hasMagnetometer
        ? { status: 'LISTENING', message: 'Starting Magnetometer sensor...' }
        : prev.magnetometer
    }));

    // Request permissions if required
    await requestSensorPermissions();

    // 1. Register Motion & Orientation Listeners
    if ('DeviceMotionEvent' in window) {
      window.addEventListener('devicemotion', handleDeviceMotion, true);
    }
    if ('DeviceOrientationEvent' in window) {
      window.addEventListener('deviceorientation', handleDeviceOrientation, true);
      window.addEventListener('deviceorientationabsolute', handleDeviceOrientationAbsolute, true);
    }

    // 2. Register Magnetometer if supported
    if ('Magnetometer' in window) {
      try {
        // @ts-ignore
        const mag = new window.Magnetometer({ frequency: 10 });
        mag.addEventListener('reading', () => {
          eventCountsRef.current.magnetometer += 1;
          const currentCount = eventCountsRef.current.magnetometer;
          setEventCounts(prev => ({ ...prev, magnetometer: currentCount }));

          latestReadings.current.magnetometer = {
            x: mag.x !== undefined && mag.x !== null ? Number(mag.x.toFixed(2)) : null,
            y: mag.y !== undefined && mag.y !== null ? Number(mag.y.toFixed(2)) : null,
            z: mag.z !== undefined && mag.z !== null ? Number(mag.z.toFixed(2)) : null
          };

          setSensorStatus(prev => ({
            ...prev,
            magnetometer: { status: 'AVAILABLE', message: `Receiving magnetometer vectors (${currentCount} readings)` }
          }));
        });

        mag.addEventListener('error', (err) => {
          setSensorStatus(prev => ({
            ...prev,
            magnetometer: { status: 'OPTIONAL_NOT_SUPPORTED', message: `Magnetometer error: ${err.error?.name || 'Not allowed or unsupported'}` }
          }));
        });
        mag.start();
        magnetometerRef.current = mag;
      } catch (e) {
        setSensorStatus(prev => ({
          ...prev,
          magnetometer: { status: 'OPTIONAL_NOT_SUPPORTED', message: `Magnetometer construction failed: ${e.message}` }
        }));
      }
    }

    // 3. Register Geolocation Watch Position
    if ('geolocation' in navigator) {
      geoWatchIdRef.current = navigator.geolocation.watchPosition(
        (position) => {
          eventCountsRef.current.gps += 1;
          const currentCount = eventCountsRef.current.gps;
          setEventCounts(prev => ({ ...prev, gps: currentCount }));

          const { latitude, longitude, altitude, speed, heading, accuracy } = position.coords;
          latestReadings.current.gps = {
            latitude: latitude !== undefined && latitude !== null ? Number(latitude.toFixed(6)) : null,
            longitude: longitude !== undefined && longitude !== null ? Number(longitude.toFixed(6)) : null,
            altitude: altitude !== undefined && altitude !== null ? Number(altitude.toFixed(2)) : null,
            speed: speed !== undefined && speed !== null ? Number(speed.toFixed(2)) : null,
            heading: heading !== undefined && heading !== null ? Number(heading.toFixed(2)) : null,
            accuracy: accuracy !== undefined && accuracy !== null ? Number(accuracy.toFixed(2)) : null
          };

          setSensorStatus(prev => ({
            ...prev,
            gps: { status: 'AVAILABLE', message: `GPS location acquired (${currentCount} updates)` }
          }));
        },
        (error) => {
          console.warn('[Geolocation Diagnostic Error]:', error);
          let detailMessage = 'Permission denied by user or system';
          if (error.code === error.PERMISSION_DENIED) {
            detailMessage = 'PERMISSION DENIED: Enable Location in Chrome Address Bar Site Settings';
          } else if (error.code === error.POSITION_UNAVAILABLE) {
            detailMessage = 'POSITION UNAVAILABLE: Turn ON Android Device Location / GPS';
          } else if (error.code === error.TIMEOUT) {
            detailMessage = 'GPS TIMEOUT: Took longer than 10s to acquire satellite lock';
          }

          setSensorStatus(prev => ({
            ...prev,
            gps: { status: 'FAILED_PERM_OR_ERR', message: detailMessage }
          }));
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    }

    // 4. Set 3-second Diagnostic Check Timeout to detect 0-event silent blocks
    if (diagnosticTimeoutRef.current) clearTimeout(diagnosticTimeoutRef.current);
    diagnosticTimeoutRef.current = setTimeout(() => {
      setSensorStatus(prev => {
        const next = { ...prev };

        if (eventCountsRef.current.motion === 0 && envDiagnostics.hasDeviceMotion) {
          next.accelerometer = {
            status: 'NO_EVENTS_FIRED',
            message: 'Listener active, but Chrome emitted 0 motion events after 3s. Check Chrome Site Settings -> Sensors, or Chrome untrusted HTTPS self-signed origin security policy.'
          };
          next.gyroscope = {
            status: 'NO_EVENTS_FIRED',
            message: 'Listener active, but Chrome emitted 0 motion events after 3s.'
          };
        }

        if (eventCountsRef.current.orientation === 0 && eventCountsRef.current.absOrientation === 0 && envDiagnostics.hasDeviceOrientation) {
          next.orientation = {
            status: 'NO_EVENTS_FIRED',
            message: 'Listener active, but Chrome emitted 0 orientation events after 3s.'
          };
        }

        if (eventCountsRef.current.gps === 0 && envDiagnostics.hasGeolocation && next.gps.status === 'LISTENING') {
          next.gps = {
            status: 'WAITING_FOR_GPS_FIX',
            message: 'Waiting for Android GPS hardware fix... Make sure location toggle is ON.'
          };
        }

        return next;
      });
    }, 3500);

  }, [handleDeviceMotion, handleDeviceOrientation, handleDeviceOrientationAbsolute, envDiagnostics, simulatedMode]);

  /**
   * Stop Listening & Clean Up
   */
  const stopListening = useCallback(() => {
    setIsListening(false);

    if (diagnosticTimeoutRef.current) {
      clearTimeout(diagnosticTimeoutRef.current);
      diagnosticTimeoutRef.current = null;
    }

    if ('DeviceMotionEvent' in window) {
      window.removeEventListener('devicemotion', handleDeviceMotion, true);
    }
    if ('DeviceOrientationEvent' in window) {
      window.removeEventListener('deviceorientation', handleDeviceOrientation, true);
      window.removeEventListener('deviceorientationabsolute', handleDeviceOrientationAbsolute, true);
    }
    if (magnetometerRef.current) {
      try { magnetometerRef.current.stop(); } catch (e) {}
      magnetometerRef.current = null;
    }
    if (geoWatchIdRef.current !== null && 'geolocation' in navigator) {
      navigator.geolocation.clearWatch(geoWatchIdRef.current);
      geoWatchIdRef.current = null;
    }

    setSensorStatus(prev => ({
      accelerometer: { ...prev.accelerometer, status: prev.accelerometer.status === 'AVAILABLE' ? 'STOPPED' : prev.accelerometer.status },
      gyroscope: { ...prev.gyroscope, status: prev.gyroscope.status === 'AVAILABLE' ? 'STOPPED' : prev.gyroscope.status },
      orientation: { ...prev.orientation, status: prev.orientation.status === 'AVAILABLE' ? 'STOPPED' : prev.orientation.status },
      gps: { ...prev.gps, status: prev.gps.status === 'AVAILABLE' ? 'STOPPED' : prev.gps.status },
      magnetometer: { ...prev.magnetometer, status: prev.magnetometer.status === 'AVAILABLE' ? 'STOPPED' : prev.magnetometer.status }
    }));
  }, [handleDeviceMotion, handleDeviceOrientation, handleDeviceOrientationAbsolute]);

  useEffect(() => {
    return () => stopListening();
  }, [stopListening]);

  /**
   * Get Snapshot for UI Rendering and WebSocket Output
   */
  const getSnapshot = useCallback(() => {
    const timestamp = new Date().toISOString();

    if (simulatedMode) {
      simStepRef.current += 0.1;
      const t = simStepRef.current;

      const simAccel = {
        x: Number((Math.sin(t) * 2.5).toFixed(4)),
        y: Number((Math.cos(t) * 1.8).toFixed(4)),
        z: Number((9.81 + Math.sin(t * 0.5) * 0.5).toFixed(4)),
        noGravity: {
          x: Number((Math.sin(t) * 2.5).toFixed(4)),
          y: Number((Math.cos(t) * 1.8).toFixed(4)),
          z: Number((Math.sin(t * 0.5) * 0.5).toFixed(4))
        }
      };

      const simGyro = {
        alpha: Number((Math.cos(t * 1.2) * 45).toFixed(4)),
        beta: Number((Math.sin(t * 0.8) * 30).toFixed(4)),
        gamma: Number((Math.cos(t * 0.5) * 15).toFixed(4))
      };

      const simOrient = {
        alpha: Number(((t * 10) % 360).toFixed(2)),
        beta: Number((Math.sin(t) * 45).toFixed(2)),
        gamma: Number((Math.cos(t * 30).toFixed(2)))
      };

      const simMag = {
        x: Number((22.5 + Math.sin(t) * 5).toFixed(2)),
        y: Number((-41.2 + Math.cos(t) * 5).toFixed(2)),
        z: Number((-15.0 + Math.sin(t * 0.5) * 3).toFixed(2))
      };

      const simGps = {
        latitude: Number((11.0168 + Math.sin(t * 0.05) * 0.001).toFixed(6)),
        longitude: Number((76.9558 + Math.cos(t * 0.05) * 0.001).toFixed(6)),
        altitude: Number((412.5 + Math.sin(t * 0.1) * 2).toFixed(2)),
        speed: Number((1.5 + Math.sin(t * 0.2) * 0.8).toFixed(2)),
        heading: Number(((t * 15) % 360).toFixed(2)),
        accuracy: 4.5
      };

      const snapshot = {
        timestamp,
        accelerometer: simAccel,
        gyroscope: simGyro,
        orientation: simOrient,
        magnetometer: simMag,
        gps: simGps,
        availability: {
          accelerometer: true,
          gyroscope: true,
          orientation: true,
          magnetometer: true,
          gps: true
        }
      };

      setDisplayReadings(snapshot);
      return snapshot;
    }

    const snapshot = {
      timestamp,
      accelerometer: latestReadings.current.accelerometer,
      gyroscope: latestReadings.current.gyroscope,
      orientation: latestReadings.current.orientation,
      magnetometer: latestReadings.current.magnetometer,
      gps: latestReadings.current.gps,
      availability: {
        accelerometer: Boolean(latestReadings.current.accelerometer),
        gyroscope: Boolean(latestReadings.current.gyroscope),
        orientation: Boolean(latestReadings.current.orientation),
        magnetometer: Boolean(latestReadings.current.magnetometer),
        gps: Boolean(latestReadings.current.gps)
      }
    };

    setDisplayReadings({ ...snapshot });
    return snapshot;
  }, [simulatedMode]);

  return {
    isSecureContext,
    permissionGranted,
    permissionError,
    isListening,
    simulatedMode,
    setSimulatedMode,
    displayReadings,
    eventCounts,
    envDiagnostics,
    sensorStatus,
    requestSensorPermissions,
    startListening,
    stopListening,
    getSnapshot
  };
}
