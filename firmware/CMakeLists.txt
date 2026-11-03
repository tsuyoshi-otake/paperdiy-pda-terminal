# PaperDIY Terminal — BLE keyboard + Wi-Fi + SSH terminal for M5Stack PaperDIY
cmake_minimum_required(VERSION 3.16)

# Third-party components fetched by fetch_deps.sh (M5GFX, M5Unified, libssh2 sources)
set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/deps/M5GFX" "${CMAKE_CURRENT_LIST_DIR}/deps/M5Unified")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
idf_build_set_property(MINIMAL_BUILD ON)
project(paperdiy_term)
