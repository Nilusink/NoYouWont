# ==========================
# Makefile for ARM 32-bit
# ==========================

# Compiler
CC = arm-linux-gnueabihf-g++
CFLAGS = -g -std=c++17 -march=armv7-a -mfpu=neon -mfloat-abi=hard -Iinclude -Isrc -lcurl -lnlohmann_json
LDFLAGS = -lpthread -lcurl

# Project directories
SRC_DIR = src
INCLUDE_DIR = include
OBJ_DIR = obj
RUN_DIR = run

# Sources and objects
SRC_SOURCES = $(shell find $(SRC_DIR) -name '*.cpp')
SRC_OBJECTS = $(patsubst $(SRC_DIR)/%.cpp,$(OBJ_DIR)/src/%.o,$(SRC_SOURCES))

INCLUDE_SOURCES = $(shell find $(INCLUDE_DIR) -name '*.cpp')
INCLUDE_OBJECTS = $(patsubst $(INCLUDE_DIR)/%.cpp,$(OBJ_DIR)/include/%.o,$(INCLUDE_SOURCES))

# Executable
EXECUTABLE = $(RUN_DIR)/main

# ==========================
# Rules
# ==========================

all: $(EXECUTABLE)

# Link all objects
$(EXECUTABLE): $(SRC_OBJECTS) $(INCLUDE_OBJECTS)
	mkdir -p $(RUN_DIR)
	$(CC) $^ -o $@ $(LDFLAGS)

# Compile src files
$(OBJ_DIR)/src/%.o: $(SRC_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

# Compile include files
$(OBJ_DIR)/include/%.o: $(INCLUDE_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

# Clean everything
clean:
	rm -rf $(OBJ_DIR) $(RUN_DIR)

.PHONY: all clean