package com.signage.player

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat
import com.signage.player.api.ApiClient
import com.signage.player.cache.ManifestCache
import com.signage.player.tv.TvSerialBridge
import com.signage.player.util.Backoff
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Foreground service ที่รัน 3 loop:
 *  1) heartbeat ทุก 30s (+ trigger manifest refresh เมื่อ outdated)
 *  2) manifest fetch on-demand (เก็บ raw JSON ไว้ใน sharedPrefs + cache media)
 *  3) TV command pull ทุก 5s + ack ผลลัพธ์
 *
 * Phase 4 polish (Option F):
 *  - ใช้ Backoff util ทั้ง 3 loop (กัน thundering herd)
 *  - บันทึก manifest version + raw payload ลง prefs (recovery หลัง crash)
 *  - ManifestCache สำหรับ media pre-fetch (ยังไม่ wire กับ render layer)
 */
class PlayerService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val bootTime = SystemClock.elapsedRealtime()
    private lateinit var api: ApiClient
    private lateinit var tv: TvSerialBridge
    private lateinit var cache: ManifestCache

    private var heartbeatJob: Job? = null
    private var commandJob: Job? = null
    private var currentManifestVersion: String? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIF_ID, buildNotif())

        val prefs = getSharedPreferences("signage", MODE_PRIVATE)
        val baseUrl = prefs.getString("server_url", "")!!
        api = ApiClient(baseUrl) { prefs.getString("device_token", null) }
        tv = TvSerialBridge(this)
        cache = ManifestCache(this)

        // recovery: โหลด version ล่าสุดจาก prefs เผื่อ service ถูก kill แล้ว restart
        currentManifestVersion = prefs.getString("manifest_version", null)

        heartbeatJob = scope.launch { runHeartbeatLoop(prefs) }
        commandJob = scope.launch { runCommandLoop() }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    // ── Heartbeat loop ────────────────────────────────────────────────────────

    private suspend fun runHeartbeatLoop(prefs: android.content.SharedPreferences) {
        val backoff = Backoff(baseMs = HEARTBEAT_INTERVAL_MS)
        while (true) {
            try {
                val uptimeSec = (SystemClock.elapsedRealtime() - bootTime) / 1000
                val resp = api.heartbeat(
                    ApiClient.HeartbeatRequest(
                        status = "online",
                        app_version = APP_VERSION,
                        uptime_sec = uptimeSec,
                        current_manifest_version = currentManifestVersion,
                    )
                )
                Log.d(TAG, "heartbeat: outdated=${resp.manifest_outdated} ver=${resp.latest_manifest_version}")

                if (resp.manifest_outdated) {
                    refreshManifest(prefs)
                }
                backoff.success()
            } catch (e: Exception) {
                Log.w(TAG, "heartbeat fail (#${backoff.consecutiveFailCount() + 1}): ${e.message}")
                backoff.fail()
            }
            delay(backoff.nextDelayMs())
        }
    }

    /**
     * ดึง manifest ใหม่ + บันทึก version ลง prefs + pre-cache media
     * (ส่วน render จริงทำใน MainActivity / WebView — service แค่ fetch + cache)
     */
    private fun refreshManifest(prefs: android.content.SharedPreferences) {
        try {
            val raw = api.getManifest()
            prefs.edit().putString("manifest_raw", raw).apply()

            // ดึง version จาก JSON แบบ lightweight (regex) — ไม่ parse model เต็ม
            val versionMatch = Regex(""""version"\s*:\s*"([^"]+)"""").find(raw)
            versionMatch?.groupValues?.get(1)?.let {
                currentManifestVersion = it
                prefs.edit().putString("manifest_version", it).apply()
            }

            // pre-cache content URLs (best-effort)
            preCacheMediaUrls(raw)
            Log.i(TAG, "manifest refreshed → version=$currentManifestVersion")
        } catch (e: Exception) {
            Log.w(TAG, "manifest refresh fail: ${e.message}")
        }
    }

    /**
     * ดึง content_url ทุกอันใน manifest แล้ว download ใส่ cache
     * lightweight regex parser — ไม่ใช้ JSON lib เพื่อไม่ผูก dependency เพิ่ม
     */
    private fun preCacheMediaUrls(rawJson: String) {
        val urlPattern = Regex(""""content_url"\s*:\s*"([^"]+)"""")
        val typePattern = Regex(""""content_type"\s*:\s*"([^"]+)"""")
        val urls = urlPattern.findAll(rawJson).map { it.groupValues[1] }.toList()
        val types = typePattern.findAll(rawJson).map { it.groupValues[1] }.toList()

        for ((i, url) in urls.withIndex()) {
            val type = types.getOrNull(i) ?: continue
            if (type != "image" && type != "video") continue
            if (cache.hasCached(url)) continue
            scope.launch {
                try {
                    val bytes = downloadBytes(url) ?: return@launch
                    cache.put(url, bytes)
                } catch (e: Exception) {
                    Log.w(TAG, "pre-cache fail $url: ${e.message}")
                }
            }
        }
    }

    private fun downloadBytes(url: String): ByteArray? {
        return try {
            val conn = java.net.URL(url).openConnection()
            conn.connectTimeout = 10_000
            conn.readTimeout = 60_000
            conn.getInputStream().use { it.readBytes() }
        } catch (e: Exception) {
            null
        }
    }

    // ── Command loop ──────────────────────────────────────────────────────────

    private suspend fun runCommandLoop() {
        val backoff = Backoff(baseMs = COMMAND_INTERVAL_MS)
        while (true) {
            try {
                val cmds = api.pullCommands()
                for (cmd in cmds) {
                    val (success, msg) = tv.sendBytes(cmd.raw_bytes_hex, cmd.brand)
                    Log.i(TAG, "exec ${cmd.cmd_id} ${cmd.command_type}: $msg")
                    api.ackCommand(cmd.cmd_id, success, if (success) null else msg)
                }
                backoff.success()
            } catch (e: Exception) {
                Log.w(TAG, "command loop fail (#${backoff.consecutiveFailCount() + 1}): ${e.message}")
                backoff.fail()
            }
            delay(backoff.nextDelayMs())
        }
    }

    // ── Foreground notification ───────────────────────────────────────────────

    private fun buildNotif(): Notification {
        val mgr = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL, "Signage Player", NotificationManager.IMPORTANCE_LOW)
            mgr.createNotificationChannel(channel)
        }
        return NotificationCompat.Builder(this, CHANNEL)
            .setContentTitle("Signage Player")
            .setContentText("ทำงานอยู่")
            .setSmallIcon(android.R.drawable.ic_menu_slideshow)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val TAG = "PlayerService"
        private const val CHANNEL = "signage_player"
        private const val NOTIF_ID = 1
        private const val HEARTBEAT_INTERVAL_MS = 30_000L
        private const val COMMAND_INTERVAL_MS = 5_000L
        private const val APP_VERSION = "0.2.0"
    }
}
