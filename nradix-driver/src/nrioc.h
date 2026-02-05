/**
 * @file nrioc.h
 * @brief N-Radix I/O Control (NRIOC) Driver Interface
 *
 * This header defines the interface for controlling N-Radix optical
 * computing arrays. It provides functions for memory management,
 * command submission, and synchronization with the optical processing
 * elements.
 */

#ifndef NRIOC_H
#define NRIOC_H

#include <stdint.h>
#include <stdbool.h>

/*============================================================================
 * Status Codes
 *===========================================================================*/

/** Operation completed successfully */
#define NR_OK               0x00

/** Device is busy processing a previous command */
#define NR_BUSY             0x01

/** Arithmetic overflow occurred in computation */
#define NR_ERR_OVERFLOW     0x10

/** Memory address not properly aligned for operation */
#define NR_ERR_ALIGNMENT    0x11

/** Invalid size parameter (zero, negative, or exceeds limits) */
#define NR_ERR_SIZE         0x12

/** Operation timed out waiting for completion */
#define NR_ERR_TIMEOUT      0x20

/*============================================================================
 * Command Codes
 *===========================================================================*/

/** Load weight matrix into optical array memory */
#define NR_LOAD_WEIGHTS     0x01

/** Stream input vector/matrix to processing elements */
#define NR_STREAM_INPUT     0x02

/** Execute matrix-vector or matrix-matrix computation */
#define NR_COMPUTE          0x03

/** Read output results from optical array */
#define NR_READ_OUTPUT      0x04

/** Reset array state and clear all pending operations */
#define NR_RESET            0x0F

/*============================================================================
 * Processing Element Types
 *===========================================================================*/

/** Addition-based processing element (uses SFG mixer) */
#define PE_TYPE_ADD         0

/** Multiplication-based processing element (uses Kerr nonlinearity) */
#define PE_TYPE_MUL         1

/*============================================================================
 * Data Structures
 *===========================================================================*/

/**
 * @brief Command descriptor for NRIOC operations
 *
 * This structure encapsulates all parameters needed to submit a command
 * to the optical array. Commands are queued and executed asynchronously.
 */
typedef struct {
    uint32_t command;    /**< Command code (NR_LOAD_WEIGHTS, NR_COMPUTE, etc.) */
    uint32_t flags;      /**< Command-specific flags and options */
    uint64_t src_addr;   /**< Source address in device memory */
    uint64_t dst_addr;   /**< Destination address in device memory */
    uint32_t width;      /**< Matrix width (columns) */
    uint32_t height;     /**< Matrix height (rows) */
    uint32_t pe_type;    /**< Processing element type (PE_TYPE_ADD or PE_TYPE_MUL) */
} nrioc_command_t;

/*============================================================================
 * Initialization and Shutdown
 *===========================================================================*/

/**
 * @brief Initialize the NRIOC driver and optical array
 *
 * Must be called before any other NRIOC functions. Performs hardware
 * detection, allocates internal resources, and resets the optical array
 * to a known state.
 *
 * @return NR_OK on success, error code on failure
 */
int nrioc_init(void);

/**
 * @brief Shutdown the NRIOC driver and release resources
 *
 * Waits for pending operations to complete, releases allocated memory,
 * and puts the optical array into low-power state. Must be called
 * before program exit.
 *
 * @return NR_OK on success, error code on failure
 */
int nrioc_shutdown(void);

/*============================================================================
 * Array Information
 *===========================================================================*/

/**
 * @brief Query the physical dimensions of the optical array
 *
 * Returns the maximum matrix dimensions supported by the hardware.
 * Actual computation sizes must not exceed these limits.
 *
 * @param[out] width   Pointer to store array width (columns)
 * @param[out] height  Pointer to store array height (rows)
 * @return NR_OK on success, error code on failure
 */
int nrioc_get_array_size(uint32_t *width, uint32_t *height);

/*============================================================================
 * Memory Management
 *===========================================================================*/

/**
 * @brief Allocate memory in the optical array's address space
 *
 * Allocates a contiguous block of device memory for storing matrices
 * or vectors. Memory is aligned for optimal DMA transfer performance.
 *
 * @param size  Number of bytes to allocate
 * @return Device address on success, 0 on failure
 */
uint64_t nrioc_alloc(size_t size);

/**
 * @brief Free previously allocated device memory
 *
 * Releases memory allocated by nrioc_alloc(). The address must not
 * be used after this call returns.
 *
 * @param addr  Device address returned by nrioc_alloc()
 * @return NR_OK on success, error code on failure
 */
int nrioc_free(uint64_t addr);

/*============================================================================
 * Command Submission and Synchronization
 *===========================================================================*/

/**
 * @brief Submit a command to the optical array for execution
 *
 * Queues a command for asynchronous execution. Returns immediately
 * without waiting for completion. Use nrioc_wait() to synchronize.
 *
 * @param cmd  Pointer to command descriptor (copied internally)
 * @return NR_OK on success, NR_BUSY if queue full, error code on failure
 */
int nrioc_submit(const nrioc_command_t *cmd);

/**
 * @brief Wait for all pending commands to complete
 *
 * Blocks until all previously submitted commands have finished
 * execution. Times out after the specified duration.
 *
 * @param timeout_ms  Maximum time to wait in milliseconds (0 = infinite)
 * @return NR_OK on success, NR_ERR_TIMEOUT if timed out
 */
int nrioc_wait(uint32_t timeout_ms);

/**
 * @brief Query the current status of the optical array
 *
 * Returns the current operational status without blocking.
 * Useful for polling-based synchronization.
 *
 * @return NR_OK if idle, NR_BUSY if processing, error code if fault
 */
int nrioc_get_status(void);

/*============================================================================
 * High-Level Operations
 *===========================================================================*/

/**
 * @brief Load a weight matrix into the optical array
 *
 * Convenience function that constructs and submits a NR_LOAD_WEIGHTS
 * command. Weights are transferred from host memory to device memory
 * and configured in the optical processing elements.
 *
 * @param weights     Pointer to weight data in host memory
 * @param dst_addr    Destination address in device memory
 * @param width       Matrix width (columns)
 * @param height      Matrix height (rows)
 * @return NR_OK on success, error code on failure
 */
int nrioc_load_weights(const void *weights, uint64_t dst_addr,
                       uint32_t width, uint32_t height);

/**
 * @brief Execute a matrix computation
 *
 * Convenience function that constructs and submits a NR_COMPUTE command.
 * Performs matrix-vector or matrix-matrix multiplication/addition using
 * the specified processing element type.
 *
 * @param src_addr    Source matrix/vector address in device memory
 * @param dst_addr    Destination address for results
 * @param width       Computation width
 * @param height      Computation height
 * @param pe_type     Processing element type (PE_TYPE_ADD or PE_TYPE_MUL)
 * @return NR_OK on success, error code on failure
 */
int nrioc_compute(uint64_t src_addr, uint64_t dst_addr,
                  uint32_t width, uint32_t height, uint32_t pe_type);

#endif /* NRIOC_H */
