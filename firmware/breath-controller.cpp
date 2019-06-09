/* Main program */

#include <stdint.h>
#include <stddef.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/eeprom.h>
#include <lufa/Drivers/USB/USB.h>
#include "descriptors.h"
#include "shared.hpp"
#include "common.hpp"
#include "delay.hpp"

/* Peripherals are configured for 8 MHz system clock */
static_assert(F_CPU == 8e6, "");

constexpr uint8_t pressure_adc_channel = 0;
constexpr uint8_t sysex_id = 0x7d;      /* SysEx Manufacturer ID */

enum class MidiMessage: uint8_t {
        control_change,
        channel_pressure,
        pitch_bend_up,
        pitch_bend_down,
};

enum class SysExCommand: uint8_t {
        set_midi_channel,
        set_midi_message,
        set_control_number,
        set_input_gain,
        set_curve,
        save_to_eeprom,
};

struct Settings {
        uint8_t midi_channel;           /* MIDI channel (1..16) */
        MidiMessage midi_message;       /* MIDI message */
        uint8_t control_number;         /* Control number (0..127) */
        uint8_t input_gain;             /* Input gain multiplied by 10 (10..40) */
        uint8_t curve[128];             /* Pressure (0..127) -> MIDI value (0..127) */
} __attribute__((packed));              /* Pack because we'll put it in EEPROM */

static Settings settings;

/* EEPROM */
Settings ee_settings EEMEM = {
        .midi_channel = 1,
        .midi_message = MidiMessage::control_change,
        .control_number = 2,
        .input_gain = 10,
        .curve = {
                  0,   1,   2,   3,   4,   5,   6,   7,
                  8,   9,  10,  11,  12,  13,  14,  15,
                 16,  17,  18,  19,  20,  21,  22,  23,
                 24,  25,  26,  27,  28,  29,  30,  31,
                 32,  33,  34,  35,  36,  37,  38,  39,
                 40,  41,  42,  43,  44,  45,  46,  47,
                 48,  49,  50,  51,  52,  53,  54,  55,
                 56,  57,  58,  59,  60,  61,  62,  63,
                 64,  65,  66,  67,  68,  69,  70,  71,
                 72,  73,  74,  75,  76,  77,  78,  79,
                 80,  81,  82,  83,  84,  85,  86,  87,
                 88,  89,  90,  91,  92,  93,  94,  95,
                 96,  97,  98,  99, 100, 101, 102, 103,
                104, 105, 106, 107, 108, 109, 110, 111,
                112, 113, 114, 115, 116, 117, 118, 119,
                120, 121, 122, 123, 124, 125, 126, 127,
        },
};

/* Shared variables (changed in interrupts) */
static uint8_t s_pressure;              /* Current pressure from the sensor (0..255) */
static bool s_pressure_updated;         /* Sets to 1 when 's_pressure' is updated */

/* 4 kHz general-purpose interrupt */
ISR(TIMER1_COMPA_vect)
{
        /* Measure the pressure */
        {
                static uint8_t counter = 0;
                static uint16_t accumulator = 0;

                accumulator += ADCH;
                if (++counter > 31) {   /* Accumulate within 8 ms (125 Hz) */
                        s_pressure = accumulator/32;
                        s_pressure_updated = 1;
                        accumulator = 0;
                        counter = 0;
                }

                /* Start next conversiona (AVCC reference, 125 kHz clock) */
                static_assert(pressure_adc_channel <= 7, "");
                ADMUX = 1<<REFS0 | 1<<ADLAR | pressure_adc_channel;
                ADCSRA = 1<<ADEN | 1<<ADSC | 1<<ADPS2 | 1<<ADPS1;
        }
}

