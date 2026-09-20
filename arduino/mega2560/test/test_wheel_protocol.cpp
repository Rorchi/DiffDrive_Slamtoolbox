#include <assert.h>
#include "../src/wheel_protocol.h"

int send(WheelProtocol &parser, const char *text, int &left, int &right) {
  int result = 0;
  while (*text) result = parser.feed(*text++, left, right);
  return result;
}

int main() {
  WheelProtocol parser;
  int left = 0, right = 0;
  assert(send(parser, "V1 -30 30\n", left, right) == 1);
  assert(left == -30 && right == 30);
  assert(send(parser, "V1 70 ", left, right) == 0);
  assert(send(parser, "130\n", left, right) == 1);
  assert(left == 70 && right == 130);
  const char *invalid[] = {"V1 151 0\n", "V1 nan 0\n", "V1 1\n",
    "V1 1 2 extra\n", "V2 1 2\n", "V1 99999999999 0\n",
    "V1 1.5 2\n", "V1 1 2\r\n", "\n"};
  for (const char *text : invalid) {
    assert(send(parser, text, left, right) == -1);
    assert(left == 0 && right == 0);
  }
  send(parser, "V1 100 ", left, right);
  assert(send(parser, "S", left, right) == -1);
  assert(left == 0 && right == 0);
  assert(send(parser, "V1 0 0\n", left, right) == 1);
  assert(send(parser, "0123456789012345678901234567890123456789\n",
              left, right) == -1);
  assert(send(parser, "V1 150 -150\n", left, right) == 1);
  assert(left == 150 && right == -150);
}
