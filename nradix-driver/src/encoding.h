/**
 * encoding.h - Ternary Encoding Module for Optical Computing
 *
 * This module provides conversion functions between floating-point values
 * and balanced ternary representation, optimized for optical computing.
 *
 * Balanced ternary uses digits {-1, 0, +1} instead of {0, 1, 2}.
 * This maps naturally to optical states: no light, partial, full intensity.
 *
 * Packing efficiency: 3^5 = 243 < 256, so 5 trits fit in one byte.
 */

#ifndef ENCODING_H
#define ENCODING_H

#include <stdint.h>
#include <stddef.h>

/* Trit values in balanced ternary */
#define TRIT_NEG  (-1)
#define TRIT_ZERO (0)
#define TRIT_POS  (1)

/**
 * Convert a float in range [-1, 1] to balanced ternary representation.
 *
 * @param value     Input float, clamped to [-1, 1]
 * @param trits     Output array of trits (each -1, 0, or +1)
 * @param num_trits Number of trits to generate (precision)
 * @return          0 on success, -1 on error
 */
int float_to_balanced_ternary(float value, int8_t *trits, int num_trits);

/**
 * Convert balanced ternary representation back to float.
 *
 * @param trits     Input array of trits (each -1, 0, or +1)
 * @param num_trits Number of trits in the array
 * @return          Reconstructed float value in [-1, 1]
 */
float balanced_ternary_to_float(const int8_t *trits, int num_trits);

/**
 * Pack 5 trits into a single byte.
 *
 * Formula: (t0+1) + (t1+1)*3 + (t2+1)*9 + (t3+1)*27 + (t4+1)*81
 * This gives values 0-242, fitting in a byte (3^5 = 243 < 256).
 *
 * @param t0-t4  Five trits, each in {-1, 0, +1}
 * @return       Packed byte value (0-242)
 */
uint8_t pack_trits(int8_t t0, int8_t t1, int8_t t2, int8_t t3, int8_t t4);

/**
 * Unpack a byte into 5 trits.
 *
 * @param packed  Packed byte value (0-242)
 * @param trits   Output array of 5 trits (each -1, 0, or +1)
 */
void unpack_trits(uint8_t packed, int8_t *trits);

/**
 * Convert a float matrix to packed ternary representation.
 *
 * @param matrix        Input float matrix (row-major, values in [-1, 1])
 * @param rows          Number of rows
 * @param cols          Number of columns
 * @param trits_per_val Number of trits per float value
 * @param packed        Output packed byte array
 * @param packed_size   Size of packed array in bytes
 * @return              0 on success, -1 on error
 */
int float_matrix_to_ternary(const float *matrix, int rows, int cols,
                            int trits_per_val, uint8_t *packed, size_t packed_size);

/**
 * Convert packed ternary representation back to float matrix.
 *
 * @param packed        Input packed byte array
 * @param packed_size   Size of packed array in bytes
 * @param trits_per_val Number of trits per float value
 * @param matrix        Output float matrix (row-major)
 * @param rows          Number of rows
 * @param cols          Number of columns
 * @return              0 on success, -1 on error
 */
int ternary_to_float_matrix(const uint8_t *packed, size_t packed_size,
                            int trits_per_val, float *matrix, int rows, int cols);

/**
 * Calculate packed size needed for a matrix.
 *
 * @param rows          Number of rows
 * @param cols          Number of columns
 * @param trits_per_val Number of trits per float value
 * @return              Required bytes for packed representation
 */
size_t calculate_packed_size(int rows, int cols, int trits_per_val);

#endif /* ENCODING_H */