/* Process raw incoming SysEx message "F0 ... F7" */
static void process_sysex(const uint8_t *message)
{
        if (message[0] != 0xf0 || message[1] != sysex_id)
                return;

        switch (static_cast<SysExCommand>(message[2])) {
        case SysExCommand::set_midi_channel:
                settings.midi_channel = clamp<uint8_t>(message[3], 1, 16);
                break;
        case SysExCommand::set_midi_message:
                settings.midi_message = static_cast<MidiMessage>(message[3]);
                break;
        case SysExCommand::set_control_number:
                settings.control_number = min<uint8_t>(message[3], 127);
                break;
        case SysExCommand::set_input_gain:
                settings.input_gain = clamp<uint8_t>(message[3], 10, 40);
                break;
        case SysExCommand::set_curve:
                for (uint8_t i = 0; i < 128 && message[i+3] != 0xf7; i++)
                        settings.curve[i] = min<uint8_t>(message[i+3], 127);
                break;
        case SysExCommand::save_to_eeprom:
                eeprom_update_block(&settings, &ee_settings, sizeof(Settings));
                break;
        default:
                break;
        }
}

/* Receive SysEx messages from the host */
static void midi_receive()
{
        MIDI_EventPacket_t event;
        constexpr size_t sysex_buffer_size = 256;
        static uint8_t buffer[sysex_buffer_size], pos = 0;

        if (USB_DeviceState != DEVICE_STATE_Configured)
                return;

        Endpoint_SelectEndpoint(MIDI_STREAM_OUT_EPADDR);

        if (!Endpoint_IsOUTReceived())
                return;

        Endpoint_Read_Stream_LE(&event, sizeof(event), NULL);

        switch (event.Event) {
        case MIDI_EVENT(0, MIDI_COMMAND_SYSEX_START_3BYTE):
        case MIDI_EVENT(0, MIDI_COMMAND_SYSEX_END_3BYTE):
                if (sysex_buffer_size - pos >= 3) {
                        buffer[pos++] = event.Data1;
                        buffer[pos++] = event.Data2;
                        buffer[pos++] = event.Data3;
                }
                break;
        case MIDI_EVENT(0, MIDI_COMMAND_SYSEX_END_2BYTE):
                if (sysex_buffer_size - pos >= 2) {
                        buffer[pos++] = event.Data1;
                        buffer[pos++] = event.Data2;
                }
                break;
        case MIDI_EVENT(0, MIDI_COMMAND_SYSEX_END_1BYTE):
                if (sysex_buffer_size - pos >= 1)
                        buffer[pos++] = event.Data1;
                break;
        default:
                break;
        }

        if (buffer[pos-1] == 0xf7) {
                process_sysex(buffer);
                pos = 0;
        }

        if (Endpoint_BytesInEndpoint() == 0)
                Endpoint_ClearOUT();
}

/* Send MIDI data to the host */
static void midi_send(uint8_t value)
{
        static uint8_t previous_value;
        MIDI_EventPacket_t event;

        if (value == previous_value)
                return;

        if (USB_DeviceState != DEVICE_STATE_Configured)
                return;

        Endpoint_SelectEndpoint(MIDI_STREAM_IN_EPADDR);

        if (!Endpoint_IsINReady())
                return;

        switch (settings.midi_message) {
        case MidiMessage::control_change:
                event.Event = MIDI_EVENT(0, MIDI_COMMAND_CONTROL_CHANGE);
                event.Data1 = MIDI_COMMAND_CONTROL_CHANGE | MIDI_CHANNEL(settings.midi_channel);
                event.Data2 = settings.control_number;
                event.Data3 = value;
                break;
        case MidiMessage::channel_pressure:
                event.Event = MIDI_EVENT(0, MIDI_COMMAND_CHANNEL_PRESSURE);
                event.Data1 = MIDI_COMMAND_CHANNEL_PRESSURE | MIDI_CHANNEL(settings.midi_channel);
                event.Data2 = value;
                event.Data3 = 0;
                break;
        case MidiMessage::pitch_bend_up:
                event.Event = MIDI_EVENT(0, MIDI_COMMAND_PITCH_WHEEL_CHANGE);
                event.Data1 = MIDI_COMMAND_PITCH_WHEEL_CHANGE | MIDI_CHANNEL(settings.midi_channel);
                event.Data2 = ((value & 63) | (value << 6)) & 127;
                event.Data3 = (128 + value) >> 1;
                break;
        case MidiMessage::pitch_bend_down:
                event.Event = MIDI_EVENT(0, MIDI_COMMAND_PITCH_WHEEL_CHANGE);
                event.Data1 = MIDI_COMMAND_PITCH_WHEEL_CHANGE | MIDI_CHANNEL(settings.midi_channel);
                event.Data2 = ((-value & 63) | (-value << 6)) & 127;
                event.Data3 = (128 - value) >> 1;
                break;
        default:
                return;
        }

        Endpoint_Write_Stream_LE(&event, sizeof(event), NULL);
        Endpoint_ClearIN();

        previous_value = value;
}

