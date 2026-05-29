package com.signage.player.util

import kotlin.math.min
import kotlin.random.Random

/**
 * Exponential backoff with jitter (§25)
 *
 * รูปแบบ:
 *   - success() → ล้าง counter, รอบถัดไปกลับมา baseMs
 *   - fail()    → ทบ counter, delay = min(maxMs, base * 2^n) + jitter(0-30%)
 *
 * ใช้ใน heartbeat / command pull / manifest fetch — กัน server พังจาก thundering herd
 *
 * Thread-safe? — ไม่ — ออกแบบให้ใช้ต่อ 1 coroutine loop
 */
class Backoff(
    private val baseMs: Long,
    private val maxMs: Long = 5 * 60_000L,    // เพดาน 5 นาที
    private val jitterPercent: Double = 0.3,
) {
    private var consecutiveFails = 0

    fun success() {
        consecutiveFails = 0
    }

    fun fail() {
        consecutiveFails++
    }

    /** คืนค่า delay (ms) ที่ควรรอก่อนรอบถัดไป */
    fun nextDelayMs(): Long {
        if (consecutiveFails == 0) return baseMs
        // 2^n × base — ระวัง overflow
        val shift = min(consecutiveFails, 20)
        val expo = min(maxMs, baseMs shl shift)
        val jitter = (expo * jitterPercent * Random.nextDouble()).toLong()
        return expo + jitter
    }

    fun consecutiveFailCount(): Int = consecutiveFails
}
