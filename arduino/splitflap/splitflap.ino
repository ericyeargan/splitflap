/*
   Copyright 2015-2016 Scott Bezek and the splitflap contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

/***** CONFIGURATION *****/

#define NUM_MODULES (12) //ON ESP32 you can control much more modules, but need to adapt SPI_IO_CONFIG accordingly
#define SENSOR_TEST false
#define SPI_IO true
#define BLUETOOTH true

#include <stdint.h>

// This should match the order of flaps on the spool:
const uint8_t flaps[] = {
  ' ',
  'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
  'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
  '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
  '.',
  ',',
  '\'',
};

/*************************/


#include "splitflap_module.h"

#if SPI_IO
#include "spi_io_config.h"
#else
#include "basic_io_config.h"
#endif

#if NEOPIXEL_DEBUGGING_ENABLED
#include <Adafruit_NeoPixel.h>
#endif

#include "bell.h"


#define RECV_BUFFER_SIZE (NUM_MODULES + 1)
int recv_buffer[RECV_BUFFER_SIZE];
uint8_t recv_count = 0;

#if NEOPIXEL_DEBUGGING_ENABLED
auto pixelType = NEO_GRB + NEO_KHZ800; // NOLINT(hicpp-signed-bitwise)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_MODULES, NEOPIXEL_PIN, pixelType);
uint32_t color_green = Adafruit_NeoPixel::Color(0, 30, 0);
uint32_t color_red = Adafruit_NeoPixel::Color(100, 0, 0);
uint32_t color_purple = Adafruit_NeoPixel::Color(15, 0, 15);
uint32_t color_orange = Adafruit_NeoPixel::Color(30, 7, 0);
#endif

#ifdef __AVR__
#define FAVR(x) F(x)
#else
#define FAVR(x) x
#endif

#if defined(ESP32) && BLUETOOTH
#include "BluetoothSerial.h"
#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please run `make menuconfig` to and enable it
#endif

BluetoothSerial SerialBT;
#endif

#define BELL_OUTPUT_PIN 10

Bell bell(BELL_OUTPUT_PIN);

void dump_status();

void setup() {
  // Setting the serial rate immediately on boot prevents the esp-link
  // programmer from syncing up correctly at the bootloader rate (115200) so
  // add a short delay.  Ideally, we'd just run at the same rate but the uno
  // seems to occasionally drop characters at higher rates.
  delay(250);
  Serial.begin(38400);

  motor_sensor_setup();
  motor_sensor_io();

  Serial.print(FAVR("{\"type\":\"init\", \"num_modules\":"));
  Serial.print(NUM_MODULES);
  Serial.print(FAVR("}\n"));

#if NEOPIXEL_DEBUGGING_ENABLED
  strip.setBrightness(64);
  strip.begin();
  strip.show();

  // Pulse neopixels for fun
  uint8_t vals[] = {0, 1, 3, 10, 16, 20, 24, 28, 28, 24, 20, 16, 10, 3, 1, 0};
  for (int16_t i = 0; i < 400; i++) {
    for (int j = 0; j < NUM_MODULES; j++) {
      int8_t index = i / 8 - j;
      if (index < 0) {
        index = 0;
      } else if (index > 15) {
        index = index % 16;
      }
      strip.setPixelColor(j, vals[index] * 2, vals[index] * 2, 0);
    }
    strip.show();
    delay(3);
  }
#else
  pinMode(LED_BUILTIN, OUTPUT);

  // Pulse the builtin LED - not as fun but indicates that we're running
  for (int i = 0; i < 11; i++) {
    digitalWrite(LED_BUILTIN, i % 2 ? HIGH : LOW);
    delay(100);
  }
#endif

  bell.Setup();

  for (uint8_t i = 0; i < NUM_MODULES; i++) {
    recv_buffer[i] = 0;
    modules[i].Init();
#if !SENSOR_TEST
    modules[i].GoHome();
#endif
  }

#if defined(ESP32) && BLUETOOTH
  SerialBT.begin("SplitFlap1"); //Bluetooth device name
  Serial.println("The device started, now you can pair it with bluetooth!");
#endif
}


