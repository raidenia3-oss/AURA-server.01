package com.ame.ecosystem;

import android.annotation.SuppressLint;
import android.content.SharedPreferences;
import android.graphics.*;
import android.os.Build;
import android.service.wallpaper.WallpaperService;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.util.Log;
import android.view.SurfaceHolder;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

/**
 * CyberLiveWallpaperService — Live Wallpaper con efecto Parallax por giroscopio.
 *
 * Toma las capas generadas por AURA (subject.png + background.png)
 * y aplica movimiento fluido al inclinar el teléfono usando sensor TYPE_GAME_ROTATION_VECTOR.
 *
 * Para activar: el usuario selecciona "Fondo dinámico" en ajustes de AME App.
 */
public class CyberLiveWallpaperService extends WallpaperService {

    private static final String TAG = "AURA-CyberLiveWP";
    private static final float PARALLAX_SCALE = 15f;
    private static final float LERP_SPEED = 0.08f;

    @Override
    public Engine onCreateEngine() {
        return new CyberLiveEngine();
    }

    private class CyberLiveEngine extends Engine implements SensorEventListener {

        private SensorManager sensorManager;
        private Sensor rotationSensor;
        private float currentX = 0f, currentY = 0f;
        private float targetX = 0f, targetY = 0f;
        private Bitmap bgBitmap = null;
        private Bitmap subjectBitmap = null;
        private boolean sensorsRegistered = false;
        private long lastFrameTime = 0;
        private int screenWidth = 1080;
        private int screenHeight = 1920;

        @Override
        public void onCreate(SurfaceHolder surfaceHolder) {
            super.onCreate(surfaceHolder);
            sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
            if (sensorManager != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR2) {
                    rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
                }
                if (rotationSensor == null) {
                    rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
                }
            }
            loadLayerImages();
            setTouchEventsEnabled(false);
        }

        private void loadLayerImages() {
            try {
                File cacheDir = getFilesDir();
                File bgFile = new File(cacheDir, "layer_background.png");
                File subjFile = new File(cacheDir, "layer_subject.png");
                if (bgFile.exists()) {
                    bgBitmap = BitmapFactory.decodeStream(new FileInputStream(bgFile));
                }
                if (subjFile.exists()) {
                    subjectBitmap = BitmapFactory.decodeStream(new FileInputStream(subjFile));
                }
                Log.i(TAG, "Layers loaded: bg=" + (bgBitmap != null) + " subject=" + (subjectBitmap != null));
            } catch (IOException e) {
                Log.e(TAG, "Failed to load layers", e);
            }
        }

        @Override
        public void onSurfaceChanged(SurfaceHolder holder, int format, int width, int height) {
            super.onSurfaceChanged(holder, format, width, height);
            screenWidth = width;
            screenHeight = height;
        }

        @Override
        public void onVisibilityChanged(boolean visible) {
            super.onVisibilityChanged(visible);
            if (visible) {
                registerSensors();
            } else {
                unregisterSensors();
            }
        }

        private void registerSensors() {
            if (!sensorsRegistered && sensorManager != null && rotationSensor != null) {
                sensorManager.registerListener(this, rotationSensor, SensorManager.SENSOR_DELAY_GAME);
                sensorsRegistered = true;
            }
        }

        private void unregisterSensors() {
            if (sensorsRegistered && sensorManager != null) {
                sensorManager.unregisterListener(this);
                sensorsRegistered = false;
            }
        }

        @Override
        public void onSensorChanged(SensorEvent event) {
            if (event.sensor.getType() == Sensor.TYPE_GAME_ROTATION_VECTOR) {
                float[] values = event.values;
                targetX = Math.max(-1f, Math.min(1f, values[0] * 2f));
                targetY = Math.max(-1f, Math.min(1f, values[1] * 2f));
            } else if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
                targetX = Math.max(-1f, Math.min(1f, event.values[0] / 9.8f));
                targetY = Math.max(-1f, Math.min(1f, event.values[1] / 9.8f));
            }
        }

        @Override
        public void onAccuracyChanged(Sensor sensor, int accuracy) {
        }

        @Override
        public void onSurfaceDestroyed(SurfaceHolder holder) {
            unregisterSensors();
            super.onSurfaceDestroyed(holder);
        }

        @Override
        public void onDestroy() {
            unregisterSensors();
            super.onDestroy();
        }

        @Override
        public void onOffsetsChanged(float xOffset, float yOffset, float xStep, float yStep, int xPixels, int yPixels) {
        }

        @SuppressLint("CanvasRecycle")
        @Override
        public void onCommand(String action, int x, int y, int z, Bundle params, boolean result) {
        }

        public void drawFrame() {
            SurfaceHolder holder = getSurfaceHolder();
            Canvas canvas = null;
            try {
                canvas = holder.lockCanvas();
                if (canvas == null) return;

                currentX += (targetX - currentX) * LERP_SPEED;
                currentY += (targetY - currentY) * LERP_SPEED;

                float offsetX = currentX * PARALLAX_SCALE;
                float offsetY = currentY * PARALLAX_SCALE;

                canvas.drawColor(Color.parseColor("#0a0a0f"));

                if (bgBitmap != null) {
                    float bgScale = Math.max(
                            (float) screenWidth / bgBitmap.getWidth(),
                            (float) screenHeight / bgBitmap.getHeight()
                    );
                    float dw = bgBitmap.getWidth() * bgScale;
                    float dh = bgBitmap.getHeight() * bgScale;
                    float dx = (screenWidth - dw) / 2f + offsetX * 0.5f;
                    float dy = (screenHeight - dh) / 2f + offsetY * 0.5f;
                    RectF dest = new RectF(dx, dy, dx + dw, dy + dh);
                    canvas.drawBitmap(bgBitmap, null, dest, null);
                }

                if (subjectBitmap != null) {
                    float sScale = Math.min(
                            (float) screenWidth / subjectBitmap.getWidth(),
                            (float) screenHeight / subjectBitmap.getHeight()
                    ) * 0.85f;
                    float dw = subjectBitmap.getWidth() * sScale;
                    float dh = subjectBitmap.getHeight() * sScale;
                    float dx = (screenWidth - dw) / 2f - offsetX * 1.2f;
                    float dy = (screenHeight - dh) / 2f - offsetY * 1.2f;
                    RectF dest = new RectF(dx, dy, dx + dw, dy + dh);
                    canvas.drawBitmap(subjectBitmap, null, dest, null);
                }

                Paint glowPaint = new Paint();
                glowPaint.setColor(Color.parseColor("#00ff88"));
                glowPaint.setAlpha(8);
                glowPaint.setMaskFilter(new MaskFilter(40f, BlurMaskFilter.Blur.NORMAL));
                canvas.drawCircle(
                        screenWidth / 2f + offsetX * 3,
                        screenHeight / 2f + offsetY * 3,
                        screenWidth * 0.25f,
                        glowPaint
                );
            } catch (Exception e) {
                Log.e(TAG, "Draw error", e);
            } finally {
                if (canvas != null) {
                    try {
                        holder.unlockCanvasAndPost(canvas);
                    } catch (Exception ignored) {
                    }
                }
            }
        }

        private final Runnable drawRunner = this::drawFrame;

        public void startDrawing() {
            removeCallbacks(drawRunner);
            post(drawRunner);
            postDelayed(drawRunner, 50);
        }

        public void stopDrawing() {
            removeCallbacks(drawRunner);
        }
    }

    private void post(Runnable r) {
    }

    private void removeCallbacks(Runnable r) {
    }

    private void postDelayed(Runnable r, long delayMillis) {
    }
}
