package com.signage.player

import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.signage.player.api.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Entry — ถ้ายัง pair ไม่ได้ → แสดงหน้า input pairing code
 * ถ้า pair แล้ว → เปิด WebView fullscreen + เรียก PlayerService (heartbeat + TV command loop)
 *
 * NOTE: นี่เป็น scaffold เริ่มต้น — Phase ถัดไปจะเพิ่ม:
 *  - manifest renderer จริง (parse JSON → render presentation/zones)
 *  - boot sequence ตาม §25
 *  - cache offline (Room DB)
 *  - LRU eviction ของ media
 */
class MainActivity : AppCompatActivity() {

    private val prefs: SharedPreferences by lazy { getSharedPreferences("signage", MODE_PRIVATE) }
    private val scope = CoroutineScope(Dispatchers.Main)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // เปิด full-screen + keep screen on
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )

        val token = prefs.getString("device_token", null)
        if (token.isNullOrBlank()) {
            showPairingScreen()
        } else {
            showPlayer()
        }
    }

    // ── Pairing UI ────────────────────────────────────────────────────────────

    private fun showPairingScreen() {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 64, 64, 64)
        }
        val title = TextView(this).apply {
            text = "ใส่ Pairing Code 6 ตัว"
            textSize = 24f
        }
        val urlInput = EditText(this).apply {
            hint = "Server URL (เช่น http://192.168.1.10:8000)"
            setText(prefs.getString("server_url", "http://192.168.1.10:8000"))
        }
        val codeInput = EditText(this).apply {
            hint = "Pairing code"
            textSize = 32f
        }
        val btn = Button(this).apply { text = "Pair" }
        val status = TextView(this)

        btn.setOnClickListener {
            val baseUrl = urlInput.text.toString().trim().trimEnd('/')
            val code = codeInput.text.toString().trim().uppercase()
            if (baseUrl.isEmpty() || code.isEmpty()) {
                Toast.makeText(this, "กรุณากรอก server + code", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            prefs.edit().putString("server_url", baseUrl).apply()
            status.text = "กำลัง pair..."
            scope.launch {
                val result = runCatching {
                    val api = ApiClient(baseUrl) { null }
                    withContext(Dispatchers.IO) {
                        api.pair(code, mac = null, serial = null, appVersion = "0.1.0")
                    }
                }
                result.onSuccess { resp ->
                    prefs.edit()
                        .putString("device_id", resp.device_id)
                        .putString("device_token", resp.device_token)
                        .apply()
                    showPlayer()
                }.onFailure { e ->
                    status.text = "ผิดพลาด: ${e.message}"
                }
            }
        }

        container.addView(title)
        container.addView(urlInput)
        container.addView(codeInput)
        container.addView(btn)
        container.addView(status)
        setContentView(container)
    }

    // ── Player (WebView placeholder) ──────────────────────────────────────────

    private fun showPlayer() {
        // start background service (heartbeat + TV command)
        startService(Intent(this, PlayerService::class.java))

        val container = FrameLayout(this)
        val webView = WebView(this).apply {
            webViewClient = WebViewClient()
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
        }
        // Phase ถัดไปจะ render manifest JSON เป็น layout จริง — ตอนนี้แสดง placeholder
        webView.loadData(
            """
            <html><body style="background:black;color:white;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">
            <div style="text-align:center">
              <h1>📺 Signage Player</h1>
              <p>Paired ✓ — กำลังรอ manifest จาก backend</p>
              <p style="opacity:0.5">device_id: ${prefs.getString("device_id", "?")}</p>
            </div></body></html>
            """.trimIndent(),
            "text/html",
            "UTF-8",
        )
        container.addView(webView)
        setContentView(container)
    }
}
