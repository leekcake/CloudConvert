package moe.leekcake.cloudconvert

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import com.arthenica.mobileffmpeg.Config
import com.arthenica.mobileffmpeg.FFmpeg
import java.io.*
import java.net.Socket

class MyService : Service() {
    private val CHANNEL_ID = "CloudConvert Service"
    val MOBILE_FFMPEG_PIPE_PREFIX = "mf_pipe_"

    fun copyStreamAndClose(src: InputStream, dest: OutputStream, count: Int, close: Boolean = true) {
        var left = count
        var readed: Int
        val buf = ByteArray(1024)
        while (left != 0) {
            if (count == -1) {
                readed = src.read(buf, 0, 1024)
            } else {
                readed = src.read(buf, 0, Math.min(1024, left))
            }

            if (readed == -1) {
                if (count == -1) {
                    break
                }
                try {
                    Thread.sleep(10)
                } catch (e: InterruptedException) {
                    e.printStackTrace()
                }

                continue
            }
            left -= readed
            dest.write(buf, 0, readed)
        }
        if (close) {
            dest.close()
        }
    }

    override fun onBind(intent: Intent): IBinder? {
        return null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID, "CloudConvert Service Channel",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager!!.createNotificationChannel(serviceChannel)
        }
    }

    private var isPerformed = false

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (isPerformed) {
            Log.i("CloudConvert", "Duplicate start command?")
            return START_STICKY
        }

        isPerformed = true
        createNotificationChannel()
        val handler = Handler(Looper.getMainLooper())

        val notiManager = getSystemService(NotificationManager::class.java)
        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("CloudConvert")
            .setContentText("Starting")
            .setSmallIcon(R.drawable.ic_launcher_foreground)

        startForeground(1, builder.build())

        fun makeLogAndUpdate(text: String) {
            Log.i("CloudConvert", text)
            builder.setContentText(text)
            handler.postDelayed({
                notiManager.notify(1, builder.build())
            }, 100)
        }

        val thread = Thread {
            val addr = "192.168.0.139"
            Thread.sleep(1000)
            while (true) {
                try {
                    makeLogAndUpdate("서버와 연결 시도중...")
                    val socket: Socket
                    try {
                        socket = Socket(addr, 39000)
                    } catch (ex: Exception) {
                        makeLogAndUpdate("오류: 연결 불가")
                        Thread.sleep(10000)
                        continue
                    }
                    val In = DataInputStream(socket.getInputStream())
                    val Out = DataOutputStream(socket.getOutputStream())

                    val header = ByteArray(5)
                    In.readFully(header)

                    if (String(header) != "Node?") {
                        socket.close()
                        makeLogAndUpdate("오류: 호스트 비 정상")
                        Thread.sleep(10000)
                        continue
                    }
                    Out.write("Yes!".toByteArray())

                    while (true) {
                        makeLogAndUpdate("새 작업 대기")
                        val dataLen = In.readInt()

                        makeLogAndUpdate("새 작업 요청, 변환 준비중")
                        val inputPipe = Config.registerNewFFmpegPipe(applicationContext)
                        val outputPipe = Config.registerNewFFmpegPipe(applicationContext)
                        val executeLine =
                            "-y -f mpegts -i $inputPipe -preset veryfast -c:v libx264 -c:a aac -f mpegts $outputPipe"
                        Log.i("CloudConvert", executeLine)
                        val ffmpeg = Thread {
                            try {
                                FFmpeg.execute(executeLine)
                            } catch (ex: Exception) {
                                ex.printStackTrace()
                            }
                        }
                        ffmpeg.start()

                        //We need to provide to ffmpeg's "input"
                        //We need to get data from ffmpeg's "output"
                        val ffIn = FileOutputStream(inputPipe)
                        var error = false

                        makeLogAndUpdate("작업 데이터 변환중")
                        val copy = Thread {
                            try {
                                copyStreamAndClose(In, ffIn, dataLen)
                            } catch (ex: Exception) {
                                error = true
                                ex.printStackTrace()
                                ffIn.close()
                                ffmpeg.interrupt()
                            }
                        }
                        copy.start()

                        val ffOut = FileInputStream(outputPipe)
                        val result = ByteArrayOutputStream()

                        var readed: Int
                        val buf = ByteArray(1024)
                        while (true) {
                            readed = ffOut.read(buf, 0, 1024)
                            if (readed == -1) {
                                if (!ffmpeg.isAlive) {
                                    break
                                }
                                try {
                                    Thread.sleep(10)
                                } catch (e: InterruptedException) {
                                    e.printStackTrace()
                                }

                                continue
                            }
                            result.write(buf, 0, readed)
                        }
                        ffOut.close()
                        Config.closeFFmpegPipe(inputPipe)
                        Config.closeFFmpegPipe(outputPipe)
                        if(error) {
                            makeLogAndUpdate("작업중 오류 발생, 연결을 끊고 재시도")
                            try {
                                socket.close()
                            } catch (ex: java.lang.Exception) {

                            }
                            throw java.lang.Exception("Error on Convert")
                        }
                        makeLogAndUpdate("작업 결과물 전송중")
                        val resultBA = result.toByteArray()
                        val bais = ByteArrayInputStream(resultBA)

                        Out.write("Done!".toByteArray())
                        Out.writeInt(resultBA.size)
                        copyStreamAndClose(bais, Out, resultBA.size, false)
                    }
                } catch (ex: Exception) {
                    ex.printStackTrace()
                    makeLogAndUpdate("예외: ${ex.message}")
                    Thread.sleep(1000)
                }
            }
        }
        thread.start()

        return START_STICKY
    }
}
