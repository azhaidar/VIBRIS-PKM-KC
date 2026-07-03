// DriverSuhu.cpp
#include "DriverSuhu.h"
#include "config.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include "MultiSensorFeatureMerger.h"
// Setup komunikasi OneWire menggunakan pin yang dikunci di config.h
static OneWire oneWireInstance(PIN_DS18B20_DATA);
static DallasTemperature temperatureSensors(&oneWireInstance);
/**
 * @brief Eksekusi Riil Task Pembacaan Sensor Suhu DS18H
 * @param pvParameters Pointer yang dilempar dari xTaskCreatePinnedToCore
 */
void TaskDriverSuhu(void *pvParameters) {
    // Casting pointer parameter ke objek memori bersama
    (void)pvParameters;
    // Inisialisasi IC Sensor
    temperatureSensors.begin();
    temperatureSensors.setResolution(12); // Resolusi tertinggi (12-bit), waktu konversi ~750ms
    temperatureSensors.setWaitForConversion(false); // Mode Asinkron (Non-blocking)
    // Inisialisasi variabel internal untuk filter data
    float lastValidTemperature = SUHU_DEFAULT_VALID;

    for (;;) {
        // Kirim perintah ke hardware untuk memulai konversi suhu
        temperatureSensors.requestTemperatures();
        
        // Block-state: Mengistirahatkan CPU selama proses konversi kimia sensor berjalan (750ms)
        vTaskDelay(pdMS_TO_TICKS(TICK_DELAY_SUHU)); 
        
        // Ambil data dari sensor indeks ke-0
        float rawTemperature = temperatureSensors.getTempCByIndex(0);
        
        // FILTER 1: Validasi Fisik Kerusakan Hardware / Jalur Putus (Disconnection Check)
        // Sensor Dallas akan mengembalikan -127.00 jika putus atau 85.00 jika power-on reset error
        if (rawTemperature != -127.00 && rawTemperature != 85.00) {
            
            // FILTER 2: Slew Rate Limiter (Deteksi Anomali Lonjakan Drastis akibat Noise)
            if (abs(rawTemperature - lastValidTemperature) <= SUHU_MAX_DELTA) {
                lastValidTemperature = rawTemperature;
            } else {
                // Jika lonjakan melewati batas deviasi makro, batasi kenaikan/penurunannya
                lastValidTemperature += (rawTemperature > lastValidTemperature) ? SUHU_MAX_DELTA : -SUHU_MAX_DELTA;
            }
            // Tulis data terfilter ke memori bersama yang diakses antar-core
            updateTemperatureFeature(lastValidTemperature);
        } else {
            // Jika masuk ke mode ini, sensor terdeteksi rusak atau kabel terlepas
            Serial.println(F("[ERROR] Sensor DS18B20 Terputus / Malfungsi!"));
        }   
    }
}