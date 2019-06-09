# This Makefile uses the build system included in LUFA
# http://www.lufa-lib.org
#
# Run "make list_targets" to list available targets

MCU          = atmega16u4
ARCH         = AVR8
F_CPU        = 8000000
F_USB        = 8000000
OPTIMIZATION = s
TARGET       = breath-controller
SRC          = breath-controller.cpp descriptors.c $(LUFA_SRC_USB)
LUFA_PATH    = lufa
CC_FLAGS     = -DUSE_LUFA_CONFIG_HEADER
LD_FLAGS     =
CPP_STANDARD = c++14

CPP_FLAGS += -Wextra -Woverloaded-virtual -Wcast-align -Wundef
CPP_FLAGS += -Wlogical-op -Wredundant-decls -Wshadow -Wsuggest-override
CPP_FLAGS += -fno-threadsafe-statics -fno-exceptions 

AVRDUDE_PROGRAMMER = usbasp

all:

# Include LUFA-specific DMBS extension modules
DMBS_LUFA_PATH ?= $(LUFA_PATH)/Build/LUFA
include $(DMBS_LUFA_PATH)/lufa-sources.mk
include $(DMBS_LUFA_PATH)/lufa-gcc.mk

# Include common DMBS build system modules
DMBS_PATH ?= $(LUFA_PATH)/Build/DMBS/DMBS
include $(DMBS_PATH)/core.mk
include $(DMBS_PATH)/cppcheck.mk
include $(DMBS_PATH)/dfu.mk
include $(DMBS_PATH)/gcc.mk
include $(DMBS_PATH)/avrdude.mk
