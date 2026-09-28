# Build system for the B# C runtime (libbsharp).
#
#   make            build libbsharp.a
#   make catalog    regenerate the error catalog from error_catalog.py
#   make check      drift-check the generated catalog + compile clean
#   make clean      remove build artifacts
#
# The library is linked into every `bsharp build` executable and is
# also exercised by Tests/test_runtime_c.py (which compiles small
# drivers against it and diffs their behavior against the interpreter).

CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror
CPPFLAGS ?= -IB_Sharp/Compiler/Runtime -IB_Sharp/Compiler/CodeInstances

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
RUNTIME_DIR := Runtime
CODE_DIR := CodeInstances
BUILD_DIR := build

LIB := $(BUILD_DIR)/libbsharp.a

SRCS := \
	$(RUNTIME_DIR)/bsharp_errors.c \
	$(RUNTIME_DIR)/bsharp_catalog_gen.c \
	$(RUNTIME_DIR)/bsharp_number.c \
	$(CODE_DIR)/BSharpObject.c

OBJS := $(patsubst %.c,$(BUILD_DIR)/%.o,$(SRCS))

.PHONY: all lib catalog check clean

all: lib

lib: $(LIB)

$(LIB): $(OBJS)
	ar rcs $@ $^

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@

catalog:
	python3 $(ROOT)/tools/gen_error_catalog.py

check: catalog-check
	@$(MAKE) --no-print-directory lib

catalog-check:
	python3 $(ROOT)/tools/gen_error_catalog.py --check

clean:
	rm -rf $(BUILD_DIR)
