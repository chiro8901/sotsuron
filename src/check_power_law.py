import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import seaborn as sns

# 日本語フォント設定
plt.rcParams['font.family'] = 'MS Gothic'
plt.rcParams['axes.unicode_minus'] = False

# データ読み込み
csv_file = r'C:\Users\chiro\titech\sotsuron\data\steam_random_10000_20260115_150016.csv'
print(f"📂 データ読み込み中: {csv_file}")
df = pd.read_csv(csv_file)

# プレイヤー数 > 0 のデータを抽出
player_counts = df['player_count'].dropna()
player_counts_non_zero = player_counts[player_counts > 0].values

print(f"\n{'='*70}")
print(f"📊 べき分布（パレート分布）の検証")
print(f"{'='*70}")
print(f"分析対象: {len(player_counts_non_zero):,}ゲーム（プレイヤー数 > 0）\n")

# 1. 基本統計
print("【基本統計】")
print(f"平均:     {np.mean(player_counts_non_zero):,.2f}")
print(f"中央値:   {np.median(player_counts_non_zero):,.2f}")
print(f"最大値:   {np.max(player_counts_non_zero):,}")
print(f"最小値:   {np.min(player_counts_non_zero):,}")
print(f"標準偏差: {np.std(player_counts_non_zero):,.2f}")

# 平均/中央値比（べき分布では大きくなる）
mean_median_ratio = np.mean(player_counts_non_zero) / np.median(player_counts_non_zero)
print(f"\n平均/中央値比: {mean_median_ratio:.2f}")
if mean_median_ratio > 2:
    print("→ ロングテール分布の特徴あり（べき分布の可能性高）")
else:
    print("→ 比較的対称的な分布")

# 2. 対数-対数プロットでの直線性チェック
print(f"\n{'='*70}")
print("【べき分布の特徴】")
print(f"{'='*70}")

# データをソートして累積分布を作成
sorted_counts = np.sort(player_counts_non_zero)[::-1]  # 降順
ranks = np.arange(1, len(sorted_counts) + 1)

# ランク vs 値の対数-対数プロット用の傾き計算
log_ranks = np.log10(ranks)
log_counts = np.log10(sorted_counts)

# 線形回帰で傾きを推定
slope, intercept, r_value, p_value, std_err = stats.linregress(log_ranks, log_counts)

print(f"対数-対数プロットの傾き（べき指数α）: {-slope:.3f}")
print(f"決定係数 R²: {r_value**2:.4f}")
print(f"p値: {p_value:.4e}")

if r_value**2 > 0.8:
    print("→ 強い線形関係あり（べき分布の可能性が高い）")
elif r_value**2 > 0.6:
    print("→ 中程度の線形関係あり（部分的にべき分布の特徴）")
else:
    print("→ 線形関係が弱い（べき分布に従わない可能性）")

# べき指数の解釈
print(f"\nべき指数 α = {-slope:.3f} の解釈:")
if -slope < 1:
    print("→ α < 1: 極端な不均等（少数が大多数を占める）")
elif -slope < 2:
    print("→ 1 < α < 2: 典型的なべき分布（パレートの法則に近い）")
elif -slope < 3:
    print("→ 2 < α < 3: 中程度の不均等")
else:
    print("→ α > 3: 比較的均等な分布")

# 3. ジニ係数計算（不平等度の指標）
sorted_values = np.sort(player_counts_non_zero)
n = len(sorted_values)
cumsum = np.cumsum(sorted_values)
gini = (2 * np.sum((np.arange(1, n+1)) * sorted_values)) / (n * np.sum(sorted_values)) - (n + 1) / n

print(f"\n【ジニ係数】: {gini:.4f}")
if gini > 0.6:
    print("→ 非常に不平等な分布（べき分布の特徴）")
elif gini > 0.4:
    print("→ 中程度の不平等")
else:
    print("→ 比較的平等な分布")

# 4. 上位20%が占める割合（パレートの法則: 80/20ルール）
sorted_desc = np.sort(player_counts_non_zero)[::-1]
top_20_percent_count = int(len(sorted_desc) * 0.2)
top_20_percent_sum = np.sum(sorted_desc[:top_20_percent_count])
total_sum = np.sum(sorted_desc)
top_20_ratio = top_20_percent_sum / total_sum

print(f"\n【パレートの法則チェック】")
print(f"上位20%のゲームが占める割合: {top_20_ratio*100:.1f}%")
if top_20_ratio > 0.8:
    print("→ 80/20ルールに従う（典型的なべき分布）")
elif top_20_ratio > 0.6:
    print("→ パレート分布の傾向あり")
else:
    print("→ パレート分布とは異なる")

# 上位1%, 5%, 10%も確認
for pct in [1, 5, 10]:
    top_n = int(len(sorted_desc) * pct / 100)
    top_sum = np.sum(sorted_desc[:top_n])
    ratio = top_sum / total_sum
    print(f"上位{pct:2d}%のゲームが占める割合: {ratio*100:.1f}%")

# 5. 可視化
fig = plt.figure(figsize=(18, 12))

# サブプロット1: 対数-対数プロット（ランク vs 値）
ax1 = plt.subplot(2, 3, 1)
ax1.scatter(ranks, sorted_counts, alpha=0.5, s=20, label='実データ')
# フィット線
fit_line = 10**(intercept + slope * log_ranks)
ax1.plot(ranks, fit_line, 'r-', linewidth=2, 
         label=f'べき分布フィット\nα = {-slope:.3f}\nR² = {r_value**2:.3f}')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_xlabel('ランク（順位）', fontsize=12)
