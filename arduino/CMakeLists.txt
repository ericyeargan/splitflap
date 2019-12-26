set(CMAKE_TOOLCHAIN_FILE Arduino-CMake-NG/cmake/Arduino-Toolchain.cmake)

cmake_minimum_required(VERSION 3.15)

project(splitflap C CXX ASM)

add_subdirectory(splitflap)
