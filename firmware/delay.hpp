/*
 * Blocking delays in active mode
 *
 * Provides delay_{us,ms,s,cycles} functions. The value of delay must be a
 * compile-time constant expression.
 */

#ifndef DELAY_HPP_
#define DELAY_HPP_

#ifndef F_CPU
#  error "Define F_CPU to the CPU frequency in Hz"
#endif

#ifndef __OPTIMIZE__
#  error "Compiler optimization must be enabled"
#endif

/* Define delay_cycles for a specific target */
#if defined(__AVR_ARCH__)
#  include <avr/builtins.h>
#  define delay_cycles __builtin_avr_delay_cycles
#elif defined(__MSP430__)
#  define delay_cycles __delay_cycles
#else
#  error "Only AVR and MSP430 are supported"
#endif

#include <math.h>  /* For compile-time calculations */

enum class DelayRound { closest, down, up };

inline __attribute__((always_inline))
void delay_us(double delay, DelayRound round = DelayRound::up)
{
        const double cycles = (delay > 0) ? (delay*F_CPU/1e6) : 0;
        const double cycles_rounded =
                (round == DelayRound::closest) ? floor(cycles + 0.5) :
                (round == DelayRound::down) ? floor(cycles) : ceil(cycles);

        delay_cycles(static_cast<unsigned long>(cycles_rounded));
}

inline __attribute__((always_inline))
void delay_ms(double delay, DelayRound round = DelayRound::up)
{
        delay_us(delay*1e3, round);
}

inline __attribute__((always_inline))
void delay_s(double delay, DelayRound round = DelayRound::up)
{
        delay_us(delay*1e6, round);
}

#endif
