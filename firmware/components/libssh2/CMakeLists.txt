# libssh2 (BSD-3-Clause) built for ESP-IDF with the mbedTLS crypto backend.
# Sources live in deps/libssh2-src (see fetch_deps.sh).
set(LIBSSH2_DIR "${CMAKE_CURRENT_LIST_DIR}/../../deps/libssh2-src")

set(LIBSSH2_SRCS
    agent.c bcrypt_pbkdf.c blowfish.c chacha.c channel.c cipher-chachapoly.c
    comp.c crypt.c crypto.c global.c hostkey.c keepalive.c kex.c knownhost.c
    mac.c misc.c packet.c pem.c poly1305.c publickey.c scp.c session.c sftp.c
    transport.c userauth.c userauth_kbd_packet.c version.c)
list(TRANSFORM LIBSSH2_SRCS PREPEND "${LIBSSH2_DIR}/src/")

idf_component_register(SRCS ${LIBSSH2_SRCS}
                       INCLUDE_DIRS "${LIBSSH2_DIR}/include"
                       PRIV_INCLUDE_DIRS "config" "${LIBSSH2_DIR}/src"
                       REQUIRES mbedtls lwip)

target_compile_definitions(${COMPONENT_LIB} PRIVATE
    HAVE_CONFIG_H LIBSSH2_MBEDTLS LIBSSH2_LIBRARY)
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wno-unused-function -Wno-unused-variable -Wno-unused-but-set-variable
    -Wno-format -Wno-char-subscripts -Wno-maybe-uninitialized -Wno-sign-compare)
