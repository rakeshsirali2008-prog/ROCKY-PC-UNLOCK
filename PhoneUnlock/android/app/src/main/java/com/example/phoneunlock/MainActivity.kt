package com.example.phoneunlock

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import java.net.HttpURLConnection
import java.net.URL
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var ipField: EditText
    private lateinit var secretField: EditText
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        ipField = findViewById(R.id.ip)
        secretField = findViewById(R.id.secret)
        status = findViewById(R.id.status)

        val prefs = getSharedPreferences("cfg", MODE_PRIVATE)
        ipField.setText(prefs.getString("ip", ""))
        secretField.setText(prefs.getString("secret", ""))

        findViewById<Button>(R.id.unlock).setOnClickListener {
            val ip = ipField.text.toString().trim()
            val secret = secretField.text.toString()
            if (ip.isEmpty() || secret.isEmpty()) {
                status.text = "Enter the PC IP and the secret first."
                return@setOnClickListener
            }
            prefs.edit().putString("ip", ip).putString("secret", secret).apply()
            askBiometric(ip, secret)
        }
    }

    private fun askBiometric(ip: String, secret: String) {
        val executor = ContextCompat.getMainExecutor(this)
        val prompt = BiometricPrompt(this, executor, object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                status.text = "Verified. Contacting PC..."
                sendUnlock(ip, secret)
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                status.text = "Not verified: $errString"
            }
        })
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock PC")
            .setSubtitle("Use your fingerprint or face")
            .setAllowedAuthenticators(BIOMETRIC_STRONG or DEVICE_CREDENTIAL)
            .build()
        prompt.authenticate(info)
    }

    private fun sendUnlock(ip: String, secret: String) {
        thread {
            val msg = try {
                val t = (System.currentTimeMillis() / 1000).toString()
                val mac = Mac.getInstance("HmacSHA256")
                mac.init(SecretKeySpec(secret.toByteArray(), "HmacSHA256"))
                val sig = mac.doFinal(t.toByteArray()).joinToString("") { "%02x".format(it) }

                val host = if (ip.contains(":")) ip else "$ip:8765"
                val conn = URL("http://$host/unlock").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.connectTimeout = 4000
                conn.readTimeout = 10000
                conn.setRequestProperty("X-Time", t)
                conn.setRequestProperty("X-Sig", sig)
                conn.doOutput = true
                conn.setFixedLengthStreamingMode(0)
                conn.outputStream.close()

                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val body = stream?.bufferedReader()?.readText() ?: ""
                "PC says ($code): $body"
            } catch (e: Exception) {
                "Could not reach PC: ${e.message}"
            }
            runOnUiThread { status.text = msg }
        }
    }
}
