package com.signage.player.tv

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import com.hoho.android.usbserial.driver.Ch34xSerialDriver
import com.hoho.android.usbserial.driver.Cp21xxSerialDriver
import com.hoho.android.usbserial.driver.FtdiSerialDriver
import com.hoho.android.usbserial.driver.ProlificSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort

/**
 * ส่ง raw bytes ที่ backend สร้างไว้แล้ว ผ่าน USB-to-Serial chip (§36)
 *
 * หลักการ: backend รู้ brand → คำนวณ raw_bytes_hex มาให้แล้ว
 *          player แค่ open serial + write (ไม่ต้องคำนวณ command เอง)
 */
class TvSerialBridge(private val context: Context) {

    private val usbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager

    companion object {
        private const val ACTION_USB_PERMISSION = "com.signage.player.USB_PERMISSION"
        private const val WRITE_TIMEOUT_MS = 2000
        // baud rate ต่อ brand — ระบบใหม่อ่านจาก backend ได้ Phase ถัดไป
        private val DEFAULT_BAUD_RATE = mapOf(
            "samsung" to 9600,
            "lg" to 9600,
            "sony" to 9600,
            "panasonic" to 19200,
            "nec" to 9600,
            "toshiba" to 9600,
        )
    }

    enum class Chip { FTDI, CP210X, CH340, PL2303 }

    /**
     * ส่ง command บล็อก (caller ต้องเรียกจาก coroutine/background thread)
     * คืน Pair<success, message>
     */
    fun sendBytes(
        rawBytesHex: String,
        brand: String,
        chip: Chip = Chip.FTDI,
    ): Pair<Boolean, String> {
        val bytes = try {
            hexToBytes(rawBytesHex)
        } catch (e: IllegalArgumentException) {
            return false to "invalid hex string: ${e.message}"
        }

        val device = findUsbDevice() ?: return false to "USB device not found"

        if (!usbManager.hasPermission(device)) {
            return false to "USB permission not granted — call requestPermission() first"
        }

        val driver = buildDriver(chip, device) ?: return false to "cannot open driver for $chip"
        val connection = usbManager.openDevice(driver.device) ?: return false to "cannot open USB connection"

        return try {
            val port = driver.ports[0]
            port.open(connection)
            port.setParameters(
                DEFAULT_BAUD_RATE[brand.lowercase()] ?: 9600,
                8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE,
            )
            port.write(bytes, WRITE_TIMEOUT_MS)
            port.close()
            true to "sent ${bytes.size} bytes @ ${DEFAULT_BAUD_RATE[brand] ?: 9600} bps"
        } catch (e: Exception) {
            false to "error: ${e.message}"
        } finally {
            connection.close()
        }
    }

    /** ขอ USB permission async — callback granted/denied */
    fun requestPermission(onResult: (Boolean) -> Unit) {
        val device = findUsbDevice() ?: return onResult(false)
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                context.unregisterReceiver(this)
                onResult(intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false))
            }
        }
        context.registerReceiver(
            receiver,
            IntentFilter(ACTION_USB_PERMISSION),
            Context.RECEIVER_NOT_EXPORTED,
        )
        val pi = PendingIntent.getBroadcast(
            context, 0,
            Intent(ACTION_USB_PERMISSION),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        usbManager.requestPermission(device, pi)
    }

    private fun findUsbDevice(): UsbDevice? = usbManager.deviceList.values.firstOrNull()

    private fun buildDriver(chip: Chip, device: UsbDevice): UsbSerialDriver? = when (chip) {
        Chip.FTDI -> FtdiSerialDriver(device)
        Chip.CP210X -> Cp21xxSerialDriver(device)
        Chip.CH340 -> Ch34xSerialDriver(device)
        Chip.PL2303 -> ProlificSerialDriver(device)
    }

    private fun hexToBytes(hex: String): ByteArray {
        val cleaned = hex.replace(" ", "").replace(":", "")
        require(cleaned.length % 2 == 0) { "hex length must be even" }
        return ByteArray(cleaned.length / 2) { i ->
            cleaned.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
    }
}
