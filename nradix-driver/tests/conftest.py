"""
Pytest configuration and shared fixtures for N-Radix driver tests.
"""

import pytest
import numpy as np
import sys

# Add the python module to path
sys.path.insert(0, '/home/jackwayne/Desktop/Optical_computing/nradix-driver/python')


@pytest.fixture(scope="session")
def random_seed():
    """Provide a fixed random seed for reproducibility."""
    return 42


@pytest.fixture
def rng(random_seed):
    """Provide a seeded numpy random generator."""
    return np.random.default_rng(random_seed)


@pytest.fixture(params=[9, 27, 81])
def array_size(request):
    """Parametrize tests over common array sizes."""
    return request.param


@pytest.fixture(params=[3, 5, 7])
def num_trits(request):
    """Parametrize tests over common trit counts."""
    return request.param


@pytest.fixture
def identity_weights(array_size):
    """Provide identity matrix weights for given array size."""
    return np.eye(array_size)


@pytest.fixture
def random_weights(array_size, rng):
    """Provide random weights in [-1, 1] for given array size."""
    return rng.uniform(-1.0, 1.0, (array_size, array_size))


@pytest.fixture
def random_input(array_size, rng):
    """Provide random input vector in [-1, 1] for given array size."""
    return rng.uniform(-1.0, 1.0, array_size)
