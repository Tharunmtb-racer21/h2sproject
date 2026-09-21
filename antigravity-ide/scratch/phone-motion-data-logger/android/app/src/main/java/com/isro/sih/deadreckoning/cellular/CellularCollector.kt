package com.isro.sih.deadreckoning.cellular

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.telephony.*
import android.util.Log

class CellularCollector(private val context: Context) {

    private val telephonyManager: TelephonyManager =
        context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

    private val permissionHelper = CellularPermissionHelper(context)

    companion object {
        private const val TAG = "CellularCollector"
        private const val INT_UNAVAILABLE = CellInfo.UNAVAILABLE
        private const val LONG_UNAVAILABLE = CellInfo.UNAVAILABLE_LONG
    }

    /**
     * Reads current hardware cellular telemetry from Android TelephonyManager.
     *
     * Returns a CellularDiagnosticResult containing serving cell, neighbor list,
     * timestamp, and permission status.
     */
    @SuppressLint("MissingPermission")
    fun collectCellularDiagnostics(): CellularDiagnosticResult {
        val timestamp = System.currentTimeMillis()

        if (!permissionHelper.hasAllPermissions()) {
            Log.w(TAG, "Permissions denied for cellular diagnostic collection.")
            return CellularDiagnosticResult(
                timestamp = timestamp,
                permissionGranted = false,
                networkOperator = null,
                servingCell = null,
                neighborCells = emptyList()
            )
        }

        val operatorName = try {
            telephonyManager.networkOperatorName.takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            null
        }

        val cellInfoList: List<CellInfo>? = try {
            telephonyManager.allCellInfo
        } catch (e: Exception) {
            Log.e(TAG, "Error calling telephonyManager.allCellInfo: ${e.message}")
            null
        }

        if (cellInfoList.isNullOrEmpty()) {
            Log.w(TAG, "allCellInfo returned empty or null list. Triggering requestCellInfoUpdate...")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                try {
                    telephonyManager.requestCellInfoUpdate(context.mainExecutor, object : TelephonyManager.CellInfoCallback() {
                        override fun onCellInfo(cellInfo: MutableList<CellInfo>) {}
                    })
                } catch (e: Exception) {
                    Log.e(TAG, "requestCellInfoUpdate error: ${e.message}")
                }
            }
            return CellularDiagnosticResult(
                timestamp = timestamp,
                permissionGranted = true,
                networkOperator = operatorName,
                servingCell = null,
                neighborCells = emptyList()
            )
        }

        val parsedRecords = mutableListOf<CellularRecord>()

        for (cellInfo in cellInfoList) {
            val record = parseCellInfo(cellInfo, timestamp, operatorName)
            if (record != null) {
                parsedRecords.add(record)
            }
        }

        val servingCell = parsedRecords.firstOrNull { it.registeredStatus }
        val neighborCells = parsedRecords.filter { !it.registeredStatus }

