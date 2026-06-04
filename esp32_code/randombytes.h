#pragma once
#include "esp_random.h"

static inline void randombytes(unsigned char* buf, unsigned long long n) {
  esp_fill_random(buf, (size_t)n);
}