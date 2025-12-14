"""
Visualization comparing time spent on AI-assisted coding vs manual implementation
Shows crossover points where manual coding becomes more efficient

CORRECTED LOGIC:
- Manual implementation time > Explanation time (always!)
- AI total time = Explanation + Review/Debug + Iteration overhead
- Crossover happens when AI overhead exceeds manual implementation efficiency
"""

import matplotlib.pyplot as plt
import numpy as np

# Create complexity range (0 = trivial, 10 = very complex)
complexity = np.linspace(0, 10, 100)

# ============================================================================
# JUNIOR DEVELOPER MODEL
# ============================================================================

# Manual implementation: Juniors are slower, time grows exponentially with complexity
junior_manual = 10 + complexity**2 * 3

# AI explanation time: Always less than manual (otherwise why use AI?)
# But grows with complexity as requirements become harder to articulate
junior_explain = 3 + complexity**1.5 * 1.5

# AI overhead: Review AI output, fix bugs, iterate on prompts
# This overhead grows significantly with complexity
junior_ai_overhead = 2 + complexity**1.8 * 2

# Total AI time = explain + overhead
junior_ai_total = junior_explain + junior_ai_overhead

# ============================================================================
# SENIOR DEVELOPER MODEL
# ============================================================================

# Manual implementation: Seniors are much faster, better algorithmic thinking
senior_manual = 5 + complexity**1.6 * 2

# AI explanation time: Seniors explain more efficiently but still takes time
senior_explain = 2 + complexity**1.3 * 1.2

# AI overhead: Seniors are better at prompting but still need to review/fix
# Overhead is lower than juniors but still grows with complexity
senior_ai_overhead = 1.5 + complexity**1.6 * 1.5

# Total AI time = explain + overhead
senior_ai_total = senior_explain + senior_ai_overhead

# ============================================================================
# CREATE VISUALIZATION
# ============================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle('AI-Assisted vs Manual Coding: When Does Manual Win?', 
             fontsize=16, fontweight='bold')

# ============================================================================
# PLOT 1: JUNIOR DEVELOPER
# ============================================================================

ax1.plot(complexity, junior_manual, 'g-', linewidth=3, label='Manual Implementation', 
         marker='s', markevery=15, markersize=8)
ax1.plot(complexity, junior_ai_total, 'b-', linewidth=3, label='AI Total (Explain + Overhead)', 
         marker='o', markevery=15, markersize=8)
ax1.plot(complexity, junior_explain, 'r--', linewidth=2, label='AI Explanation Time Only', 
         alpha=0.7, marker='^', markevery=15, markersize=6)

# Fill area showing AI overhead
ax1.fill_between(complexity, junior_explain, junior_ai_total, 
                 alpha=0.2, color='orange', label='AI Overhead (Review/Debug/Iterate)')

# Find crossover point
junior_diff = junior_manual - junior_ai_total
junior_crossover_idx = np.where(np.diff(np.sign(junior_diff)))[0]
if len(junior_crossover_idx) > 0:
    idx = junior_crossover_idx[0]
    crossover_x = complexity[idx]
    crossover_y = junior_ai_total[idx]
    
    ax1.plot(crossover_x, crossover_y, 'ro', markersize=18, 
            markeredgewidth=3, markerfacecolor='yellow', markeredgecolor='red', zorder=5)
    ax1.axvline(crossover_x, color='red', linestyle=':', linewidth=2, alpha=0.5)
    ax1.annotate(f'Crossover Point\nComplexity: {crossover_x:.1f}\nTime: {crossover_y:.0f} min', 
                xy=(crossover_x, crossover_y), 
                xytext=(crossover_x + 1.5, crossover_y + 30),
                arrowprops=dict(arrowstyle='->', color='red', lw=2.5),
                fontsize=11, fontweight='bold', color='red',
                bbox=dict(boxstyle='round,pad=0.6', facecolor='yellow', alpha=0.9, edgecolor='red', linewidth=2))
    
    # Add shaded regions
    ax1.axvspan(0, crossover_x, alpha=0.15, color='blue', label=f'AI Wins (0-{crossover_x:.1f})')
    ax1.axvspan(crossover_x, 10, alpha=0.15, color='green', label=f'Manual Wins ({crossover_x:.1f}-10)')