        return CellularDiagnosticResult(
            timestamp = timestamp,
            permissionGranted = true,
            networkOperator = operatorName ?: servingCell?.networkOperator,
            servingCell = servingCell,
            neighborCells = neighborCells
        )
    }

    private fun parseCellInfo(cellInfo: CellInfo, timestamp: Long, defaultOperator: String?): CellularRecord? {
        val isRegistered = cellInfo.isRegistered

        return when (cellInfo) {
            is CellInfoLte -> parseLte(cellInfo, timestamp, isRegistered, defaultOperator)
            is CellInfoNr -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                parseNr(cellInfo as CellInfoNr, timestamp, isRegistered, defaultOperator)
            } else null
            is CellInfoGsm -> parseGsm(cellInfo, timestamp, isRegistered, defaultOperator)
            is CellInfoWcdma -> parseWcdma(cellInfo, timestamp, isRegistered, defaultOperator)
            is CellInfoCdma -> parseCdma(cellInfo, timestamp, isRegistered, defaultOperator)
            else -> null
        }
    }

    // --- LTE ---
    private fun parseLte(info: CellInfoLte, timestamp: Long, isRegistered: Boolean, defaultOperator: String?): CellularRecord {
        val id = info.cellIdentity
        val ss = info.cellSignalStrength

        val ci = sanitizeLong(id.ci.toLong())
        val mcc = sanitizeMccMnc(id.mccString ?: id.mcc?.toString())
        val mnc = sanitizeMccMnc(id.mncString ?: id.mnc?.toString())
        val tac = sanitizeInt(id.tac)
        val pci = sanitizeInt(id.pci)
        val earfcn = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) sanitizeInt(id.earfcn) else null

        val signalDbm = sanitizeInt(ss.dbm)
        val signalLevel = sanitizeInt(ss.level)

        // Extended research signal metrics
        var rsrp: Int? = null
        var rsrq: Int? = null
        var rssi: Int? = null

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            rsrp = sanitizeInt(ss.rsrp)
            rsrq = sanitizeInt(ss.rsrq)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            rssi = sanitizeInt(ss.rssi)
        }

        val rawDetails = mutableMapOf<String, Any?>()
        if (rsrp != null) rawDetails["rsrp"] = rsrp
        if (rsrq != null) rawDetails["rsrq"] = rsrq
        if (rssi != null) rawDetails["rssi"] = rssi
        if (id.bandwidth != INT_UNAVAILABLE) rawDetails["bandwidth"] = id.bandwidth

        return CellularRecord(
            timestamp = timestamp,
            registeredStatus = isRegistered,
            cellType = "LTE",
            cellId = ci,
            mcc = mcc,
            mnc = mnc,
            lac = null,
            tac = tac,
            pci = pci,
            arfcn = earfcn,
            signalDbm = signalDbm,
            signalLevel = signalLevel,
            networkOperator = defaultOperator,
            signalMetricType = "LTE_RSRP",
            rawSignalValue = rsrp ?: signalDbm,
            rawTechnologyDetails = rawDetails
        )
    }

    // --- 5G NR ---
    private fun parseNr(info: CellInfoNr, timestamp: Long, isRegistered: Boolean, defaultOperator: String?): CellularRecord? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return null

        val id = info.cellIdentity as? CellIdentityNr ?: return null
        val ss = info.cellSignalStrength as? CellSignalStrengthNr

        val nci = sanitizeLong(id.nci)
        val mcc = sanitizeMccMnc(id.mccString)
        val mnc = sanitizeMccMnc(id.mncString)
        val tac = sanitizeInt(id.tac)
        val pci = sanitizeInt(id.pci)
        val nrarfcn = sanitizeInt(id.nrarfcn)

        val signalDbm = ss?.dbm?.let { sanitizeInt(it) }
        val signalLevel = ss?.level?.let { sanitizeInt(it) }

        val ssRsrp = ss?.ssRsrp?.let { sanitizeInt(it) }
        val ssRsrq = ss?.ssRsrq?.let { sanitizeInt(it) }
        val ssSinr = ss?.ssSinr?.let { sanitizeInt(it) }
        val csiRsrp = ss?.csiRsrp?.let { sanitizeInt(it) }
        val csiRsrq = ss?.csiRsrq?.let { sanitizeInt(it) }
        val csiSinr = ss?.csiSinr?.let { sanitizeInt(it) }

        val rawDetails = mutableMapOf<String, Any?>()
        if (ssRsrp != null) rawDetails["ssRsrp"] = ssRsrp
        if (ssRsrq != null) rawDetails["ssRsrq"] = ssRsrq
        if (ssSinr != null) rawDetails["ssSinr"] = ssSinr
        if (csiRsrp != null) rawDetails["csiRsrp"] = csiRsrp
        if (csiRsrq != null) rawDetails["csiRsrq"] = csiRsrq
        if (csiSinr != null) rawDetails["csiSinr"] = csiSinr

        return CellularRecord(
            timestamp = timestamp,
            registeredStatus = isRegistered,
            cellType = "NR",
            cellId = nci,
            mcc = mcc,
            mnc = mnc,
            lac = null,
            tac = tac,
            pci = pci,
            arfcn = nrarfcn,
            signalDbm = signalDbm,
            signalLevel = signalLevel,
            networkOperator = defaultOperator,
            signalMetricType = "NR_SS_RSRP",
            rawSignalValue = ssRsrp ?: signalDbm,
            rawTechnologyDetails = rawDetails
        )
    }

    // --- GSM ---
    private fun parseGsm(info: CellInfoGsm, timestamp: Long, isRegistered: Boolean, defaultOperator: String?): CellularRecord {
        val id = info.cellIdentity
        val ss = info.cellSignalStrength

        val cid = sanitizeLong(id.cid.toLong())
        val mcc = sanitizeMccMnc(id.mccString ?: id.mcc?.toString())
        val mnc = sanitizeMccMnc(id.mncString ?: id.mnc?.toString())
        val lac = sanitizeInt(id.lac)
        val arfcn = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) sanitizeInt(id.arfcn) else null
        val bsic = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) sanitizeInt(id.bsic) else null

        val signalDbm = sanitizeInt(ss.dbm)
        val signalLevel = sanitizeInt(ss.level)

        val rawDetails = mutableMapOf<String, Any?>()
        if (bsic != null) rawDetails["bsic"] = bsic

        return CellularRecord(
            timestamp = timestamp,
            registeredStatus = isRegistered,
            cellType = "GSM",
            cellId = cid,
            mcc = mcc,
            mnc = mnc,
            lac = lac,
            tac = null,
            pci = null,
            arfcn = arfcn,
            signalDbm = signalDbm,
            signalLevel = signalLevel,
            networkOperator = defaultOperator,
            signalMetricType = "GSM_RSSI",
            rawSignalValue = signalDbm,
            rawTechnologyDetails = rawDetails
        )
    }

    // --- WCDMA (3G) ---
    private fun parseWcdma(info: CellInfoWcdma, timestamp: Long, isRegistered: Boolean, defaultOperator: String?): CellularRecord {
        val id = info.cellIdentity
        val ss = info.cellSignalStrength

        val ucid = sanitizeLong(id.cid.toLong())
        val mcc = sanitizeMccMnc(id.mccString ?: id.mcc?.toString())
        val mnc = sanitizeMccMnc(id.mncString ?: id.mnc?.toString())
        val lac = sanitizeInt(id.lac)
        val psc = sanitizeInt(id.psc)
        val uarfcn = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) sanitizeInt(id.uarfcn) else null

        val signalDbm = sanitizeInt(ss.dbm)
        val signalLevel = sanitizeInt(ss.level)

        val rawDetails = mutableMapOf<String, Any?>()
        if (psc != null) rawDetails["psc"] = psc

        return CellularRecord(
            timestamp = timestamp,
            registeredStatus = isRegistered,
            cellType = "WCDMA",
            cellId = ucid,
            mcc = mcc,
            mnc = mnc,
            lac = lac,
            tac = null,
            pci = psc,
            arfcn = uarfcn,
            signalDbm = signalDbm,
            signalLevel = signalLevel,
            networkOperator = defaultOperator,
            signalMetricType = "WCDMA_RSCP",
            rawSignalValue = signalDbm,
            rawTechnologyDetails = rawDetails
        )
    }

    // --- CDMA ---
    private fun parseCdma(info: CellInfoCdma, timestamp: Long, isRegistered: Boolean, defaultOperator: String?): CellularRecord {
        val id = info.cellIdentity
        val ss = info.cellSignalStrength

        val bsId = sanitizeLong(id.basestationId.toLong())
        val signalDbm = sanitizeInt(ss.dbm)
        val signalLevel = sanitizeInt(ss.level)

        return CellularRecord(
            timestamp = timestamp,
            registeredStatus = isRegistered,
            cellType = "CDMA",
            cellId = bsId,
            mcc = null,
            mnc = null,
            lac = sanitizeInt(id.networkId),
            tac = null,
            pci = null,
            arfcn = null,
            signalDbm = signalDbm,
            signalLevel = signalLevel,
            networkOperator = defaultOperator,
            signalMetricType = "CDMA_DBM",
            rawSignalValue = signalDbm,
            rawTechnologyDetails = mapOf("systemId" to id.systemId)
        )
    }

    // --- Sanitization Helpers ---
    private fun sanitizeInt(valInt: Int?): Int? {
        if (valInt == null || valInt == INT_UNAVAILABLE || valInt == Int.MAX_VALUE || valInt == -1 || valInt == 65535) {
            return null
        }
        return valInt
    }

    private fun sanitizeLong(valLong: Long?): Long? {
        if (valLong == null || valLong == LONG_UNAVAILABLE || valLong == Long.MAX_VALUE || valLong == -1L) {
            return null
        }
        return valLong
    }

    private fun sanitizeMccMnc(valStr: String?): String? {
        if (valStr.isNullOrBlank() || valStr == "null" || valStr == "2147483647") {
            return null
        }
        return valStr
    }
}