/* Event handler for the USB_Connect event */
void EVENT_USB_Device_Connect(void)
{
}

/* Event handler for the USB_Disconnect event */
void EVENT_USB_Device_Disconnect(void)
{
}

/* Event handler for the USB_ConfigurationChanged event */
void EVENT_USB_Device_ConfigurationChanged(void)
{
        bool success = true;

        /* Setup MIDI Data Endpoints */
        success &= Endpoint_ConfigureEndpoint(MIDI_STREAM_IN_EPADDR, EP_TYPE_BULK, MIDI_STREAM_EPSIZE, 1);
        success &= Endpoint_ConfigureEndpoint(MIDI_STREAM_OUT_EPADDR, EP_TYPE_BULK, MIDI_STREAM_EPSIZE, 1);

        /* If success then LED's brightness is PWM controlled */
        set_bits(TCCR0A, 1<<COM0A1, success);
}

static uint8_t zero_adjust(uint8_t value, uint8_t zero)
{
        return (value > zero) ? (value-zero)*255u/(255u-zero) : 0;
}

static uint8_t input_gain(uint8_t value, uint8_t gain)
{
        return min(static_cast<uint16_t>(value)*gain/10u, 255u);
}

int main()
{
        /* Disable the system clock prescaler */
        CLKPR = 1<<CLKPCE;
        CLKPR = 0;

        /* Enable Watchdog Timer (1 s) */
        WDTCSR = 1<<WDCE | 1<<WDE;
        WDTCSR = 1<<WDE | 1<<WDP2 | 1<<WDP1;

        /* GPIO init */
        DDRB  = 0b10000000;
        PORTB = 0b11111111;
        DDRC  = 0b00000000;
        PORTC = 0b11111111;
        DDRD  = 0b00000000;
        PORTD = 0b11111111;
        DDRE  = 0b00000000;
        PORTE = 0b11111111;
        DDRF  = 0b00000000;
        PORTF = 0b11111110;

        /* T/C0: PWM for the LED */
        TCCR0A = 1<<WGM01 | 1<<WGM00;
        TCCR0B = 1<<CS01;
        OCR0A = 0;

        /* T/C1: 4 kHz general-purpose interrupt */
        TCCR1A = 0;
        TCCR1B = 1<<WGM12 | 1<<CS11;
        OCR1A = 249;
        TIMSK1 = 1<<OCIE1A;

        /* Disable unused peripherals */
        ACSR |= 1<<ACD;
        PRR0 = 1<<PRTWI | 1<<PRSPI;
        PRR1 = 1<<4 /* PRTIM4 */ | 1<<PRTIM3 | 1<<PRUSART1;

        /* Load settings from EEPROM */
        eeprom_read_block(&settings, &ee_settings, sizeof(Settings));

        USB_Init();

        sei();

        /* Skip transients */
        delay_ms(500);

        /* Auto-zero */
        uint8_t pressure_zero = atomic_read(s_pressure);

        while (true)
        {
                asm volatile ("wdr" ::: "memory");

                if (atomic_read(s_pressure_updated)) {
                        uint8_t v = atomic_read(s_pressure);
                        v = zero_adjust(v, pressure_zero);
                        v = input_gain(v, settings.input_gain);
                        v = settings.curve[v/2];
                        OCR0A = v*2;
                        midi_send(v);
                        atomic_write(s_pressure_updated, 0);
                }

                midi_receive();
                USB_USBTask();
        }

        return 0;
}
