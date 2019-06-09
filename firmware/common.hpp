#ifndef COMMON_HPP_
#define COMMON_HPP_

#include <stddef.h>

template<typename T, size_t n>
constexpr size_t size(const T (&)[n]) {
        return n;
}

template<typename T>
inline void set_bits(T &x, decltype(T{}) mask, bool bit) {
        bit ? (x |= mask) : (x &= ~mask);
}

template<typename T>
constexpr T abs(T x) {
        return (x < 0) ? -x : x;
}

template<typename T>
constexpr T min(T x, T y) {
        return (x < y) ? x : y;
}

template<typename T>
constexpr T max(T x, T y) {
        return (x > y) ? x : y;
}

template<typename T>
constexpr T clamp(T x, T low, T high) {
        return (x < low) ? low :
                (x > high) ? high : x;
}

constexpr uint16_t concat16(uint8_t a, uint8_t b) {
        return static_cast<uint16_t>(a) << 8 | b;
}

constexpr uint32_t concat32(uint16_t a, uint16_t b) {
        return static_cast<uint32_t>(a) << 16 | b;
}

constexpr uint32_t concat32(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {
        return static_cast<uint32_t>(a) << 24 |
                static_cast<uint32_t>(b) << 16 |
                static_cast<uint16_t>(c) << 8 | d;
}

#endif
