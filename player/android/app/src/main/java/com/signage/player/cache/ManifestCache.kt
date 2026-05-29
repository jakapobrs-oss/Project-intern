package com.signage.player.cache

import android.content.Context
import android.util.Log
import java.io.File
import java.security.MessageDigest

/**
 * Media file cache สำหรับ manifest content (§25)
 *
 * - เก็บไฟล์ใน app private dir: `<filesDir>/media-cache/<sha1(url)>`
 * - LRU eviction เมื่อขนาดรวม > MAX_BYTES (sort by lastModified asc → ลบเก่าก่อน)
 * - thread-safe: synchronize เฉพาะตอน evict (read/write file ใช้ FS lock ของ OS)
 *
 * ตอนนี้ยังไม่ wire กับ manifest renderer — เป็น util ให้ phase ถัดไปเรียก
 */
class ManifestCache(context: Context) {
    private val cacheDir: File = File(context.filesDir, "media-cache").apply { mkdirs() }

    /** path ของไฟล์ใน cache สำหรับ URL นี้ (ไม่ได้ดาวน์โหลด — แค่คำนวณ path) */
    fun fileFor(url: String): File = File(cacheDir, sha1(url))

    fun hasCached(url: String): Boolean = fileFor(url).exists()

    /** บันทึก response body ลง cache + run eviction */
    @Synchronized
    fun put(url: String, bytes: ByteArray) {
        val f = fileFor(url)
        try {
            f.outputStream().use { it.write(bytes) }
            evictIfOversize()
        } catch (e: Exception) {
            Log.w(TAG, "cache put failed: $url — ${e.message}")
        }
    }

    /** อ่าน bytes จาก cache (null = ไม่มี) */
    fun get(url: String): ByteArray? {
        val f = fileFor(url)
        if (!f.exists()) return null
        // touch — update lastModified ให้ LRU เห็นว่าใช้งานล่าสุด
        f.setLastModified(System.currentTimeMillis())
        return try { f.readBytes() } catch (e: Exception) { null }
    }

    /** ลบทั้ง cache (call ตอน logout/unpair) */
    @Synchronized
    fun clear() {
        cacheDir.listFiles()?.forEach { it.delete() }
    }

    fun totalBytes(): Long =
        cacheDir.listFiles()?.sumOf { it.length() } ?: 0L

    /** LRU eviction — ลบไฟล์ที่ lastModified เก่าสุดจนกว่า total ≤ 80% MAX */
    @Synchronized
    private fun evictIfOversize() {
        val files = cacheDir.listFiles() ?: return
        var total = files.sumOf { it.length() }
        if (total <= MAX_BYTES) return

        val target = (MAX_BYTES * 0.8).toLong()
        val sorted = files.sortedBy { it.lastModified() }   // เก่าสุดก่อน
        for (f in sorted) {
            if (total <= target) break
            val sz = f.length()
            if (f.delete()) total -= sz
        }
        Log.i(TAG, "media-cache evicted → ${total / 1024 / 1024}MB")
    }

    private fun sha1(s: String): String {
        val md = MessageDigest.getInstance("SHA-1")
        val bytes = md.digest(s.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val TAG = "ManifestCache"
        const val MAX_BYTES = 500L * 1024 * 1024    // 500 MB sync กับ web sw.js
    }
}