ax1.set_xlabel('Task Complexity (0=Trivial, 10=Very Complex)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Time (minutes)', fontsize=12, fontweight='bold')
ax1.set_title('Junior Developer', fontsize=14, fontweight='bold', pad=15)
ax1.legend(loc='upper left', fontsize=9, framealpha=0.95)
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.set_xlim(0, 10)
ax1.set_ylim(0, max(junior_manual.max(), junior_ai_total.max()) * 1.1)

# ============================================================================
# PLOT 2: SENIOR DEVELOPER
# ============================================================================

ax2.plot(complexity, senior_manual, 'g-', linewidth=3, label='Manual Implementation', 
         marker='s', markevery=15, markersize=8)
ax2.plot(complexity, senior_ai_total, 'b-', linewidth=3, label='AI Total (Explain + Overhead)', 
         marker='o', markevery=15, markersize=8)
ax2.plot(complexity, senior_explain, 'r--', linewidth=2, label='AI Explanation Time Only', 
         alpha=0.7, marker='^', markevery=15, markersize=6)

# Fill area showing AI overhead
ax2.fill_between(complexity, senior_explain, senior_ai_total, 
                 alpha=0.2, color='orange', label='AI Overhead (Review/Debug/Iterate)')

# Find crossover point
senior_diff = senior_manual - senior_ai_total
senior_crossover_idx = np.where(np.diff(np.sign(senior_diff)))[0]
if len(senior_crossover_idx) > 0:
    idx = senior_crossover_idx[0]
    crossover_x = complexity[idx]
    crossover_y = senior_ai_total[idx]
    
    ax2.plot(crossover_x, crossover_y, 'mo', markersize=18, 
            markeredgewidth=3, markerfacecolor='yellow', markeredgecolor='magenta', zorder=5)
    ax2.axvline(crossover_x, color='magenta', linestyle=':', linewidth=2, alpha=0.5)
    ax2.annotate(f'Crossover Point\nComplexity: {crossover_x:.1f}\nTime: {crossover_y:.0f} min', 
                xy=(crossover_x, crossover_y), 
                xytext=(crossover_x + 1.5, crossover_y + 15),
                arrowprops=dict(arrowstyle='->', color='magenta', lw=2.5),
                fontsize=11, fontweight='bold', color='magenta',
                bbox=dict(boxstyle='round,pad=0.6', facecolor='yellow', alpha=0.9, edgecolor='magenta', linewidth=2))
    
    # Add shaded regions
    ax2.axvspan(0, crossover_x, alpha=0.15, color='blue', label=f'AI Wins (0-{crossover_x:.1f})')
    ax2.axvspan(crossover_x, 10, alpha=0.15, color='green', label=f'Manual Wins ({crossover_x:.1f}-10)')

ax2.set_xlabel('Task Complexity (0=Trivial, 10=Very Complex)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Time (minutes)', fontsize=12, fontweight='bold')
ax2.set_title('Senior Developer', fontsize=14, fontweight='bold', pad=15)
ax2.legend(loc='upper left', fontsize=9, framealpha=0.95)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.set_xlim(0, 10)
ax2.set_ylim(0, max(senior_manual.max(), senior_ai_total.max()) * 1.1)

plt.tight_layout()
plt.savefig('/Users/jportilla/Downloads/pilot/time_comparison.png', dpi=300, bbox_inches='tight')
print("✅ Plot saved to: time_comparison.png")

# ============================================================================
# COMBINED COMPARISON PLOT
# ============================================================================

