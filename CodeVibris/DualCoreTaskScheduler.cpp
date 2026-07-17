#include "DualCoreTaskScheduler.h"
#include "FFTProcessor.h"
#include "config.h"
#include "MultiSensorFeatureMerger.h"
#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

static QueueHandle_t vibrationQueue = NULL;
static volatile float latestRPM = 0.0f;
static volatile float latestSNR = 0.0f;

static float lastValidRPM = 0.0f;
#define RPM_MAX_DELTA_PER_CYCLE 300.0f
static float latestBandEnergies[4] = {0.0f, 0.0f, 0.0f, 0.0f};

QueueHandle_t Scheduler_GetVibrationQueue() {
    return vibrationQueue;
}
static float latestRmsX = 0.0f;
static float latestRmsZ = 0.0f;
static float latestRmsY = 0.0f;

static void TaskFFTProcessor(void *pvParameters) {
    static VibrationBuffer incomingBuffer;
    float rpmResult = 0.0f;
    float snrResult = 0.0f;
    float bandEnergies[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    SensorFeatures fftLocalFeatures;

    FFTProcessor_Init();

    for (;;) {
        if (xQueueReceive(vibrationQueue, &incomingBuffer, portMAX_DELAY) == pdTRUE) {
            float snrResult = 0.0f;
            FFTProcessor_Process(&incomingBuffer, &fftLocalFeatures, &rpmResult, bandEnergies, &snrResult);
            latestSNR = snrResult;
            if (rpmResult > 0.0f && lastValidRPM > 0.0f &&
                fabsf(rpmResult - lastValidRPM) > RPM_MAX_DELTA_PER_CYCLE) {
                rpmResult = lastValidRPM + (rpmResult > lastValidRPM ? RPM_MAX_DELTA_PER_CYCLE : -RPM_MAX_DELTA_PER_CYCLE);
            }
            if (rpmResult > 0.0f) lastValidRPM = rpmResult;
            latestRPM = rpmResult;
            latestSNR = snrResult;
            latestRmsX = incomingBuffer.rms_x_raw;   // 
            latestRmsZ = incomingBuffer.rms_z_raw;
            latestRmsY = incomingBuffer.rms_y_raw;   //
            for (int i = 0; i < 4; i++) latestBandEnergies[i] = bandEnergies[i];

            updateVibrationFeature(fftLocalFeatures.rms_getaran);

            Serial.printf("[FFT] RPM=%.1f |  Y_RMS=%.4f | X_RMS=%.4f | Z_RMS=%.4f | Unbalance=%.2f | Misalign=%.2f\n",
                          rpmResult, fftLocalFeatures.rms_getaran, latestRmsX, latestRmsZ, bandEnergies[0], bandEnergies[1]);
        }
    }
}
void Scheduler_GetLatestAxisRMS(float *xOut, float *yOut, float *zOut) {
    *xOut = latestRmsX;
    *yOut = latestRmsY;
    *zOut = latestRmsZ;
}
void Scheduler_InitTasks() {
    vibrationQueue = xQueueCreate(1, sizeof(VibrationBuffer));

    xTaskCreatePinnedToCore(
        TaskFFTProcessor, "Task_FFT", STACK_TASK_FFT, NULL,
        PRIO_TASK_FFT, NULL, CORE_SYSTEM_SLOW_IO
    );
}

float Scheduler_GetLatestRPM() {
    return latestRPM;
}
float Scheduler_GetLatestSNR() {
    return latestSNR;
}
void Scheduler_GetLatestBandEnergies(float *dest) {
    for (int i = 0; i < 4; i++) dest[i] = latestBandEnergies[i];
}
