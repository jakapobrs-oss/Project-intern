package com.signage.player.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Client เรียก backend API ฝั่ง player (§13, §35.2)
 * ใช้ device_token ที่ได้จากตอน pair
 */
class ApiClient(
    private val baseUrl: String,                          // e.g. http://192.168.1.10:8000
    private val tokenProvider: () -> String?,             // device_token (null = ยังไม่ pair)
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = false }

    // ── DTOs ──────────────────────────────────────────────────────────────────

    @Serializable
    data class PairRequest(
        val pairing_code: String,
        val platform: String = "android_tv",
        val mac_address: String? = null,
        val serial_number: String? = null,
        val app_version: String? = null,
    )

    @Serializable
    data class PairResponse(
        val device_id: String,
        val device_token: String,
        val server_time: String,
    )

    @Serializable
    data class HeartbeatRequest(
        val status: String = "online",
        val app_version: String? = null,
        val cpu_percent: Double? = null,
        val temperature_c: Double? = null,
        val uptime_sec: Long? = null,
        val current_manifest_version: String? = null,
    )

    @Serializable
    data class HeartbeatResponse(
        val server_time: String,
        val manifest_outdated: Boolean,
        val latest_manifest_version: String?,
    )

    @Serializable
    data class TVCommandInQueue(
        val cmd_id: String,
        val brand: String,
        val command_type: String,
        val raw_bytes_hex: String,           // ← raw bytes ที่ backend สร้างให้แล้ว
        val set_id: Int = 0,
        val attempts: Int = 1,
    )

    @Serializable
    data class TVCommandAckBody(val success: Boolean, val error: String? = null)

    // ── API methods ───────────────────────────────────────────────────────────

    fun pair(pairingCode: String, mac: String?, serial: String?, appVersion: String): PairResponse {
        val body = json.encodeToString(
            PairRequest.serializer(),
            PairRequest(pairingCode, "android_tv", mac, serial, appVersion),
        )
        return postJson("/api/v1/player/pair", body, requireAuth = false, PairResponse.serializer())
    }

    fun heartbeat(req: HeartbeatRequest): HeartbeatResponse {
        val body = json.encodeToString(HeartbeatRequest.serializer(), req)
        return postJson("/api/v1/player/heartbeat", body, requireAuth = true, HeartbeatResponse.serializer())
    }

    /** ดึง manifest JSON ดิบ (parse แยกใน ManifestRenderer) */
    fun getManifest(): String = getRaw("/api/v1/player/manifest", requireAuth = true)

    fun pullCommands(): List<TVCommandInQueue> {
        val body = getRaw("/api/v1/player/commands", requireAuth = true)
        return json.decodeFromString(
            kotlinx.serialization.builtins.ListSerializer(TVCommandInQueue.serializer()),
            body,
        )
    }

    fun ackCommand(cmdId: String, success: Boolean, error: String? = null) {
        val body = json.encodeToString(TVCommandAckBody.serializer(), TVCommandAckBody(success, error))
        postJsonNoResp("/api/v1/player/commands/$cmdId/ack", body, requireAuth = true)
    }

    // ── HTTP helpers ──────────────────────────────────────────────────────────

    private fun <T> postJson(
        path: String,
        body: String,
        requireAuth: Boolean,
        deserializer: kotlinx.serialization.DeserializationStrategy<T>,
    ): T {
        val req = newRequest(path, requireAuth).post(body.toRequestBody("application/json".toMediaType())).build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            check(resp.isSuccessful) { "HTTP ${resp.code}: $text" }
            return json.decodeFromString(deserializer, text)
        }
    }

    private fun postJsonNoResp(path: String, body: String, requireAuth: Boolean) {
        val req = newRequest(path, requireAuth).post(body.toRequestBody("application/json".toMediaType())).build()
        client.newCall(req).execute().use { resp ->
            check(resp.isSuccessful) { "HTTP ${resp.code}" }
        }
    }

    private fun getRaw(path: String, requireAuth: Boolean): String {
        val req = newRequest(path, requireAuth).get().build()
        client.newCall(req).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            check(resp.isSuccessful) { "HTTP ${resp.code}: $text" }
            return text
        }
    }

    private fun newRequest(path: String, requireAuth: Boolean): Request.Builder {
        val b = Request.Builder().url("$baseUrl$path")
        if (requireAuth) {
            val token = tokenProvider() ?: error("ยังไม่ได้ pair — ไม่มี device_token")
            b.header("Authorization", "Bearer $token")
        }
        return b
    }
}
