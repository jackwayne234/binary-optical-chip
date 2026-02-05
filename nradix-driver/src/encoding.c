/**
 * encoding.c - Ternary Encoding Implementation
 *
 * Balanced Ternary Math:
 * ----------------------
 * Each trit position i has weight 3^i. With balanced ternary {-1, 0, +1}:
 *   value = sum(trit[i] * 3^i) for i = 0 to n-1
 *
 * For n trits, the range is [-(3^n - 1)/2, +(3^n - 1)/2].
 * We normalize this to [-1, +1] for float conversion.
 *
 * Packing Math:
 * -------------
 * To pack trits into bytes, we shift from {-1, 0, +1} to {0, 1, 2}.
 * Then treat as base-3 number: packed = sum((trit[i]+1) * 3^i)
 *
 * For 5 trits: 3^5 = 243 possible values, which fits in a byte (< 256).
 * This gives ~1.58 bits per trit, close to theoretical log2(3) = 1.585.
 */

#include "encoding.h"
#include <math.h>
#include <string.h>

/* Clamp value to range [-1, 1] */
static inline float clamp(float v) {
    if (v < -1.0f) return -1.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

/**
 * Convert float [-1, 1] to balanced ternary.
 *
 * Algorithm:
 * 1. Scale float to integer range [-(3^n-1)/2, +(3^n-1)/2]
 * 2. Convert integer to balanced ternary using modified base-3 conversion
 *
 * For balanced ternary conversion of integer k:
 *   - If k mod 3 == 0: trit = 0, k = k/3
 *   - If k mod 3 == 1: trit = 1, k = k/3
 *   - If k mod 3 == 2: trit = -1, k = (k+1)/3  (borrow from next position)
 */
int float_to_balanced_ternary(float value, int8_t *trits, int num_trits) {
    if (!trits || num_trits <= 0) {
        return -1;
    }

    /* Clamp input to valid range */
    value = clamp(value);

    /* Calculate max representable value: (3^n - 1) / 2 */
    int max_val = 1;
    for (int i = 0; i < num_trits; i++) {
        max_val *= 3;
    }
    max_val = (max_val - 1) / 2;

    /* Scale float to integer range */
    int k = (int)roundf(value * max_val);

    /* Convert to balanced ternary */
    for (int i = 0; i < num_trits; i++) {
        int rem = k % 3;

        /* Handle negative numbers correctly */
        if (k < 0 && rem != 0) {
            rem += 3;
        }

        if (rem == 0) {
            trits[i] = 0;
            k = k / 3;
        } else if (rem == 1) {
            trits[i] = 1;
            k = k / 3;
        } else {  /* rem == 2 */
            trits[i] = -1;
            k = (k + 1) / 3;
        }
    }

    return 0;
}

/**
 * Convert balanced ternary back to float.
 *
 * Sum up: trit[i] * 3^i, then normalize to [-1, 1].
 */
float balanced_ternary_to_float(const int8_t *trits, int num_trits) {
    if (!trits || num_trits <= 0) {
        return 0.0f;
    }

    /* Calculate value as sum of trit[i] * 3^i */
    int value = 0;
    int power = 1;
    for (int i = 0; i < num_trits; i++) {
        value += trits[i] * power;
        power *= 3;
    }

    /* Calculate max value for normalization: (3^n - 1) / 2 */
    int max_val = (power - 1) / 2;

    /* Normalize to [-1, 1] */
    return (float)value / (float)max_val;
}

/**
 * Pack 5 trits into one byte.
 *
 * Math: 3^5 = 243 < 256, so 5 trits fit in a byte.
 *
 * Shift trits from {-1, 0, +1} to {0, 1, 2}, then encode as base-3:
 *   packed = (t0+1) + (t1+1)*3 + (t2+1)*9 + (t3+1)*27 + (t4+1)*81
 *
 * This gives values 0 to 242 (when all trits are +1).
 */
uint8_t pack_trits(int8_t t0, int8_t t1, int8_t t2, int8_t t3, int8_t t4) {
    return (uint8_t)(
        (t0 + 1) +
        (t1 + 1) * 3 +
        (t2 + 1) * 9 +
        (t3 + 1) * 27 +
        (t4 + 1) * 81
    );
}

/**
 * Unpack a byte into 5 trits.
 *
 * Reverse of pack_trits: extract each base-3 digit, then shift back
 * from {0, 1, 2} to {-1, 0, +1}.
 */
void unpack_trits(uint8_t packed, int8_t *trits) {
    if (!trits) return;

    /* Extract each base-3 digit and shift to balanced form */
    trits[0] = (packed % 3) - 1;
    packed /= 3;
    trits[1] = (packed % 3) - 1;
    packed /= 3;
    trits[2] = (packed % 3) - 1;
    packed /= 3;
    trits[3] = (packed % 3) - 1;
    packed /= 3;
    trits[4] = (packed % 3) - 1;
}

/**
 * Calculate packed byte size needed for a matrix.
 *
 * Total trits = rows * cols * trits_per_val
 * Bytes needed = ceil(total_trits / 5)
 */
size_t calculate_packed_size(int rows, int cols, int trits_per_val) {
    size_t total_trits = (size_t)rows * cols * trits_per_val;
    return (total_trits + 4) / 5;  /* Ceiling division by 5 */
}

/**
 * Convert float matrix to packed ternary.
 *
 * Process:
 * 1. Convert each float to balanced ternary (num_trits per value)
 * 2. Collect all trits into a stream
 * 3. Pack groups of 5 trits into bytes
 */
int float_matrix_to_ternary(const float *matrix, int rows, int cols,
                            int trits_per_val, uint8_t *packed, size_t packed_size) {
    if (!matrix || !packed || rows <= 0 || cols <= 0 || trits_per_val <= 0) {
        return -1;
    }

    size_t required_size = calculate_packed_size(rows, cols, trits_per_val);
    if (packed_size < required_size) {
        return -1;
    }

    /* Initialize output */
    memset(packed, 0, packed_size);

    /* Temporary storage for trits */
    int8_t trits[64];  /* Enough for reasonable trits_per_val */
    if (trits_per_val > 64) {
        return -1;
    }

    /* Track position in packed output */
    size_t trit_index = 0;
    int8_t trit_buffer[5] = {0, 0, 0, 0, 0};
    int buffer_pos = 0;
    size_t packed_index = 0;

    /* Process each matrix element */
    for (int i = 0; i < rows * cols; i++) {
        /* Convert float to trits */
        float_to_balanced_ternary(matrix[i], trits, trits_per_val);

        /* Add trits to buffer, pack when we have 5 */
        for (int j = 0; j < trits_per_val; j++) {
            trit_buffer[buffer_pos++] = trits[j];

            if (buffer_pos == 5) {
                packed[packed_index++] = pack_trits(
                    trit_buffer[0], trit_buffer[1], trit_buffer[2],
                    trit_buffer[3], trit_buffer[4]
                );
                buffer_pos = 0;
            }
        }
    }

    /* Pack any remaining trits (padded with zeros) */
    if (buffer_pos > 0) {
        while (buffer_pos < 5) {
            trit_buffer[buffer_pos++] = 0;
        }
        packed[packed_index] = pack_trits(
            trit_buffer[0], trit_buffer[1], trit_buffer[2],
            trit_buffer[3], trit_buffer[4]
        );
    }

    return 0;
}

/**
 * Convert packed ternary back to float matrix.
 *
 * Reverse of float_matrix_to_ternary:
 * 1. Unpack bytes into trit stream
 * 2. Group trits into sets of trits_per_val
 * 3. Convert each group back to float
 */
int ternary_to_float_matrix(const uint8_t *packed, size_t packed_size,
                            int trits_per_val, float *matrix, int rows, int cols) {
    if (!packed || !matrix || rows <= 0 || cols <= 0 || trits_per_val <= 0) {
        return -1;
    }

    /* Temporary storage for trits */
    int8_t trits[64];
    if (trits_per_val > 64) {
        return -1;
    }

    /* Track position in packed input */
    size_t packed_index = 0;
    int8_t unpacked[5];
    int unpack_pos = 5;  /* Force initial unpack */

    /* Process each matrix element */
    for (int i = 0; i < rows * cols; i++) {
        /* Collect trits_per_val trits for this float */
        for (int j = 0; j < trits_per_val; j++) {
            if (unpack_pos >= 5) {
                if (packed_index >= packed_size) {
                    return -1;  /* Ran out of packed data */
                }
                unpack_trits(packed[packed_index++], unpacked);
                unpack_pos = 0;
            }
            trits[j] = unpacked[unpack_pos++];
        }

        /* Convert trits back to float */
        matrix[i] = balanced_ternary_to_float(trits, trits_per_val);
    }

    return 0;
}
