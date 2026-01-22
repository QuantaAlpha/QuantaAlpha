#!/usr/bin/env python3
"""
QuantaAlpha vs AlphaAgent Factor Performance Visualization
Two visualization modes:
1. Single method multi-metric plot: show metrics vs topk ratio for each method
2. Comparison plot: direct comparison of both methods' performance and decay rate
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches

# Style settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 200

# Color schemes
COLORS = {
    'QuantaAlpha': {
        'primary': '#E63946',      # Vibrant red
        'secondary': '#FF6B6B',
        'fill': '#FFE5E5'
    },
    'AlphaAgent': {
        'primary': '#457B9D',      # Calm blue
        'secondary': '#7FB3D5', 
        'fill': '#E8F4F8'
    }
}

# Metric color mapping
METRIC_COLORS = {
    'IC': '#2E86AB',
    'ICIR': '#A23B72', 
    'Rank IC': '#F18F01',
    'Rank ICIR': '#C73E1D',
    'Ann. Return': '#3A7D44',
    'Info Ratio': '#7B2D8E',
    'Max DD': '#4A4A4A'
}

# Column name mapping (Chinese to English)
COL_MAP = {
    '方法': 'Method',
    'topk因子占比': 'TopK Ratio',
    '年化收益': 'Ann. Return',
    '信息比率': 'Info Ratio',
    '最大回撤': 'Max DD'
}

def load_data(filepath):
    """Load and rename CSV data"""
    df = pd.read_csv(filepath)
    df = df.rename(columns=COL_MAP)
    return df

def create_single_method_plot(df, method, save_path=None):
    """
    Create multi-metric plot for a single method
    Handles different scales with subplots
    """
    method_data = df[df['Method'] == method].copy()
    topk = method_data['TopK Ratio'].values
    
    # Define metric groups
    ic_metrics = ['IC', 'Rank IC']
    ratio_metrics = ['ICIR', 'Rank ICIR', 'Info Ratio']
    
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor('#FAFAFA')
    
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Main title
    color = COLORS[method]['primary']
    fig.suptitle(f'{method}: Metrics vs Top-K Factor Ratio', 
                 fontsize=18, fontweight='bold', color=color, y=0.98)
    
    # =============================================
    # Top-left: IC metrics
    # =============================================
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#FFFFFF')
    
    for metric in ic_metrics:
        values = method_data[metric].values
        ax1.plot(topk, values, 'o-', linewidth=2.5, markersize=8, 
                label=metric, color=METRIC_COLORS[metric])
        ax1.fill_between(topk, 0, values, alpha=0.15, color=METRIC_COLORS[metric])
    
    ax1.set_xlabel('Top-K Factor Ratio', fontsize=11)
    ax1.set_ylabel('IC Value', fontsize=11)
    ax1.set_title('IC Metrics', fontsize=13, fontweight='bold', pad=10)
    ax1.legend(loc='lower right', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_xlim(0.1, 1.0)
    
    # =============================================
    # Top-center: Ratio metrics  
    # =============================================
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#FFFFFF')
    
    for metric in ratio_metrics:
        values = method_data[metric].values
        ax2.plot(topk, values, 'o-', linewidth=2.5, markersize=8,
                label=metric, color=METRIC_COLORS[metric])
    
    ax2.set_xlabel('Top-K Factor Ratio', fontsize=11)
    ax2.set_ylabel('Ratio Value', fontsize=11)
    ax2.set_title('Ratio Metrics (ICIR / Info Ratio)', fontsize=13, fontweight='bold', pad=10)
    ax2.legend(loc='lower right', framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_xlim(0.1, 1.0)
    
    # =============================================
    # Bottom-left: Return metrics
    # =============================================
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor('#FFFFFF')
    
    values = method_data['Ann. Return'].values
    bars = ax3.bar(topk, values, width=0.1, color=METRIC_COLORS['Ann. Return'], 
                   alpha=0.7, edgecolor='white', linewidth=1.5)
    ax3.plot(topk, values, 'o-', linewidth=2, markersize=6, 
            color=METRIC_COLORS['Ann. Return'])
    
    for i, (x, v) in enumerate(zip(topk, values)):
        ax3.annotate(f'{v:.1%}', (x, v), textcoords="offset points",
                    xytext=(0, 8), ha='center', fontsize=9, fontweight='bold')
    
    ax3.set_xlabel('Top-K Factor Ratio', fontsize=11)
    ax3.set_ylabel('Annualized Return', fontsize=11)
    ax3.set_title('Annualized Return', fontsize=13, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax3.set_xlim(0.05, 1.0)
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0%}'))
    
    # =============================================
    # Bottom-center: Max Drawdown (negative values)
    # =============================================
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor('#FFFFFF')
    
    values = method_data['Max DD'].values
    abs_values = np.abs(values)
    
    bars = ax4.bar(topk, abs_values, width=0.1, color='#C73E1D', 
                   alpha=0.7, edgecolor='white', linewidth=1.5)
    ax4.plot(topk, abs_values, 'o-', linewidth=2, markersize=6, color='#C73E1D')
    
    for i, (x, v) in enumerate(zip(topk, abs_values)):
        ax4.annotate(f'{v:.1%}', (x, v), textcoords="offset points",
                    xytext=(0, 8), ha='center', fontsize=9, fontweight='bold')
    
    ax4.set_xlabel('Top-K Factor Ratio', fontsize=11)
    ax4.set_ylabel('Max Drawdown (Absolute)', fontsize=11)
    ax4.set_title('Max Drawdown', fontsize=13, fontweight='bold', pad=10)
    ax4.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax4.set_xlim(0.05, 1.0)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
    ax4.invert_yaxis()  # Lower is better for drawdown
    
    # =============================================
    # Right side: Radar chart (normalized)
    # =============================================
    ax5 = fig.add_subplot(gs[:, 2], projection='polar')
    
    metrics_for_radar = ['IC', 'ICIR', 'Rank IC', 'Rank ICIR', 'Ann. Return', 'Info Ratio']
    
    final_values = []
    for metric in metrics_for_radar:
        val = method_data[metric].iloc[-1]
        if metric in ['IC', 'Rank IC']:
            norm_val = val / 0.2
        elif metric in ['ICIR', 'Rank ICIR']:
            norm_val = val / 1.0
        elif metric == 'Ann. Return':
            norm_val = val / 0.4
        else:
            norm_val = val / 4.0
        final_values.append(min(norm_val, 1.0))
    
    angles = np.linspace(0, 2 * np.pi, len(metrics_for_radar), endpoint=False).tolist()
    final_values_plot = final_values + [final_values[0]]
    angles_plot = angles + [angles[0]]
    
    ax5.fill(angles_plot, final_values_plot, color=color, alpha=0.25)
    ax5.plot(angles_plot, final_values_plot, 'o-', linewidth=2, color=color, markersize=6)
    
    ax5.set_xticks(angles)
    ax5.set_xticklabels(metrics_for_radar, fontsize=10)
    ax5.set_ylim(0, 1)
    ax5.set_title(f'{method}\nOverall Performance (TopK=93%)', fontsize=12, fontweight='bold', pad=20)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"Saved: {save_path}")
    
    return fig


def create_comparison_plot(df, save_path=None):
    """
    Create dual-method comparison plot
    Show QuantaAlpha advantages and decay rate comparison
    """
    qa_data = df[df['Method'] == 'QuantaAlpha'].copy()
    aa_data = df[df['Method'] == 'AlphaAgent'].copy()
    topk = qa_data['TopK Ratio'].values
    
    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor('#FAFAFA')
    
    fig.suptitle('QuantaAlpha vs AlphaAgent: Performance Comparison', 
                 fontsize=20, fontweight='bold', y=0.98)
    
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    
    metrics_config = [
        ('IC', 'IC Comparison', gs[0, 0]),
        ('ICIR', 'ICIR Comparison', gs[0, 1]),
        ('Rank IC', 'Rank IC Comparison', gs[0, 2]),
        ('Rank ICIR', 'Rank ICIR Comparison', gs[1, 0]),
        ('Ann. Return', 'Annualized Return Comparison', gs[1, 1]),
        ('Info Ratio', 'Information Ratio Comparison', gs[1, 2]),
    ]
    
    for metric, title, pos in metrics_config:
        ax = fig.add_subplot(pos)
        ax.set_facecolor('#FFFFFF')
        
        qa_values = qa_data[metric].values
        aa_values = aa_data[metric].values
        
        line_qa, = ax.plot(topk, qa_values, 'o-', linewidth=2.5, markersize=8,
                          color=COLORS['QuantaAlpha']['primary'], label='QuantaAlpha')
        line_aa, = ax.plot(topk, aa_values, 's--', linewidth=2.5, markersize=8,
                          color=COLORS['AlphaAgent']['primary'], label='AlphaAgent')
        
        ax.fill_between(topk, qa_values, aa_values, 
                       where=(qa_values >= aa_values),
                       color=COLORS['QuantaAlpha']['fill'], alpha=0.5,
                       interpolate=True, label='QA Leading')
        ax.fill_between(topk, qa_values, aa_values,
                       where=(qa_values < aa_values),
                       color=COLORS['AlphaAgent']['fill'], alpha=0.5,
                       interpolate=True, label='AA Leading')
        
        ax.set_xlabel('Top-K Factor Ratio', fontsize=10)
        ax.set_ylabel(metric, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold', pad=8)
        ax.legend(loc='best', fontsize=8, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0.1, 1.0)
        
        final_diff = (qa_values[-1] - aa_values[-1]) / aa_values[-1] * 100
        ax.annotate(f'QA Lead: {final_diff:+.1f}%', 
                   xy=(0.95, 0.05), xycoords='axes fraction',
                   fontsize=9, fontweight='bold',
                   color=COLORS['QuantaAlpha']['primary'] if final_diff > 0 else COLORS['AlphaAgent']['primary'],
                   ha='right')
    
    # =============================================
    # Bottom: Marginal gain analysis (decay rate)
    # =============================================
    ax_decay = fig.add_subplot(gs[2, :])
    ax_decay.set_facecolor('#FFFFFF')
    
    x_positions = np.arange(len(topk) - 1)
    bar_width = 0.35
    
    qa_returns = qa_data['Ann. Return'].values
    aa_returns = aa_data['Ann. Return'].values
    
    qa_marginal = np.diff(qa_returns) / qa_returns[:-1] * 100
    aa_marginal = np.diff(aa_returns) / aa_returns[:-1] * 100
    
    x_labels = [f'{topk[i]:.0%}->{topk[i+1]:.0%}' for i in range(len(topk)-1)]
    
    bars1 = ax_decay.bar(x_positions - bar_width/2, qa_marginal, bar_width,
                        label='QuantaAlpha', color=COLORS['QuantaAlpha']['primary'],
                        alpha=0.8, edgecolor='white', linewidth=1.5)
    bars2 = ax_decay.bar(x_positions + bar_width/2, aa_marginal, bar_width,
                        label='AlphaAgent', color=COLORS['AlphaAgent']['primary'],
                        alpha=0.8, edgecolor='white', linewidth=1.5)
    
    for bar, val in zip(bars1, qa_marginal):
        ax_decay.annotate(f'{val:.1f}%', 
                         xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                         xytext=(0, 3), textcoords='offset points',
                         ha='center', va='bottom', fontsize=9, fontweight='bold',
                         color=COLORS['QuantaAlpha']['primary'])
    
    for bar, val in zip(bars2, aa_marginal):
        ax_decay.annotate(f'{val:.1f}%', 
                         xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                         xytext=(0, 3), textcoords='offset points',
                         ha='center', va='bottom', fontsize=9, fontweight='bold',
                         color=COLORS['AlphaAgent']['primary'])
    
    ax_decay.set_xlabel('Top-K Factor Ratio Interval', fontsize=12)
    ax_decay.set_ylabel('Marginal Gain Rate (%)', fontsize=12)
    ax_decay.set_title('Annualized Return Marginal Gain - Factor Expansion Decay Rate Analysis', 
                      fontsize=14, fontweight='bold', pad=15)
    ax_decay.set_xticks(x_positions)
    ax_decay.set_xticklabels(x_labels, fontsize=10)
    ax_decay.legend(loc='upper right', fontsize=11, framealpha=0.9)
    ax_decay.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax_decay.axhline(y=0, color='gray', linestyle='-', linewidth=0.8)
    
    textstr = ('Analysis Notes:\n'
               '* Marginal Gain = (New Return / Original) x 100%\n'
               '* Higher values = more benefit from adding factors\n'
               '* Rapid decline = faster quality decay')
    props = dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.8)
    ax_decay.text(0.02, 0.98, textstr, transform=ax_decay.transAxes, fontsize=9,
                 verticalalignment='top', bbox=props)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"Saved: {save_path}")
    
    return fig


def create_decay_analysis_plot(df, save_path=None):
    """
    Create dedicated decay rate analysis plot
    More intuitive comparison of performance decay between methods
    """
    qa_data = df[df['Method'] == 'QuantaAlpha'].copy()
    aa_data = df[df['Method'] == 'AlphaAgent'].copy()
    topk = qa_data['TopK Ratio'].values
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('#FAFAFA')
    fig.suptitle('Factor Expansion Decay Analysis: QuantaAlpha vs AlphaAgent', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    key_metrics = ['IC', 'Ann. Return', 'ICIR', 'Info Ratio']
    
    for idx, metric in enumerate(key_metrics):
        ax = axes[idx // 2, idx % 2]
        ax.set_facecolor('#FFFFFF')
        
        qa_values = qa_data[metric].values
        aa_values = aa_data[metric].values
        
        qa_norm = qa_values / qa_values[0] * 100
        aa_norm = aa_values / aa_values[0] * 100
        
        line_qa = ax.plot(topk, qa_values, 'o-', linewidth=3, markersize=10,
                         color=COLORS['QuantaAlpha']['primary'], label='QuantaAlpha')
        line_aa = ax.plot(topk, aa_values, 's-', linewidth=3, markersize=10,
                         color=COLORS['AlphaAgent']['primary'], label='AlphaAgent')
        
        ax.fill_between(topk, qa_values, aa_values,
                       where=(qa_values >= aa_values),
                       color=COLORS['QuantaAlpha']['primary'], alpha=0.15)
        
        ax.set_xlabel('Top-K Factor Ratio', fontsize=12)
        ax.set_ylabel(metric, fontsize=12)
        ax.set_title(f'{metric} Comparison', fontsize=14, fontweight='bold', pad=10)
        
        ax2 = ax.twinx()
        ax2.plot(topk, qa_norm, '--', linewidth=1.5, alpha=0.5,
                color=COLORS['QuantaAlpha']['secondary'])
        ax2.plot(topk, aa_norm, '--', linewidth=1.5, alpha=0.5,
                color=COLORS['AlphaAgent']['secondary'])
        ax2.set_ylabel('Growth vs Start (%)', fontsize=10, alpha=0.7)
        ax2.tick_params(axis='y', labelsize=9, colors='gray')
        
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0.1, 1.0)
        
        avg_advantage = np.mean((qa_values - aa_values) / aa_values * 100)
        final_advantage = (qa_values[-1] - aa_values[-1]) / aa_values[-1] * 100
        
        qa_slope = np.polyfit(topk, qa_norm, 1)[0]
        aa_slope = np.polyfit(topk, aa_norm, 1)[0]
        
        info_text = (f'QA Avg Lead: {avg_advantage:+.1f}%\n'
                    f'Final Lead: {final_advantage:+.1f}%\n'
                    f'Growth Slope QA: {qa_slope:.1f}\n'
                    f'Growth Slope AA: {aa_slope:.1f}')
        
        props = dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, edgecolor='gray')
        ax.text(0.98, 0.02, info_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='bottom', horizontalalignment='right', bbox=props)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"Saved: {save_path}")
    
    return fig


def create_summary_dashboard(df, save_path=None):
    """
    Create comprehensive dashboard - all key info in one view
    """
    qa_data = df[df['Method'] == 'QuantaAlpha'].copy()
    aa_data = df[df['Method'] == 'AlphaAgent'].copy()
    topk = qa_data['TopK Ratio'].values
    
    fig = plt.figure(figsize=(20, 12))
    fig.patch.set_facecolor('#1a1a2e')  # Dark background
    
    gs = GridSpec(2, 4, figure=fig, hspace=0.3, wspace=0.3,
                 left=0.05, right=0.95, top=0.90, bottom=0.08)
    
    fig.suptitle('QuantaAlpha vs AlphaAgent: Performance Overview', 
                 fontsize=22, fontweight='bold', color='white', y=0.96)
    
    qa_color = '#FF6B6B'
    aa_color = '#4ECDC4'
    text_color = '#E8E8E8'
    grid_color = '#333355'
    
    def style_ax(ax, title):
        ax.set_facecolor('#16213e')
        ax.set_title(title, fontsize=13, fontweight='bold', color=text_color, pad=10)
        ax.tick_params(colors=text_color)
        ax.spines['bottom'].set_color(grid_color)
        ax.spines['top'].set_color(grid_color)
        ax.spines['left'].set_color(grid_color)
        ax.spines['right'].set_color(grid_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.grid(True, alpha=0.2, color=grid_color, linestyle='--')
    
    # =============================================
    # Top row: 4 key metric comparisons
    # =============================================
    metrics_top = [('IC', 'IC'), ('ICIR', 'ICIR'), ('Ann. Return', 'Ann. Return'), ('Info Ratio', 'Info Ratio')]
    
    for i, (metric, title) in enumerate(metrics_top):
        ax = fig.add_subplot(gs[0, i])
        style_ax(ax, title)
        
        qa_values = qa_data[metric].values
        aa_values = aa_data[metric].values
        
        ax.plot(topk, qa_values, 'o-', linewidth=2.5, markersize=7,
               color=qa_color, label='QuantaAlpha')
        ax.plot(topk, aa_values, 's-', linewidth=2.5, markersize=7,
               color=aa_color, label='AlphaAgent')
        ax.fill_between(topk, qa_values, aa_values,
                       where=(qa_values >= aa_values),
                       color=qa_color, alpha=0.2)
        
        if i == 0:
            ax.legend(loc='lower right', fontsize=9, facecolor='#16213e', 
                     edgecolor='gray', labelcolor=text_color)
        
        ax.set_xlabel('TopK Ratio', fontsize=10)
        ax.set_xlim(0.1, 1.0)
    
    # =============================================
    # Bottom-left: Bar chart - final performance
    # =============================================
    ax_bar = fig.add_subplot(gs[1, 0:2])
    style_ax(ax_bar, 'Final Performance (TopK=93%)')
    
    metrics_bar = ['IC', 'ICIR', 'Rank IC', 'Rank ICIR']
    x = np.arange(len(metrics_bar))
    width = 0.35
    
    qa_final = [qa_data[m].iloc[-1] for m in metrics_bar]
    aa_final = [aa_data[m].iloc[-1] for m in metrics_bar]
    
    bars1 = ax_bar.bar(x - width/2, qa_final, width, label='QuantaAlpha',
                      color=qa_color, alpha=0.85)
    bars2 = ax_bar.bar(x + width/2, aa_final, width, label='AlphaAgent',
                      color=aa_color, alpha=0.85)
    
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(metrics_bar, fontsize=11)
    ax_bar.legend(loc='upper left', fontsize=10, facecolor='#16213e',
                 edgecolor='gray', labelcolor=text_color)
    
    for i, (qa_v, aa_v) in enumerate(zip(qa_final, aa_final)):
        diff_pct = (qa_v - aa_v) / aa_v * 100
        ax_bar.annotate(f'+{diff_pct:.1f}%' if diff_pct > 0 else f'{diff_pct:.1f}%',
                       xy=(i, max(qa_v, aa_v) + 0.02),
                       ha='center', fontsize=9, fontweight='bold',
                       color='#FFD93D')
    
    # =============================================
    # Bottom-right: Risk-Return scatter
    # =============================================
    ax_risk = fig.add_subplot(gs[1, 2:4])
    style_ax(ax_risk, 'Risk-Return Trajectory (Bubble Size = Info Ratio)')
    
    qa_returns = qa_data['Ann. Return'].values
    qa_mdd = np.abs(qa_data['Max DD'].values)
    qa_ir = qa_data['Info Ratio'].values
    
    aa_returns = aa_data['Ann. Return'].values
    aa_mdd = np.abs(aa_data['Max DD'].values)
    aa_ir = aa_data['Info Ratio'].values
    
    ax_risk.plot(qa_mdd, qa_returns, '-', linewidth=2, color=qa_color, alpha=0.5)
    ax_risk.plot(aa_mdd, aa_returns, '-', linewidth=2, color=aa_color, alpha=0.5)
    
    scatter_qa = ax_risk.scatter(qa_mdd, qa_returns, s=qa_ir*80, c=qa_color,
                                alpha=0.7, edgecolors='white', linewidth=1.5,
                                label='QuantaAlpha')
    scatter_aa = ax_risk.scatter(aa_mdd, aa_returns, s=aa_ir*80, c=aa_color,
                                alpha=0.7, edgecolors='white', linewidth=1.5,
                                label='AlphaAgent')
    
    for i, tk in enumerate(topk):
        ax_risk.annotate(f'{tk:.0%}', (qa_mdd[i], qa_returns[i]),
                        textcoords="offset points", xytext=(5, 5),
                        fontsize=8, color=qa_color, alpha=0.8)
        ax_risk.annotate(f'{tk:.0%}', (aa_mdd[i], aa_returns[i]),
                        textcoords="offset points", xytext=(5, -10),
                        fontsize=8, color=aa_color, alpha=0.8)
    
    ax_risk.set_xlabel('Max Drawdown (Absolute)', fontsize=11)
    ax_risk.set_ylabel('Annualized Return', fontsize=11)
    ax_risk.legend(loc='lower right', fontsize=10, facecolor='#16213e',
                  edgecolor='gray', labelcolor=text_color)
    
    ax_risk.text(0.02, 0.98, 'Upper-right is better\n(High Return + Low DD)',
                transform=ax_risk.transAxes, fontsize=9, color='#FFD93D',
                verticalalignment='top', style='italic')
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"Saved: {save_path}")
    
    return fig


def main():
    csv_path = '/home/tjxy/quantagent/AlphaAgent/factor_library/对比.csv'
    df = load_data(csv_path)
    
    print("=" * 60)
    print("QuantaAlpha vs AlphaAgent Visualization Analysis")
    print("=" * 60)
    
    output_dir = '/home/tjxy/quantagent/AlphaAgent/factor_library/'
    
    print("\n[1/5] Generating QuantaAlpha single-method analysis...")
    create_single_method_plot(df, 'QuantaAlpha', 
                             save_path=f'{output_dir}QuantaAlpha_analysis.png')
    
    print("[2/5] Generating AlphaAgent single-method analysis...")
    create_single_method_plot(df, 'AlphaAgent',
                             save_path=f'{output_dir}AlphaAgent_analysis.png')
    
    print("[3/5] Generating comparison plot...")
    create_comparison_plot(df, save_path=f'{output_dir}comparison.png')
    
    print("[4/5] Generating decay rate analysis...")
    create_decay_analysis_plot(df, save_path=f'{output_dir}decay_analysis.png')
    
    print("[5/5] Generating summary dashboard...")
    create_summary_dashboard(df, save_path=f'{output_dir}summary_dashboard.png')
    
    print("\n" + "=" * 60)
    print("All visualizations generated successfully!")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  * {output_dir}QuantaAlpha_analysis.png")
    print(f"  * {output_dir}AlphaAgent_analysis.png")
    print(f"  * {output_dir}comparison.png")
    print(f"  * {output_dir}decay_analysis.png")
    print(f"  * {output_dir}summary_dashboard.png")
    
    plt.show()


if __name__ == '__main__':
    main()
