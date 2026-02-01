import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def draw_block_diagram():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    
    # Function to draw a box with text
    def draw_box(x, y, w, h, text, color='#E0E0E0', ec='black'):
        # Use FancyBboxPatch for rounded corners
        # Note: FancyBboxPatch takes (x,y) as bottom-left, similar to Rectangle
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=ec, facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=10, fontweight='bold')
        return x+w, y+h/2 # Return connection point (right center)

    # Function to draw arrow
    def draw_arrow(x1, y1, x2, y2, color='black'):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5))

    # --- 1. Source Layer (Revised) ---
    ax.text(2, 7.5, "1. Source Layer\n(Single Pump)", ha='center', fontsize=12, fontweight='bold')
    
    # Single Pump Laser
    draw_box(0.5, 3.5, 1.5, 1.0, "Pump\nLaser", color='#FFFFFF')
    draw_arrow(2, 4.0, 3, 4.0, 'black') # Pump light
    
    # Kerr Comb (The Rainbow Generator)
    draw_box(3, 3.5, 1.5, 1.0, "Kerr\nComb", color='#F0F0F0')
    
    # Comb Output (Multi-color arrow concept)
    ax.annotate("", xy=(5.5, 4.0), xytext=(4.5, 4.0),
                arrowprops=dict(arrowstyle="->", color='purple', lw=2))
    ax.text(5, 4.2, "Comb", ha='center', fontsize=9)
    
    # AWG (The Splitter)
    # Visualize AWG as a large block splitting paths
    path_awg = patches.Polygon([[5.5, 4.5], [5.5, 3.5], [6.5, 6.5], [6.5, 1.5]], closed=True, facecolor='#E0E0E0', edgecolor='black')
    ax.add_patch(path_awg)
    ax.text(6.0, 4.0, "AWG\n(Demux)", ha='center', fontsize=9, rotation=90)
    
    # --- 2. Logic Layer (Selectors) ---
    ax.text(8, 7.5, "2. Logic Layer", ha='center', fontsize=12, fontweight='bold')
    
    # Outputs from AWG to Selectors
    # Red Path (Top)
    draw_arrow(6.5, 6.0, 7.5, 6.0, 'red')
    draw_box(7.5, 5.6, 1.5, 0.8, "Selector\n($\lambda$=1.55$\mu$m)", color='white')
    
    # Green Path (Middle)
    draw_arrow(6.5, 4.0, 7.5, 4.0, 'green')
    draw_box(7.5, 3.6, 1.5, 0.8, "Selector\n($\lambda$=1.30$\mu$m)", color='white')
    
    # Blue Path (Bottom)
    draw_arrow(6.5, 2.0, 7.5, 2.0, 'blue')
    draw_box(7.5, 1.6, 1.5, 0.8, "Selector\n($\lambda$=1.00$\mu$m)", color='white')
    
    # --- 3. Processing Layer ---
    ax.text(12, 7.5, "3. Processing", ha='center', fontsize=12, fontweight='bold')
    
    # Combiner Mux
    path_mux = patches.Polygon([[9.5, 6.5], [9.5, 1.5], [10.5, 4.5], [10.5, 3.5]], closed=True, facecolor='#E0E0E0', edgecolor='black')
    ax.add_patch(path_mux)
    
    draw_arrow(9.0, 6.0, 9.5, 6.0, 'red')
    draw_arrow(9.0, 4.0, 9.5, 4.0, 'green')
    draw_arrow(9.0, 2.0, 9.5, 2.0, 'blue')
    
    # Nonlinear Mixer
    draw_box(11, 3.5, 2.0, 1.0, "SFG Mixer\n($\chi^{(2)}$)", color='#FFFFCC')
    draw_arrow(10.5, 4.0, 11, 4.0, 'black')
    
    # Output
    draw_arrow(13, 4.0, 13.8, 4.0, 'purple')
    ax.text(13.8, 4.3, "Result\n($\lambda_{sum}$)", ha='right', fontsize=10)
    ax.text(13.8, 3.8, "0.56 / 0.61 / 0.71 $\mu$m", ha='right', fontsize=8, color='purple')

    plt.tight_layout()
    
    output_path = os.path.join(os.path.dirname(__file__), '../data/new_architecture.png')
    plt.savefig(output_path, dpi=300)
    print(f"Architecture diagram saved to: {output_path}")

if __name__ == "__main__":
    draw_block_diagram()
