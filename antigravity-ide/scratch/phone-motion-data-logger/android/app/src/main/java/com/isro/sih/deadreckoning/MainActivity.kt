package com.isro.sih.deadreckoning

import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.isro.sih.deadreckoning.cellular.CellularCollector
import com.isro.sih.deadreckoning.cellular.CellularDiagnosticResult
import com.isro.sih.deadreckoning.cellular.CellularPermissionHelper
import com.isro.sih.deadreckoning.gnss.GnssCollector
import com.isro.sih.deadreckoning.gnss.GnssReading
import com.isro.sih.deadreckoning.logger.SessionLogger
import com.isro.sih.deadreckoning.sensor.SensorCollector
import com.isro.sih.deadreckoning.sensor.SensorReading
import java.util.concurrent.atomic.AtomicLong

class MainActivity : AppCompatActivity() {

    private lateinit var permissionHelper: CellularPermissionHelper
    private lateinit var cellularCollector: CellularCollector
    private lateinit var sensorCollector: SensorCollector
    private lateinit var gnssCollector: GnssCollector
    private lateinit var sessionLogger: SessionLogger

    // Frequency state
    private var selectedFrequencyHz = 10

    // Stream Active States
    private var isSensorActive = false
    private var isGnssActive = false
    private var isCellularActive = false

    val cellRecordsCount = AtomicLong(0)

    // UI elements
    private lateinit var tvSelectedFrequency: TextView
    private lateinit var btnFreq1Hz: Button
    private lateinit var btnFreq10Hz: Button
    private lateinit var btnFreq50Hz: Button
    private lateinit var btnFreq100Hz: Button

    private lateinit var btnStartSensor: Button
    private lateinit var btnStartGnss: Button
    private lateinit var btnStartCellular: Button
    private lateinit var btnStartAll: Button

    private lateinit var tvSessionId: TextView
    private lateinit var tvSensorEventsCount: TextView
    private lateinit var tvGnssFixesCount: TextView
    private lateinit var tvSatelliteRecordsCount: TextView
    private lateinit var tvCellRecordsCount: TextView

    private lateinit var tvCellularStatus: TextView
    private lateinit var tvGnssStatus: TextView
    private lateinit var tvNeighborCellsDetails: TextView

    // Cellular polling handler (1 Hz)
    private val uiHandler = Handler(Looper.getMainLooper())
    private val cellularPollRunnable = object : Runnable {
        override fun run() {
            if (isCellularActive) {
                pollCellularData()
                uiHandler.postDelayed(this, 1000L) // 1 Hz polling
            }
        }
    }