ax1.set_ylabel('プレイヤー数', fontsize=12)
ax1.set_title('ランク-サイズ分布（対数-対数プロット）', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend()

# サブプロット2: 累積分布関数（CCDF）
ax2 = plt.subplot(2, 3, 2)
unique_values = np.unique(player_counts_non_zero)
ccdf = np.array([np.sum(player_counts_non_zero >= val) / len(player_counts_non_zero) 
                 for val in unique_values])
ax2.scatter(unique_values, ccdf, alpha=0.5, s=20)
ax2.set_xscale('log')
ax2.set_yscale('log')
ax2.set_xlabel('プレイヤー数', fontsize=12)
ax2.set_ylabel('P(X ≥ x)', fontsize=12)
ax2.set_title('相補累積分布関数（CCDF）', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)

# サブプロット3: ヒストグラム（対数ビン）
ax3 = plt.subplot(2, 3, 3)
bins = np.logspace(np.log10(1), np.log10(max(player_counts_non_zero)), 50)
ax3.hist(player_counts_non_zero, bins=bins, alpha=0.7, edgecolor='black')
ax3.set_xscale('log')
ax3.set_xlabel('プレイヤー数（対数スケール）', fontsize=12)
ax3.set_ylabel('ゲーム数', fontsize=12)
ax3.set_title('プレイヤー数分布（対数ビン）', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3)

# サブプロット4: ローレンツ曲線
ax4 = plt.subplot(2, 3, 4)
sorted_values = np.sort(player_counts_non_zero)
cumsum_values = np.cumsum(sorted_values)
lorenz = cumsum_values / cumsum_values[-1]
population = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
ax4.plot(population, lorenz, linewidth=2, label=f'ローレンツ曲線\nジニ係数={gini:.3f}')
ax4.plot([0, 1], [0, 1], 'k--', linewidth=1, label='完全平等線')
ax4.fill_between(population, lorenz, population, alpha=0.3)
ax4.set_xlabel('ゲームの累積割合', fontsize=12)
ax4.set_ylabel('プレイヤー数の累積割合', fontsize=12)
ax4.set_title('ローレンツ曲線（不平等度の可視化）', fontsize=14, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)

# サブプロット5: 上位集中度
ax5 = plt.subplot(2, 3, 5)
percentiles = np.arange(1, 101)
concentration = []
for p in percentiles:
    top_n = int(len(sorted_desc) * p / 100)
    if top_n == 0:
        top_n = 1
    ratio = np.sum(sorted_desc[:top_n]) / total_sum
    concentration.append(ratio * 100)

ax5.plot(percentiles, concentration, linewidth=2, color='green')
ax5.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='80%ライン')
ax5.axvline(x=20, color='red', linestyle='--', alpha=0.5, label='20%ライン')
ax5.scatter([20], [top_20_ratio*100], s=200, c='red', zorder=5, 
            label=f'上位20%: {top_20_ratio*100:.1f}%')
ax5.set_xlabel('上位ゲームの割合 (%)', fontsize=12)
ax5.set_ylabel('プレイヤー数の占有率 (%)', fontsize=12)
ax5.set_title('上位集中度（パレート分析）', fontsize=14, fontweight='bold')
ax5.legend()
ax5.grid(True, alpha=0.3)

# サブプロット6: Q-Qプロット（べき分布との比較）
ax6 = plt.subplot(2, 3, 6)
# パレート分布のシミュレーション
alpha_est = -slope
x_min = np.min(player_counts_non_zero)
theoretical = stats.pareto.rvs(alpha_est, scale=x_min, size=len(player_counts_non_zero))
stats.probplot(player_counts_non_zero, dist=stats.pareto(alpha_est, scale=x_min), plot=ax6)
ax6.set_title('Q-Qプロット（パレート分布）', fontsize=14, fontweight='bold')
ax6.set_xlabel('理論分位点', fontsize=12)
ax6.set_ylabel('サンプル分位点', fontsize=12)
ax6.grid(True, alpha=0.3)

plt.tight_layout()

# 保存
output_file = 'power_law_analysis.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n{'='*70}")
print(f"💾 べき分布分析グラフを保存: {output_file}")
print(f"{'='*70}")

plt.show()

# 結論
print(f"\n{'='*70}")
print("【総合判定】")
print(f"{'='*70}")

evidence_count = 0
total_tests = 5

# 判定基準
if r_value**2 > 0.7:
    print("✅ 対数-対数プロットで強い線形性")
    evidence_count += 1
else:
    print("❌ 対数-対数プロットの線形性が弱い")

if gini > 0.5:
    print("✅ 高いジニ係数（不平等分布）")
    evidence_count += 1
else:
    print("❌ ジニ係数が低い")

if top_20_ratio > 0.7:
    print("✅ 上位20%が70%以上を占める")
    evidence_count += 1
else:
    print("❌ 上位集中度が低い")

if mean_median_ratio > 3:
    print("✅ 平均/中央値比が大きい（ロングテール）")
    evidence_count += 1
else:
    print("❌ 平均/中央値比が小さい")

if 1 < -slope < 3:
    print("✅ べき指数が典型的な範囲内")
    evidence_count += 1
else:
    print("❌ べき指数が典型的な範囲外")

print(f"\nべき分布の証拠: {evidence_count}/{total_tests}")

if evidence_count >= 4:
    print("\n🎯 結論: このデータは **べき分布（パレート分布）に従っている可能性が非常に高い** です。")
    print("   Steamゲームのプレイヤー数は典型的なロングテール分布を示しています。")
elif evidence_count >= 3:
    print("\n🎯 結論: このデータは **べき分布に近い特性を持っている** と考えられます。")
    print("   一部の人気ゲームが大多数のプレイヤーを集める傾向があります。")
else:
    print("\n🎯 結論: このデータは **べき分布とは異なる分布** の可能性があります。")

print(f"{'='*70}\n")
