/*
 * NR-IOC: N-Radix Integrated Optical Computing Driver
 *
 * Header file for the optical computing hardware driver.
 * Provides interface for ternary optical matrix operations.
 *
 * Copyright (c) 2026 Optical Computing Project
 * SPDX-License-Identifier: MIT
 */

#ifndef NRIOC_H
#define NRIOC_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Status codes */
typedef enum {
    NR_OK = 0,
    NR_ERROR = -1,
    NR_TIMEOUT = -2,
    NR_BUSY = -3,
    NR_INVALID_PARAM = -4,
    NR_NO_DEVICE = -5,
    NR_OUT_OF_MEMORY = -6
} nrioc_status_t;

/* Device states */
typedef enum {
    NR_STATE_UNINITIALIZED = 0,
    NR_STATE_IDLE,
    NR_STATE_BUSY,
    NR_STATE_ERROR
} nrioc_state_t;

/* Command types */
typedef enum {
    NR_CMD_NOP = 0,
    NR_CMD_LOAD_WEIGHTS,
    NR_CMD_COMPUTE,
    NR_CMD_RESET,
    NR_CMD_CALIBRATE
} nrioc_cmd_type_t;

/* Command structure */
typedef struct {
    nrioc_cmd_type_t type;
    void *src;
    void *dst;
    int width;
    int height;
    uint32_t flags;
    uint64_t timestamp;
} nrioc_command_t;

/* Core API functions */
nrioc_status_t nrioc_init(void);
nrioc_status_t nrioc_shutdown(void);

/* Array configuration */
nrioc_status_t nrioc_get_array_size(int *width, int *height);

/* Memory management */
void *nrioc_alloc(size_t size);
void nrioc_free(void *ptr);

/* Command submission */
nrioc_status_t nrioc_submit(nrioc_command_t *cmd);
nrioc_status_t nrioc_wait(int timeout_ms);

/* Status queries */
nrioc_state_t nrioc_get_status(void);

/* Convenience wrappers */
nrioc_status_t nrioc_load_weights(void *weights, int width, int height);
nrioc_status_t nrioc_compute(void *input, void *output, int width, int height);

#ifdef __cplusplus
}
#endif

#endif /* NRIOC_H */