inline int8_t FindFlapIndex(uint8_t character) {
    for (int8_t i = 0; i < NUM_FLAPS; i++) {
        if (character == flaps[i]) {
          return i;
        }
    }
    return -1;
}

bool was_stopped = false;
bool pending_no_op = false;
bool bell_on_stop = false;

inline void run_iteration() {
    boolean all_idle = true;
    boolean all_stopped = true;
    boolean any_bad_timing = false;
    for (uint8_t i = 0; i < NUM_MODULES; i++) {
      any_bad_timing |= modules[i].Update();
      bool is_idle = modules[i].state == PANIC
#if HOME_CALIBRATION_ENABLED
        || modules[i].state == LOOK_FOR_HOME
        || modules[i].state == SENSOR_ERROR
#endif
        || (modules[i].state == NORMAL && modules[i].current_accel_step == 0);
      all_idle &= is_idle;
      all_stopped &= modules[i].current_accel_step == 0;
      if (i & 0b11u) motor_sensor_io();
    }
    motor_sensor_io();

    if (all_idle) {
#if NEOPIXEL_DEBUGGING_ENABLED
      for (int i = 0; i < NUM_MODULES; i++) {
        uint32_t color;
        switch (modules[i].state) {
          case NORMAL:
            color = color_green;
            break;
#if HOME_CALIBRATION_ENABLED
          case LOOK_FOR_HOME:
            color = color_purple;
            break;
          case SENSOR_ERROR:
            color = color_orange;
            break;
#endif
          case PANIC:
          default:
            color = color_red;
            break;
        }
        strip.setPixelColor(i, color);
      }
      strip.show();
#endif

      bell.Update();

      static const int OP_CODE_UPDATE_MASK = 0b00111100;
      static const int OP_CODE_FORCE_REFRESH_MASK = 0x01;
      static const int OP_CODE_BELL_MASK = 0x02;

      while (Serial.available() > 0) {
        int b = Serial.read();
        if (b == '\n') {
          if (recv_count > 0) {
            int const op_code = recv_buffer[0];
            switch (op_code) {
              case '@':
                for (uint8_t i = 0; i < NUM_MODULES; i++) { // NOLINT(modernize-loop-convert)
                  modules[i].ResetErrorCounters();
                  modules[i].GoHome();
                }
                break;
              case 'A':
                dump_status();
                break;
              default:
                if ((op_code & OP_CODE_UPDATE_MASK) == OP_CODE_UPDATE_MASK) {
                    SplitflapModule::FlapRefresh refresh = op_code & OP_CODE_FORCE_REFRESH_MASK 
                      ? SplitflapModule::FLAP_REFRESH_FORCE 
                      : SplitflapModule::FLAP_REFRESH_NONE;

                    bell_on_stop = op_code & OP_CODE_BELL_MASK;

                    Serial.print(FAVR("{\"type\":\"move_echo\", \"refresh\":"));
                    if (refresh == SplitflapModule::FLAP_REFRESH_FORCE) {
                    Serial.print(FAVR("\"force\""));
                    } else {
                      Serial.print(FAVR("\"none\""));
                    }

                    Serial.print(FAVR(", \"bell\":"));
                    if (bell_on_stop) {
                      Serial.print(FAVR("\"true\""));
                    } else {
                      Serial.print(FAVR("\"false\""));
                    }

                    Serial.print(FAVR(", \"dest\":\""));
                    for (uint8_t i = 1; i < recv_count; i++) {
                      int8_t index = FindFlapIndex(recv_buffer[i]);
                      if (index != -1) {
                        modules[i - 1].GoToFlapIndex(index, refresh);
                      }
                      Serial.write(recv_buffer[i]);
                    }
                    Serial.print(FAVR("\"}\n"));
                    Serial.flush();
                } else {
                  pending_no_op = true;
                }
              break;
            }
          }
          recv_count = 0;
        }
        else if (recv_count < RECV_BUFFER_SIZE) {
          recv_buffer[recv_count] = b;
          recv_count++;
        }
      }

#if defined(ESP32) && BLUETOOTH
      while (SerialBT.available() > 0) {
        int c = SerialBT.read();
        switch (c) {
          case '@':
            for (uint8_t i = 0; i < NUM_MODULES; i++) {
              modules[i].ResetErrorCounters();
              modules[i].GoHome();
            }
            break;
          case '#':
            pending_no_op = true;
            break;
          case '=':
            recv_count = 0;
            break;
          case '\n':
              Serial.print(FAVR("{\"type\":\"move_echo\", \"dest\":\""));
              for (uint8_t i = 0; i < recv_count; i++) {
                int8_t index = FindFlapIndex(recv_buffer[i]);
                if (index != -1) {
                  modules[i].GoToFlapIndex(index);
                }
                Serial.write(recv_buffer[i]);
              }
              Serial.print(FAVR("\"}\n"));
              Serial.flush();
              break;
          default:
            if (recv_count > NUM_MODULES - 1) {
              break;
            }
            recv_buffer[recv_count] = c;
            recv_count++;
            break;
        }
      }
#endif

      if (pending_no_op && all_stopped) {
        Serial.print(FAVR("{\"type\":\"no_op\"}\n"));
        Serial.flush();
        pending_no_op = false;
      }
  
      if (!was_stopped && all_stopped) {
        if (bell_on_stop) {
          bell.Ding();
        }
        dump_status();
      }

    }
    was_stopped = all_stopped;
}