    // Live UI Refresh Runnable (every 500ms)
    private val uiUpdateRunnable = object : Runnable {
        override fun run() {
            updateSessionCountersUI()
            if (isSensorActive || isGnssActive || isCellularActive) {
                uiHandler.postDelayed(this, 500L)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        permissionHelper = CellularPermissionHelper(this)
        cellularCollector = CellularCollector(this)
        sessionLogger = SessionLogger(this)

        sensorCollector = SensorCollector(this) { reading: SensorReading ->
            sessionLogger.logSensor(reading)
        }

        gnssCollector = GnssCollector(this) { reading: GnssReading ->
            sessionLogger.logGnss(reading)
            runOnUiThread { updateGnssCardUI(reading) }
        }

        bindViews()
        setupFrequencyListeners()
        setupStreamListeners()
    }

    private fun bindViews() {
        tvSelectedFrequency = findViewById(R.id.tvSelectedFrequency)
        btnFreq1Hz = findViewById(R.id.btnFreq1Hz)
        btnFreq10Hz = findViewById(R.id.btnFreq10Hz)
        btnFreq50Hz = findViewById(R.id.btnFreq50Hz)
        btnFreq100Hz = findViewById(R.id.btnFreq100Hz)

        btnStartSensor = findViewById(R.id.btnStartSensor)
        btnStartGnss = findViewById(R.id.btnStartGnss)
        btnStartCellular = findViewById(R.id.btnStartCellular)
        btnStartAll = findViewById(R.id.btnStartAll)

        tvSessionId = findViewById(R.id.tvSessionId)
        tvSensorEventsCount = findViewById(R.id.tvSensorEventsCount)
        tvGnssFixesCount = findViewById(R.id.tvGnssFixesCount)
        tvSatelliteRecordsCount = findViewById(R.id.tvSatelliteRecordsCount)
        tvCellRecordsCount = findViewById(R.id.tvCellRecordsCount)

        tvCellularStatus = findViewById(R.id.tvCellularStatus)
        tvGnssStatus = findViewById(R.id.tvGnssStatus)
        tvNeighborCellsDetails = findViewById(R.id.tvNeighborCellsDetails)
    }

    private fun setupFrequencyListeners() {
        val buttons = mapOf(
            1 to btnFreq1Hz,
            10 to btnFreq10Hz,
            50 to btnFreq50Hz,
            100 to btnFreq100Hz
        )

        buttons.forEach { (freq, btn) ->
            btn.setOnClickListener {
                selectedFrequencyHz = freq
                tvSelectedFrequency.text = "Selected frequency: $selectedFrequencyHz Hz"
                buttons.forEach { (f, b) ->
                    if (f == freq) {
                        b.setBackgroundColor(Color.parseColor("#0EA5E9")) // Active cyan
                    } else {
                        b.setBackgroundColor(Color.parseColor("#334155")) // Inactive slate
                    }
                }
                if (isSensorActive) {
                    sensorCollector.start(selectedFrequencyHz)
                }
            }
        }
    }

    private fun setupStreamListeners() {
        btnStartSensor.setOnClickListener {
            toggleSensorStream()
        }

        btnStartGnss.setOnClickListener {
            if (checkOrRequestPermissions()) {
                toggleGnssStream()
            }
        }

        btnStartCellular.setOnClickListener {
            if (checkOrRequestPermissions()) {
                toggleCellularStream()
            }
        }

        btnStartAll.setOnClickListener {
            if (checkOrRequestPermissions()) {
                toggleAllStreams()
            }
        }
    }

    private fun checkOrRequestPermissions(): Boolean {
        if (!permissionHelper.hasAllPermissions()) {
            permissionHelper.requestPermissions(this)
            return false
        }
        return true
    }

    private fun ensureSessionStarted() {
        if (!sessionLogger.isLogging) {
            val sid = sessionLogger.startSession()
            tvSessionId.text = "Session ID: $sid"
            uiHandler.post(uiUpdateRunnable)
        }
    }

    private fun checkStopSessionIfAllStopped() {
        if (!isSensorActive && !isGnssActive && !isCellularActive) {
            sessionLogger.stopSession()
            uiHandler.removeCallbacks(uiUpdateRunnable)
            updateSessionCountersUI()
        }
    }

    // --- STREAM TOGGLES ---
    private fun toggleSensorStream() {
        if (!isSensorActive) {
            ensureSessionStarted()
            sensorCollector.start(selectedFrequencyHz)
            isSensorActive = true
            btnStartSensor.text = "STOP SENSOR"
            btnStartSensor.setBackgroundColor(Color.parseColor("#EF4444")) // Red
        } else {
            sensorCollector.stop()
            isSensorActive = false
            btnStartSensor.text = "START SENSOR"
            btnStartSensor.setBackgroundColor(Color.parseColor("#10B981")) // Green
            checkStopSessionIfAllStopped()
        }
        updateStartAllButtonUI()
    }

    private fun toggleGnssStream() {
        if (!isGnssActive) {
            ensureSessionStarted()
            gnssCollector.start()
            isGnssActive = true
            btnStartGnss.text = "STOP GNSS"
            btnStartGnss.setBackgroundColor(Color.parseColor("#EF4444"))
            tvGnssStatus.text = "Status: RUNNING\nFix: WAITING / NO FIX\nLat: N/A | Lng: N/A\nAlt: N/A | Acc: N/A\nSatellites: Searching..."
        } else {
            gnssCollector.stop()
            isGnssActive = false
            btnStartGnss.text = "START GNSS"
            btnStartGnss.setBackgroundColor(Color.parseColor("#F59E0B"))
            tvGnssStatus.text = "Status: STOPPED\nFix: WAITING / NO FIX\nLat: N/A | Lng: N/A\nAlt: N/A | Acc: N/A\nSatellites: 0 in view (0 in fix)"
            checkStopSessionIfAllStopped()
        }
        updateStartAllButtonUI()
    }

    private fun toggleCellularStream() {
        if (!isCellularActive) {
            ensureSessionStarted()
            isCellularActive = true
            btnStartCellular.text = "STOP CELLULAR"
            btnStartCellular.setBackgroundColor(Color.parseColor("#EF4444"))
            uiHandler.post(cellularPollRunnable)
        } else {
            isCellularActive = false
            uiHandler.removeCallbacks(cellularPollRunnable)
            btnStartCellular.text = "START CELLULAR"
            btnStartCellular.setBackgroundColor(Color.parseColor("#6366F1"))
            tvCellularStatus.text = "Status: STOPPED\nTechnology: N/A\nServing Cell ID: N/A\nPCI: N/A\nRSRP: N/A\nARFCN: N/A\nTAC: N/A"
            checkStopSessionIfAllStopped()
        }
        updateStartAllButtonUI()
    }

    private fun toggleAllStreams() {
        val anyActive = isSensorActive || isGnssActive || isCellularActive
        if (!anyActive) {
            if (!isSensorActive) toggleSensorStream()
            if (!isGnssActive) toggleGnssStream()
            if (!isCellularActive) toggleCellularStream()
        } else {
            if (isSensorActive) toggleSensorStream()
            if (isGnssActive) toggleGnssStream()
            if (isCellularActive) toggleCellularStream()
        }
        updateStartAllButtonUI()
    }

    private fun updateStartAllButtonUI() {
        val allActive = isSensorActive && isGnssActive && isCellularActive
        if (allActive) {
            btnStartAll.text = "STOP ALL STREAMS"
            btnStartAll.setBackgroundColor(Color.parseColor("#EF4444"))
        } else {
            btnStartAll.text = "START ALL STREAMS"
            btnStartAll.setBackgroundColor(Color.parseColor("#EC4899"))
        }
    }

    // --- CELLULAR POLLING ---
    private fun pollCellularData() {
        val result: CellularDiagnosticResult = cellularCollector.collectCellularDiagnostics()
        sessionLogger.logCellular(result)

        // Increment cell record counters
        val addedCount = (if (result.servingCell != null) 1 else 0) + result.neighborCells.size
        if (addedCount > 0) {
            cellRecordsCount.addAndGet(addedCount.toLong())
        }

        updateCellularCardUI(result)
    }

    private fun updateCellularCardUI(result: CellularDiagnosticResult) {
        val serving = result.servingCell
        if (serving != null) {
            val sb = StringBuilder()
            sb.append("Status: RUNNING\n")
            sb.append("Technology: ").append(serving.cellType).append("\n")
            sb.append("Serving Cell ID: ").append(serving.cellId?.toString() ?: "N/A").append("\n")
            sb.append("PCI: ").append(serving.pci?.toString() ?: "N/A").append("\n")
            sb.append("RSRP: ").append(serving.signalDbm?.let { "$it dBm" } ?: "N/A")
            if (serving.signalMetricType != null) {
                sb.append(" (").append(serving.signalMetricType).append(")")
            }
            sb.append("\n")
            sb.append("ARFCN: ").append(serving.arfcn?.toString() ?: "N/A").append("\n")
            sb.append("TAC: ").append(serving.tac?.toString() ?: "N/A")

            tvCellularStatus.text = sb.toString()
        } else {
            tvCellularStatus.text = "Status: RUNNING\nTechnology: Searching...\nServing Cell ID: N/A\nPCI: N/A\nRSRP: N/A\nARFCN: N/A\nTAC: N/A"
        }

        if (result.neighborCells.isNotEmpty()) {
            val nbSb = StringBuilder()
            result.neighborCells.forEachIndexed { i, nb ->
                nbSb.append("#").append(i + 1).append(" ")
                    .append(nb.cellType).append(" | PCI: ")
                    .append(nb.pci?.toString() ?: "N/A").append(" | Signal: ")
                    .append(nb.signalDbm?.let { "$it dBm" } ?: "N/A").append("\n")
            }
            tvNeighborCellsDetails.text = nbSb.toString().trimEnd()
        } else {
            tvNeighborCellsDetails.text = "No neighbor cells detected."
        }
    }

    private fun updateGnssCardUI(reading: GnssReading) {
        val fixText = if (reading.hasFix) "FIX ACQUIRED" else "WAITING / NO FIX"
        val latStr = reading.latitude?.let { String.format("%.5f", it) } ?: "N/A"
        val lngStr = reading.longitude?.let { String.format("%.5f", it) } ?: "N/A"
        val altStr = reading.altitude?.let { String.format("%.1fm", it) } ?: "N/A"
        val accStr = reading.accuracy?.let { String.format("%.1fm", it) } ?: "N/A"

        val statusText = "Status: RUNNING\nFix: $fixText\nLat: $latStr | Lng: $lngStr\nAlt: $altStr | Acc: $accStr\nSatellites: ${reading.satellitesInView} in view (${reading.satellitesUsedInFix} in fix)"
        tvGnssStatus.text = statusText
    }

    private fun updateSessionCountersUI() {
        tvSensorEventsCount.text = "Sensor events: ${sensorCollector.eventsCount.get()}"
        tvGnssFixesCount.text = "GNSS fixes: ${gnssCollector.fixesCount.get()}"
        tvSatelliteRecordsCount.text = "Satellite records: ${gnssCollector.satelliteRecordsCount.get()}"
        tvCellRecordsCount.text = "Cell records: ${cellRecordsCount.get()}"
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CellularPermissionHelper.PERMISSION_REQUEST_CODE) {
            val allGranted = grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            if (!allGranted) {
                tvCellularStatus.text = "Permission DENIED."
                tvGnssStatus.text = "Permission DENIED."
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        sensorCollector.stop()
        gnssCollector.stop()
        uiHandler.removeCallbacksAndMessages(null)
        sessionLogger.stopSession()
    }
}