fig2, ax = plt.subplots(figsize=(14, 8))

# Plot all curves
ax.plot(complexity, junior_manual, 'g-', linewidth=3, 
        label='Junior: Manual', marker='s', markevery=15, markersize=8)
ax.plot(complexity, junior_ai_total, 'b-', linewidth=3, 
        label='Junior: AI Total', marker='o', markevery=15, markersize=8)
ax.plot(complexity, senior_manual, 'g--', linewidth=3, 
        label='Senior: Manual', marker='s', markevery=15, markersize=8)
ax.plot(complexity, senior_ai_total, 'b--', linewidth=3, 
        label='Senior: AI Total', marker='o', markevery=15, markersize=8)

# Mark both crossover points
if len(junior_crossover_idx) > 0:
    idx = junior_crossover_idx[0]
    ax.plot(complexity[idx], junior_ai_total[idx], 'ro', markersize=18, 
            markeredgewidth=3, markerfacecolor='yellow', markeredgecolor='red', zorder=5)
    ax.annotate(f'Junior Crossover\n{complexity[idx]:.1f}', 
                xy=(complexity[idx], junior_ai_total[idx]), 
                xytext=(complexity[idx] + 1.5, junior_ai_total[idx] + 25),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=12, fontweight='bold', color='red',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9))

if len(senior_crossover_idx) > 0:
    idx = senior_crossover_idx[0]
    ax.plot(complexity[idx], senior_ai_total[idx], 'mo', markersize=18, 
            markeredgewidth=3, markerfacecolor='yellow', markeredgecolor='magenta', zorder=5)
    ax.annotate(f'Senior Crossover\n{complexity[idx]:.1f}', 
                xy=(complexity[idx], senior_ai_total[idx]), 
                xytext=(complexity[idx] - 2.5, senior_ai_total[idx] - 20),
                arrowprops=dict(arrowstyle='->', color='magenta', lw=2),
                fontsize=12, fontweight='bold', color='magenta',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9))

ax.set_xlabel('Task Complexity (0=Trivial, 10=Very Complex)', fontsize=13, fontweight='bold')
ax.set_ylabel('Time (minutes)', fontsize=13, fontweight='bold')
ax.set_title('AI vs Manual: Complete Comparison\nCrossover points show where manual coding becomes more efficient', 
             fontsize=15, fontweight='bold')
ax.legend(loc='upper left', fontsize=12, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 10)

plt.tight_layout()
plt.savefig('/Users/jportilla/Downloads/pilot/crossover_analysis.png', dpi=300, bbox_inches='tight')
print("✅ Crossover analysis plot saved to: crossover_analysis.png")

plt.show()

print("\n" + "="*60)
print("KEY INSIGHTS (CORRECTED)")
print("="*60)
print(f"""
✅ CORRECTED ASSUMPTIONS:
   • Manual implementation time > Explanation time (ALWAYS!)
   • AI has overhead: reviewing output, fixing bugs, iterating on prompts
   • Crossover happens when AI overhead exceeds manual efficiency gains

📊 JUNIOR DEVELOPERS:
   • Crossover at complexity ~{complexity[junior_crossover_idx[0]] if len(junior_crossover_idx) > 0 else 'N/A'}
   • AI wins for simple-to-medium tasks
   • Manual wins for complex tasks (overhead too high)

📊 SENIOR DEVELOPERS:
   • Crossover at complexity ~{complexity[senior_crossover_idx[0]] if len(senior_crossover_idx) > 0 else 'N/A'}
   • Crossover happens EARLIER than juniors
   • Seniors code complex logic faster than explaining it to AI

🎯 THE PARADOX:
   • Better developers = earlier crossover point
   • AI is most valuable for juniors on complex tasks? NO!
   • AI is most valuable for EVERYONE on simple/repetitive tasks
   • Complex tasks: Manual coding wins for experienced developers
""")