void sensor_test_iteration() {
    motor_sensor_io();

#if NEOPIXEL_DEBUGGING_ENABLED
    for (uint8_t i = 0; i < NUM_MODULES; i++) {
      uint32_t color;
      if (!modules[i].GetHomeState()) {
        color = color_green;
      } else {
        color = color_purple;
      }

      // Make LEDs flash in sequence to indicate sensor test mode
      if ((millis() / 32) % NUM_MODULES == i) {
        color += 8u + (8u << 8u) + (8u << 16u);
      }
      strip.setPixelColor(i, color);
    }
    strip.show();
#else
    // We only have one LED - just show the first module's home state status
    if (NUM_MODULES > 0) {
      digitalWrite(LED_BUILTIN, !modules[0].GetHomeState() ? HIGH : LOW);
    }
#endif
}

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wmissing-noreturn"

void loop() {
  while (true) {
#if SENSOR_TEST
    sensor_test_iteration();
#else
    run_iteration();
#endif

    #ifdef ESP8266 || defined(ESP32)
    // Yield to avoid triggering Soft WDT
    yield();
    #endif
  }
}

#pragma clang diagnostic pop

void dump_status() {
  Serial.print(FAVR("{\"type\":\"status\", \"modules\":["));
  for (uint8_t i = 0; i < NUM_MODULES; i++) {
    Serial.print(FAVR("{\"state\":\""));
    switch (modules[i].state) {
      case NORMAL:
        Serial.print(FAVR("normal"));
        break;
#if HOME_CALIBRATION_ENABLED
      case LOOK_FOR_HOME:
        Serial.print(FAVR("look_for_home"));
        break;
      case SENSOR_ERROR:
        Serial.print(FAVR("sensor_error"));
        break;
#endif
      case PANIC:
        Serial.print(FAVR("panic"));
        break;
    }
    Serial.print(FAVR("\", \"flap\":\""));
    Serial.write(flaps[modules[i].GetCurrentFlapIndex()]);
    Serial.print(FAVR("\", \"count_missed_home\":"));
    Serial.print(modules[i].count_missed_home);
    Serial.print(FAVR(", \"count_unexpected_home\":"));
    Serial.print(modules[i].count_unexpected_home);
    Serial.print(FAVR("}"));
    if (i < NUM_MODULES - 1) {
      Serial.print(FAVR(", "));
    }
  }
  Serial.print(FAVR("]}\n"));
  Serial.flush();
}
