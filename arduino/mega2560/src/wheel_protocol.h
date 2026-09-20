#pragma once

#include <stdlib.h>
#include <string.h>

// V1 <left mm/s> <right mm/s>\n, range +/-150 mm/s.
// Only complete frames refresh the watchdog. S is an immediate stop.
struct WheelProtocol {
  char buffer[32] = {};
  unsigned char size = 0;
  bool discard = false;

  static bool number(char *&p, int &value) {
    char *start = p;
    if (*p == '-' || *p == '+') ++p;
    char *digits = p;
    long result = 0;
    while (*p >= '0' && *p <= '9') {
      result = result * 10 + (*p++ - '0');
      if (result > 150) return false;
    }
    if (p == digits) return false;
    value = (*start == '-') ? -result : result;
    return true;
  }

  // 0: incomplete; 1: valid command; -1: stop/invalid input.
  int feed(char c, int &left, int &right) {
    if (c == 'S') {
      size = 0;
      discard = false;
      left = right = 0;
      return -1;
    }
    if (c == '\n') {
      buffer[size] = '\0';
      bool valid = !discard && strncmp(buffer, "V1 ", 3) == 0;
      char *p = buffer + 3;
      if (valid) valid = number(p, left);
      if (valid) valid = *p++ == ' ';
      if (valid) valid = number(p, right);
      if (valid) valid = *p == '\0';
      size = 0;
      discard = false;
      if (!valid) left = right = 0;
      return valid ? 1 : -1;
    }
    if (discard) return 0;
    if (size >= sizeof(buffer) - 1 || c < ' ' || c > '~') {
      discard = true;
      left = right = 0;
      return -1;
    }
    buffer[size++] = c;
    return 0;
  }
};
