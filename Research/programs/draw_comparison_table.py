import matplotlib.pyplot as plt

def draw_comparison_table():
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('off')
    
    # Table Data
    columns = ["Approach", "Cost Scaling", "Speed", "Scalability", "Key Limitation"]
    rows = [
        ["Electronic Ternary\n(Transistors)", "High\n(~40x per trit)", "Medium\n(GHz)", "Low\n(Wiring)", "Radix\nPenalty"],
        ["Optical Ternary\n(Polarization)", "Medium\n(Filter complexity)", "High\n(THz)", "Medium", "Difficult\nDetection"],
        ["Optical Ternary\n(Wavelength - Ours)", "Constant\n(WDM)", "High\n(THz)", "High\n(Telecom)", "Waveguide\nSize"]
    ]
    
    # Colors
    colors = [['#E0E0E0'] * 5, ['#F9F9F9'] * 5, ['#E6F2FF'] * 5] # Highlight ours in light blue
    
    # Create Table
    table = ax.table(cellText=rows, colLabels=columns, cellLoc='center', loc='center', cellColours=colors)
    
    # Formatting
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5) # Wider rows
    
    # Make header bold (manually iterating since matplotlib table header is tricky)
    # Just standard clean look is sufficient for IEEE
    
    plt.title("Comparison of Ternary Computing Implementations", fontsize=14, fontweight='bold', y=0.95)
    
    output_path = os.path.join(os.path.dirname(__file__), '../data/new_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Comparison table saved to: {output_path}")

if __name__ == "__main__":
    import os
    draw_comparison_table()
