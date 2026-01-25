import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# 日本語フォント設定（Windowsの場合）
plt.rcParams['font.family'] = 'MS Gothic'
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け対策

# データ読み込み
csv_file = r'c:\Users\chiro\titech\sotsuron\steam_random_50000_20260116_211133.csv'
print(f"📂 データ読み込み中: {csv_file}")
df = pd.read_csv(csv_file)

print(f"✅ {len(df)}件のデータを読み込みました\n")

# player_countの基本統計
print("="*70)
print("📊 プレイヤー数の基本統計")
print("="*70)

# NaNと0を除外したデータ
player_counts = df['player_count'].dropna()
player_counts_non_zero = player_counts[player_counts > 0]

print(f"総ゲーム数:              {len(df):,}")
print(f"プレイヤー数データあり:  {len(player_counts):,}")
print(f"プレイヤー数 > 0:        {len(player_counts_non_zero):,}")
print(f"プレイヤー数 = 0 or NaN: {len(df) - len(player_counts_non_zero):,}")

if len(player_counts_non_zero) > 0:
    print(f"\n【プレイヤー数 > 0 のゲームの統計】")
    print(f"合計:    {player_counts_non_zero.sum():,.0f} 人")
    print(f"平均:    {player_counts_non_zero.mean():,.2f} 人")
    print(f"中央値:  {player_counts_non_zero.median():,.0f} 人")
    print(f"最大:    {player_counts_non_zero.max():,.0f} 人")
    print(f"最小:    {player_counts_non_zero.min():,.0f} 人")
    print(f"標準偏差: {player_counts_non_zero.std():,.2f}")

print("="*70)

# TOP 10表示
print("\n🏆 プレイヤー数 TOP 10")
print("="*70)
top_10 = df.nlargest(10, 'player_count')[['app_id', 'player_count']]
for i, (idx, row) in enumerate(top_10.iterrows(), 1):
    print(f"{i:2d}. AppID {int(row['app_id']):8d}: {int(row['player_count']):10,} 人")
print("="*70)

# ヒストグラム作成
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Steam ゲーム プレイヤー数分布分析', fontsize=16, fontweight='bold')

# 1. 全データ（0含む）のヒストグラム
ax1 = axes[0, 0]
ax1.hist(player_counts.fillna(0), bins=50, color='skyblue', edgecolor='black', alpha=0.7)
ax1.set_xlabel('プレイヤー数', fontsize=12)
ax1.set_ylabel('ゲーム数', fontsize=12)
ax1.set_title('プレイヤー数の分布（全データ）', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.text(0.95, 0.95, f'N = {len(player_counts):,}', 
         transform=ax1.transAxes, ha='right', va='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 2. プレイヤー数 > 0 のヒストグラム（対数スケール）
ax2 = axes[0, 1]
if len(player_counts_non_zero) > 0:
    ax2.hist(player_counts_non_zero, bins=50, color='coral', edgecolor='black', alpha=0.7)
    ax2.set_xlabel('プレイヤー数', fontsize=12)
    ax2.set_ylabel('ゲーム数', fontsize=12)
    ax2.set_title('プレイヤー数の分布（> 0、対数スケール）', fontsize=14, fontweight='bold')
    ax2.set_yscale('log')
    ax2.grid(True, alpha=0.3)
    ax2.text(0.95, 0.95, f'N = {len(player_counts_non_zero):,}', 
             transform=ax2.transAxes, ha='right', va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 3. プレイヤー数の対数変換ヒストグラム
ax3 = axes[1, 0]
if len(player_counts_non_zero) > 0:
    log_counts = np.log10(player_counts_non_zero + 1)  # +1してlog(0)を回避
    ax3.hist(log_counts, bins=50, color='lightgreen', edgecolor='black', alpha=0.7)
    ax3.set_xlabel('log10(プレイヤー数 + 1)', fontsize=12)
    ax3.set_ylabel('ゲーム数', fontsize=12)
    ax3.set_title('プレイヤー数の対数分布', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.text(0.95, 0.95, f'N = {len(player_counts_non_zero):,}', 
             transform=ax3.transAxes, ha='right', va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 4. 累積分布関数（CDF）
ax4 = axes[1, 1]
if len(player_counts_non_zero) > 0:
    sorted_counts = np.sort(player_counts_non_zero)
    cumulative = np.arange(1, len(sorted_counts) + 1) / len(sorted_counts) * 100
    ax4.plot(sorted_counts, cumulative, color='purple', linewidth=2)
    ax4.set_xlabel('プレイヤー数', fontsize=12)
    ax4.set_ylabel('累積割合 (%)', fontsize=12)
    ax4.set_title('プレイヤー数の累積分布関数（CDF）', fontsize=14, fontweight='bold')
    ax4.set_xscale('log')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50%')
    ax4.axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='90%')
    ax4.legend()
    
    # 中央値と90パーセンタイルを表示
    median_val = player_counts_non_zero.median()
    p90_val = player_counts_non_zero.quantile(0.9)
    ax4.text(0.05, 0.95, f'中央値: {median_val:,.0f}\n90%: {p90_val:,.0f}', 
             transform=ax4.transAxes, ha='left', va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()

# 保存
output_file = 'player_count_histogram.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n💾 ヒストグラムを保存しました: {output_file}")

# 表示
plt.show()

print("\n✨ 分析完了！")
