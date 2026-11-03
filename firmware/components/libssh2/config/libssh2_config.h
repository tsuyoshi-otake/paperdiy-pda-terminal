/* libssh2 configuration for ESP-IDF (lwIP sockets, newlib). */
#ifndef LIBSSH2_CONFIG_H
#define LIBSSH2_CONFIG_H

#define HAVE_UNISTD_H
#define HAVE_INTTYPES_H
#define HAVE_SYS_SELECT_H
#define HAVE_SYS_SOCKET_H
#define HAVE_SYS_IOCTL_H
#define HAVE_SYS_TIME_H
#define HAVE_ARPA_INET_H
#define HAVE_NETINET_IN_H

#define HAVE_GETTIMEOFDAY
#define HAVE_STRTOLL
#define HAVE_SNPRINTF
#define HAVE_SELECT
#define HAVE_O_NONBLOCK

#endif /* LIBSSH2_CONFIG_H */
