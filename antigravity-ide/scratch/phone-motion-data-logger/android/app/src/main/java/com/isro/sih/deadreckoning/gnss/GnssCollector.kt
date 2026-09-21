package com.isro.sih.deadreckoning.gnss

import android.annotation.SuppressLint
import android.content.Context
import android.location.*
import android.os.Build
import android.util.Log
import java.util.concurrent.atomic.AtomicLong

data class GnssReading(
    val timestampMs: Long,
    val hasFix: Boolean,
    val latitude: Double?,
    val longitude: Double?,
    val altitude: Double?,
    val accuracy: Float?,
    val speed: Float?,
    val bearing: Float?,
    val satellitesInView: Int,
    val satellitesUsedInFix: Int
)

class GnssCollector(
    private val context: Context,
    private val onGnssData: (GnssReading) -> Unit
) {

    private val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

    @Volatile
    var isRunning = false
        private set

    val fixesCount = AtomicLong(0)
    val satelliteRecordsCount = AtomicLong(0)

    @Volatile var latestLatitude: Double? = null
    @Volatile var latestLongitude: Double? = null
    @Volatile var latestAltitude: Double? = null
    @Volatile var latestAccuracy: Float? = null
    @Volatile var latestSpeed: Float? = null
    @Volatile var latestBearing: Float? = null
    @Volatile var satellitesInView = 0
    @Volatile var satellitesUsedInFix = 0
    @Volatile var hasFix = false

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            hasFix = true
            latestLatitude = location.latitude
            latestLongitude = location.longitude
            latestAltitude = if (location.hasAltitude()) location.altitude else null
            latestAccuracy = if (location.hasAccuracy()) location.accuracy else null
            latestSpeed = if (location.hasSpeed()) location.speed else null
            latestBearing = if (location.hasBearing()) location.bearing else null

            fixesCount.incrementAndGet()

            val reading = GnssReading(
                timestampMs = location.time.takeIf { it > 0 } ?: System.currentTimeMillis(),
                hasFix = true,
                latitude = latestLatitude,
                longitude = latestLongitude,
                altitude = latestAltitude,
                accuracy = latestAccuracy,
                speed = latestSpeed,
                bearing = latestBearing,
                satellitesInView = satellitesInView,
                satellitesUsedInFix = satellitesUsedInFix
            )

            onGnssData(reading)
        }

        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) {}
        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {
            hasFix = false
        }
    }

    private val gnssStatusCallback = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
        object : GnssStatus.Callback() {
            override fun onSatelliteStatusChanged(status: GnssStatus) {
                var totalSatellites = status.satelliteCount
                var usedSatellites = 0
                for (i in 0 until totalSatellites) {
                    if (status.usedInFix(i)) {
                        usedSatellites++
                    }
                }
                satellitesInView = totalSatellites
                satellitesUsedInFix = usedSatellites

                satelliteRecordsCount.incrementAndGet()

                val reading = GnssReading(
                    timestampMs = System.currentTimeMillis(),
                    hasFix = hasFix,
                    latitude = latestLatitude,
                    longitude = latestLongitude,
                    altitude = latestAltitude,
                    accuracy = latestAccuracy,
                    speed = latestSpeed,
                    bearing = latestBearing,
                    satellitesInView = totalSatellites,
                    satellitesUsedInFix = usedSatellites
                )

                onGnssData(reading)
            }
        }
    } else null

    @SuppressLint("MissingPermission")
    fun start() {
        if (isRunning) stop()

        try {
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    1000L,
                    0f,
                    locationListener
                )
            }
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER,
                    1000L,
                    0f,
                    locationListener
                )
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && gnssStatusCallback != null) {
                locationManager.registerGnssStatusCallback(context.mainExecutor, gnssStatusCallback)
            }
            isRunning = true
        } catch (e: Exception) {
            Log.e("GnssCollector", "Error starting GNSS collector: ${e.message}")
        }
    }

    fun stop() {
        if (!isRunning) return
        try {
            locationManager.removeUpdates(locationListener)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && gnssStatusCallback != null) {
                locationManager.unregisterGnssStatusCallback(gnssStatusCallback)
            }
        } catch (e: Exception) {
            Log.e("GnssCollector", "Error stopping GNSS collector: ${e.message}")
        }
        isRunning = false
        hasFix = false
    }
}
