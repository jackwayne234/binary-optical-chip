import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def draw_state_encoding():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')
    
    # Title
    ax.text(5, 4.5, "Wavelength-Division Ternary State Encoding", ha='center', fontsize=12, fontweight='bold')
    
    # Function to draw a state box
    def draw_state(x, label, wvl, color, state_val):
        # State Circle
        circle = patches.Circle((x, 2.5), 0.8, facecolor=color, edgecolor='black', alpha=0.3)
        ax.add_patch(circle)
        
        # State Text
        ax.text(x, 2.5, f"State\n{state_val}", ha='center', va='center', fontsize=12, fontweight='bold')
        
        # Wavelength Label
        ax.text(x, 1.2, f"{label}\n$\lambda = {wvl} \mu m$", ha='center', va='top', fontsize=10)
        
        # Pulse/Wave visual (simple line)
        t = [x - 0.5 + i*0.1 for i in range(11)]
        # Just a visual marker
        ax.plot([x-0.6, x+0.6], [3.5, 3.5], color=color, lw=3)
        ax.text(x, 3.7, "Optical Carrier", ha='center', fontsize=8, color='gray')

    # Draw the three states
    # State -1 (Red)
    draw_state(2, "Red", "1.55", 'red', "-1")
    
    # State 0 (Green)
    draw_state(5, "Green", "1.30", 'green', "0")
    
    # State 1 (Blue)
    draw_state(8, "Blue", "1.00", 'blue', "1")
    
    plt.tight_layout()
    
    output_path = os.path.join(os.path.dirname(__file__), '../data/new_state_encoding.png')
    plt.savefig(output_path, dpi=300)
    print(f"Encoding diagram saved to: {output_path}")

if __name__ == "__main__":
    draw_state_encoding()
