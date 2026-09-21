package com.isro.sih.deadreckoning.cellular

/**
 * Clean Data Model for Native Android Cellular Telemetry.
 *
 * Represents an individual cell record (Serving or Neighbor) parsed directly
 * from native Android TelephonyManager APIs.
 */
data class CellularRecord(
    val timestamp: Long,
    val registeredStatus: Boolean,       // true = serving cell, false = neighbor cell
    val cellType: String,               // "LTE", "NR", "GSM", "WCDMA", "CDMA", "UNKNOWN"
    val cellId: Long?,                  // CI (LTE), NCI (NR), CID (GSM), UCID (WCDMA)
    val mcc: String?,                   // Mobile Country Code
    val mnc: String?,                   // Mobile Network Code
    val lac: Int?,                      // Location Area Code (GSM/WCDMA)
    val tac: Int?,                      // Tracking Area Code (LTE/5G NR)
    val pci: Int?,                      // Physical Cell ID (LTE/5G NR)
    val arfcn: Int?,                    // EARFCN (LTE), NRARFCN (NR), ARFCN (GSM), UARFCN (WCDMA)
    val signalDbm: Int?,                // Primary dBm
    val signalLevel: Int?,              // 0..4
    val networkOperator: String?,       // Operator name / Alpha long

    // Research-Grade Signal & Technology Preservation
    val signalMetricType: String?,      // "LTE_RSRP", "NR_SS_RSRP", "GSM_RSSI", "WCDMA_RSCP", etc.
    val rawSignalValue: Int?,           // Precise signal measurement value
    val rawTechnologyDetails: Map<String, Any?> = emptyMap()
)

/**
 * Diagnostic result snapshot containing permission status, operator,
 * serving cell, and neighbor list.
 */
data class CellularDiagnosticResult(
    val timestamp: Long,
    val permissionGranted: Boolean,
    val networkOperator: String?,
    val servingCell: CellularRecord?,
    val neighborCells: List<CellularRecord>
)
