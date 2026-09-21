package com.isro.sih.deadreckoning.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import java.util.concurrent.atomic.AtomicLong

data class SensorReading(
    val timestampMs: Long,
    val timestampNanos: Long,
    val accelX: Float?,
    val accelY: Float?,
    val accelZ: Float?,
    val gyroX: Float?,
    val gyroY: Float?,
    val gyroZ: Float?,
    val magX: Float?,
    val magY: Float?,
    val magZ: Float?
)

class SensorCollector(
    private val context: Context,
    private val onSensorData: (SensorReading) -> Unit
) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager

    private val accelSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val gyroSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
    private val magSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)

    @Volatile
    var isRunning = false
        private set

    val eventsCount = AtomicLong(0)

    // Current latest values
    @Volatile var latestAccel: FloatArray? = null
    @Volatile var latestGyro: FloatArray? = null
    @Volatile var latestMag: FloatArray? = null

    /**
     * Starts listening to sensors at requested sampling rate in Hz (1, 10, 50, 100).
     */
    fun start(frequencyHz: Int) {
        if (isRunning) stop()

        val samplingPeriodMicros = when (frequencyHz) {
            1 -> 1_000_000
            50 -> 20_000
            100 -> 10_000
            else -> 100_000 // Default 10 Hz
        }

        accelSensor?.let { sensorManager.registerListener(this, it, samplingPeriodMicros) }
        gyroSensor?.let { sensorManager.registerListener(this, it, samplingPeriodMicros) }
        magSensor?.let { sensorManager.registerListener(this, it, samplingPeriodMicros) }

        isRunning = true
    }

    fun stop() {
        if (!isRunning) return
        sensorManager.unregisterListener(this)
        isRunning = false
    }

    override fun onSensorChanged(event: SensorEvent) {
        val wallClockMs = System.currentTimeMillis()
        val sensorNanos = event.timestamp

        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> latestAccel = event.values.clone()
            Sensor.TYPE_GYROSCOPE -> latestGyro = event.values.clone()
            Sensor.TYPE_MAGNETIC_FIELD -> latestMag = event.values.clone()
        }

        eventsCount.incrementAndGet()

        val reading = SensorReading(
            timestampMs = wallClockMs,
            timestampNanos = sensorNanos,
            accelX = latestAccel?.getOrNull(0),
            accelY = latestAccel?.getOrNull(1),
            accelZ = latestAccel?.getOrNull(2),
            gyroX = latestGyro?.getOrNull(0),
            gyroY = latestGyro?.getOrNull(1),
            gyroZ = latestGyro?.getOrNull(2),
            magX = latestMag?.getOrNull(0),
            magY = latestMag?.getOrNull(1),
            magZ = latestMag?.getOrNull(2)
        )

        onSensorData(reading)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}
