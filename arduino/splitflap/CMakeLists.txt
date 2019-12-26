option(ARDUINO_PORT "the Arduino's serial device path")

get_board_id(board_id uno)

# Configure up the NoePixel lib target
set(target_name Adafruit_NeoPixel)

set (neopixel_lib_path "${CMAKE_SOURCE_DIR}/Adafruit_NeoPixel")

add_arduino_library(${target_name} ${board_id} "${neopixel_lib_path}/Adafruit_NeoPixel.cpp")
target_include_directories(${target_name} PUBLIC ${neopixel_lib_path})

# Configure the splitflap firmware target
set(target_name splitflap)

add_arduino_executable(${target_name} ${board_id} splitflap.cpp)

link_platform_library(${target_name} SPI ${board_id})
link_arduino_library(${target_name} Adafruit_NeoPixel ${board_id})

if (ARDUINO_PORT)
	message(STATUS "Arduino serial device: ${ARDUINO_PORT}")

	set_upload_target_flags(${target_name} ${board_id} ${ARDUINO_PORT} upload_args)

	add_custom_target(upload ALL
			COMMAND ${ARDUINO_CMAKE_AVRDUDE_PROGRAM} ${upload_args}
			COMMENT "Uploading ${target_name} target"
			DEPENDS ${target_name})

	find_package(PythonInterp 3 REQUIRED)

	add_custom_target(monitor
			COMMAND ${PYTHON_EXECUTABLE} -m serial.tools.miniterm -e ${ARDUINO_PORT} 38400)
endif()
