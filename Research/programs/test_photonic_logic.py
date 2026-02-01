import os
import sys
import pytest
import glob

# Add scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts import sfg_mixer
from scripts import optical_selector
from scripts import y_junction
from scripts import photodetector

def get_data_path(filename):
    """
    Helper to get the absolute path to a file in the data directory.
    Assumes we are running from project root or inside scripts.
    """
    # Base dir is the parent of the 'scripts' directory containing this test file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", filename)

def test_sfg_mixer_execution():
    """
    Verifies that the SFG Mixer simulation runs and generates the spectrum plot.
    """
    # Run the simulation function
    sfg_mixer.run_sfg_simulation()
    
    # Check if output file exists
    output_plot = get_data_path("sfg_spectrum.png")
    assert os.path.exists(output_plot), f"SFG Spectrum plot was not created at {output_plot}"

def test_optical_selector_execution():
    """
    Verifies the Optical Selector runs for both ON and OFF states.
    """
    # Test OFF state
    optical_selector.run_selector_simulation(voltage_on=False)
    assert os.path.exists(get_data_path("selector_spectrum_OFF.png"))
    
    # Test ON state
    optical_selector.run_selector_simulation(voltage_on=True)
    assert os.path.exists(get_data_path("selector_spectrum_ON.png"))

def test_y_junction_execution():
    """
    Verifies the Y-Junction Combiner simulation.
    """
    y_junction.run_y_junction_simulation()
    assert os.path.exists(get_data_path("y_junction_spectrum.png"))
    assert os.path.exists(get_data_path("y_junction_geometry.png"))


def test_photodetector_execution():
    """
    Verifies the Photodetector simulation.
    """
    # Capture stdout to check for detection message if needed, 
    # but for now just check it runs without error.
    photodetector.run_photodetector_simulation()
    
    # Verify data files if any (we print to stdout, but we could check for log files)
    # Ideally, we'd check the return value of the function, but our scripts print to stdout.
    # We assume success if no exception is raised.
