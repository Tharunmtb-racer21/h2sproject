package com.isro.sih.deadreckoning.logger

import android.content.Context
import android.os.Environment
import android.util.Log
import com.isro.sih.deadreckoning.cellular.CellularDiagnosticResult
import com.isro.sih.deadreckoning.gnss.GnssReading
import com.isro.sih.deadreckoning.sensor.SensorReading
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ConcurrentLinkedQueue

class SessionLogger(private val context: Context) {

    @Volatile
    var sessionId: String = ""
        private set

    @Volatile
    var isLogging = false
        private set

    private val recordsQueue = ConcurrentLinkedQueue<String>()
    private var appCsvFile: File? = null
    private var publicCsvFile: File? = null

    companion object {
        private const val TAG = "SessionLogger"
        private const val CSV_HEADER = "stream_type,timestamp_ms,sensor_nanos,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,has_fix,latitude,longitude,altitude,accuracy,speed,bearing,sats_view,sats_used,registered,cell_type,cell_id,mcc,mnc,lac,tac,pci,arfcn,signal_dbm,signal_metric,signal_level,operator\n"
    }

    fun startSession(): String {
        val timeStr = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        sessionId = "SESSION-$timeStr"
        recordsQueue.clear()

        // 1. App-scoped private storage
        val appDir = File(context.getExternalFilesDir(null), "sessions")
        if (!appDir.exists()) appDir.mkdirs()
        appCsvFile = File(appDir, "${sessionId}.csv")

        // 2. Public Downloads storage for easy phone File Manager access
        val publicDir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "ISRO_DeadReckoning")
        if (!publicDir.exists()) publicDir.mkdirs()
        publicCsvFile = File(publicDir, "${sessionId}.csv")

        try {
            FileWriter(appCsvFile, false).use { it.write(CSV_HEADER) }
            FileWriter(publicCsvFile, false).use { it.write(CSV_HEADER) }
            Log.d(TAG, "Created CSV files: ${appCsvFile?.absolutePath} & ${publicCsvFile?.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create CSV files: ${e.message}")
        }

        isLogging = true
        return sessionId
    }

    fun stopSession() {
        isLogging = false
        flushQueue()
    }

    fun logSensor(reading: SensorReading) {
        if (!isLogging) return
        val line = "SENSOR,${reading.timestampMs},${reading.timestampNanos},${reading.accelX ?: ""},${reading.accelY ?: ""},${reading.accelZ ?: ""},${reading.gyroX ?: ""},${reading.gyroY ?: ""},${reading.gyroZ ?: ""},${reading.magX ?: ""},${reading.magY ?: ""},${reading.magZ ?: ""},,,,,,,,,,,,,,,,,,,,,,\n"
        recordsQueue.add(line)
        if (recordsQueue.size >= 50) flushQueue()
    }

    fun logGnss(reading: GnssReading) {
        if (!isLogging) return
        val line = "GNSS,${reading.timestampMs},,,,,,,,,,,${reading.hasFix},${reading.latitude ?: ""},${reading.longitude ?: ""},${reading.altitude ?: ""},${reading.accuracy ?: ""},${reading.speed ?: ""},${reading.bearing ?: ""},${reading.satellitesInView},${reading.satellitesUsedInFix},,,,,,,,,,,,,\n"
        recordsQueue.add(line)
        if (recordsQueue.size >= 10) flushQueue()
    }

    fun logCellular(result: CellularDiagnosticResult) {
        if (!isLogging) return
        val serving = result.servingCell
        if (serving != null) {
            val line = "CELLULAR,${serving.timestamp},,,,,,,,,,,,,,,,,,,,${serving.registeredStatus},${serving.cellType},${serving.cellId ?: ""},${serving.mcc ?: ""},${serving.mnc ?: ""},${serving.lac ?: ""},${serving.tac ?: ""},${serving.pci ?: ""},${serving.arfcn ?: ""},${serving.signalDbm ?: ""},${serving.signalMetricType ?: ""},${serving.signalLevel ?: ""},${serving.networkOperator ?: ""}\n"
            recordsQueue.add(line)
        }
        for (neighbor in result.neighborCells) {
            val line = "CELLULAR,${neighbor.timestamp},,,,,,,,,,,,,,,,,,,,false,${neighbor.cellType},${neighbor.cellId ?: ""},${neighbor.mcc ?: ""},${neighbor.mnc ?: ""},${neighbor.lac ?: ""},${neighbor.tac ?: ""},${neighbor.pci ?: ""},${neighbor.arfcn ?: ""},${neighbor.signalDbm ?: ""},${neighbor.signalMetricType ?: ""},${neighbor.signalLevel ?: ""},${neighbor.networkOperator ?: ""}\n"
            recordsQueue.add(line)
        }
        flushQueue()
    }

    @Synchronized
    private fun flushQueue() {
        if (recordsQueue.isEmpty()) return

        val linesToFlush = mutableListOf<String>()
        while (!recordsQueue.isEmpty()) {
            val record = recordsQueue.poll() ?: break
            linesToFlush.add(record)
        }

        if (linesToFlush.isEmpty()) return

        val content = linesToFlush.joinToString("")

        // Write to app internal storage
        appCsvFile?.let { file ->
            try { FileWriter(file, true).use { it.write(content) } } catch (e: Exception) { Log.e(TAG, e.message ?: "") }
        }

        // Write to public Downloads/ISRO_DeadReckoning storage
        publicCsvFile?.let { file ->
            try { FileWriter(file, true).use { it.write(content) } } catch (e: Exception) { Log.e(TAG, e.message ?: "") }
        }
    }
}
