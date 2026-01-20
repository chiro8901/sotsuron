"""
Steam レビュー数のべき分布分析ツール
CSVファイルから total_reviews を読み込み、べき分布への適合度を分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['MS Gothic', 'Yu Gothic', 'Meiryo']
plt.rcParams['axes.unicode_minus'] = False

# スタイル設定
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300


def load_review_data(csv_path):
    """CSVからレビュー数を読み込み"""
    print(f"📂 読み込み中: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # total_reviews列を抽出
    reviews = df['total_reviews'].dropna()
    
    # 0より大きい値のみ
    reviews = reviews[reviews > 0].astype(int)
    
    print(f"✅ 読み込み完了: {len(df):,} 行")
    print(f"✅ レビューあり: {len(reviews):,} ゲーム ({len(reviews)/len(df)*100:.1f}%)")
    
    return reviews.values


def calculate_power_law_metrics(data):
    """べき分布の各種指標を計算"""
    
    # 降順ソート
    sorted_data = np.sort(data)[::-1]
    n = len(sorted_data)
    
    # ランク付け
    ranks = np.arange(1, n + 1)
    
    # 対数変換
    log_ranks = np.log10(ranks)
    log_values = np.log10(sorted_data)
    
    # 線形回帰 (log-log)
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_ranks, log_values)
    
    alpha = -slope  # べき指数
    r_squared = r_value ** 2
    
    # Gini係数
    sorted_asc = np.sort(data)
    n = len(sorted_asc)
    index = np.arange(1, n + 1)
    gini = (2 * np.sum(index * sorted_asc)) / (n * np.sum(sorted_asc)) - (n + 1) / n
    
    # パレート分析 (上位20%)
    top_20_idx = int(n * 0.2)
    top_20_sum = np.sum(sorted_data[:top_20_idx])
    total_sum = np.sum(sorted_data)
    pareto_ratio = top_20_sum / total_sum
    
    # 上位1%, 5%, 10%の分析
    top_1_sum = np.sum(sorted_data[:max(1, int(n * 0.01))])
    top_5_sum = np.sum(sorted_data[:max(1, int(n * 0.05))])
    top_10_sum = np.sum(sorted_data[:max(1, int(n * 0.10))])
    
    return {
        'alpha': alpha,
        'r_squared': r_squared,
        'gini': gini,
        'pareto_20': pareto_ratio,
        'top_1_pct': top_1_sum / total_sum,
        'top_5_pct': top_5_sum / total_sum,
        'top_10_pct': top_10_sum / total_sum,
        'slope': slope,
        'intercept': intercept,
        'p_value': p_value
    }


def create_analysis_plots(data, metrics, output_path):
    """分析グラフを作成"""
    
    fig = plt.figure(figsize=(16, 12))
    
    sorted_data = np.sort(data)[::-1]
    ranks = np.arange(1, len(sorted_data) + 1)
    
    # 1. 基本分布（ヒストグラム）
    ax1 = plt.subplot(3, 3, 1)
    plt.hist(data, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
    plt.xlabel('レビュー数', fontsize=11)
    plt.ylabel('ゲーム数', fontsize=11)
    plt.title('レビュー数の分布', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # 2. 対数スケールヒストグラム
    ax2 = plt.subplot(3, 3, 2)
    plt.hist(data, bins=50, edgecolor='black', alpha=0.7, color='coral')
    plt.xlabel('レビュー数 (log)', fontsize=11)
    plt.ylabel('ゲーム数 (log)', fontsize=11)
    plt.xscale('log')
    plt.yscale('log')
    plt.title('対数スケール分布', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # 3. ランク-レビュー数プロット (log-log)
    ax3 = plt.subplot(3, 3, 3)
    plt.scatter(ranks, sorted_data, s=10, alpha=0.5, color='darkgreen')
    
    # 回帰直線
    log_ranks = np.log10(ranks)
    log_predicted = metrics['slope'] * log_ranks + metrics['intercept']
    predicted = 10 ** log_predicted
    plt.plot(ranks, predicted, 'r-', linewidth=2, 
             label=f'べき法則フィット\nα={metrics["alpha"]:.3f}\nR²={metrics["r_squared"]:.4f}')
    
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('ランク (log)', fontsize=11)
    plt.ylabel('レビュー数 (log)', fontsize=11)
    plt.title('ランク-レビュー数プロット (log-log)', fontsize=12, fontweight='bold')
    plt.legend(fontsize=9)
    plt.grid(True, alpha=0.3)
    
    # 4. 累積分布関数 (CCDF)
    ax4 = plt.subplot(3, 3, 4)
    unique_values = np.unique(sorted_data)
    ccdf = np.array([np.sum(data >= val) / len(data) for val in unique_values])
    
    plt.scatter(unique_values, ccdf, s=10, alpha=0.5, color='purple')
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('レビュー数 (log)', fontsize=11)
    plt.ylabel('P(X ≥ x)', fontsize=11)
    plt.title('相補累積分布関数 (CCDF)', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # 5. ローレンツ曲線
    ax5 = plt.subplot(3, 3, 5)
    sorted_asc = np.sort(data)
    cumsum = np.cumsum(sorted_asc)
    cumsum_norm = cumsum / cumsum[-1]
    x = np.linspace(0, 1, len(cumsum_norm))
    
    plt.plot(x, cumsum_norm, linewidth=2, color='darkblue', label='ローレンツ曲線')
    plt.plot([0, 1], [0, 1], 'k--', linewidth=1, label='完全平等線')
    
    plt.fill_between(x, cumsum_norm, x, alpha=0.3, color='skyblue')
    plt.xlabel('累積ゲーム割合', fontsize=11)
    plt.ylabel('累積レビュー割合', fontsize=11)
    plt.title(f'ローレンツ曲線 (Gini={metrics["gini"]:.4f})', fontsize=12, fontweight='bold')
    plt.legend(fontsize=9)
    plt.grid(True, alpha=0.3)
    
    # 6. Q-Qプロット
    ax6 = plt.subplot(3, 3, 6)
    log_data = np.log10(sorted_data)
    theoretical_quantiles = np.linspace(log_data.min(), log_data.max(), len(log_data))
    
    plt.scatter(theoretical_quantiles, log_data, s=10, alpha=0.5, color='orange')
    plt.plot([log_data.min(), log_data.max()], 
             [log_data.min(), log_data.max()], 
             'r--', linewidth=2, label='理論直線')
    
    plt.xlabel('理論分位点 (log)', fontsize=11)
    plt.ylabel('実測分位点 (log)', fontsize=11)
    plt.title('Q-Qプロット (べき分布)', fontsize=12, fontweight='bold')
    plt.legend(fontsize=9)
    plt.grid(True, alpha=0.3)
    
    # 7. 上位ゲームの集中度
    ax7 = plt.subplot(3, 3, 7)
    percentages = [1, 5, 10, 20, 50]
    contributions = [
        metrics['top_1_pct'] * 100,
        metrics['top_5_pct'] * 100,
        metrics['top_10_pct'] * 100,
        metrics['pareto_20'] * 100,
        np.sum(sorted_data[:int(len(data)*0.5)]) / np.sum(data) * 100
    ]
    
    bars = plt.bar(range(len(percentages)), contributions, 
                   color=['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd'],
                   edgecolor='black', linewidth=1.5)
    plt.xticks(range(len(percentages)), [f'上位{p}%' for p in percentages])
    plt.ylabel('総レビュー数に占める割合 (%)', fontsize=11)
    plt.title('レビュー数の集中度', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    
    # 値をバーの上に表示
    for bar, val in zip(bars, contributions):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 8. 残差プロット
    ax8 = plt.subplot(3, 3, 8)
    log_ranks = np.log10(ranks)
    log_values = np.log10(sorted_data)
    predicted_log = metrics['slope'] * log_ranks + metrics['intercept']
    residuals = log_values - predicted_log
    
    plt.scatter(log_ranks, residuals, s=10, alpha=0.5, color='brown')
    plt.axhline(y=0, color='r', linestyle='--', linewidth=2)
    plt.xlabel('log(ランク)', fontsize=11)
    plt.ylabel('残差', fontsize=11)
    plt.title('残差プロット', fontsize=12, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # 9. 統計サマリー
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')
    
    summary_text = f"""
【べき分布分析結果】

べき指数 (α):     {metrics['alpha']:.3f}
決定係数 (R²):    {metrics['r_squared']:.4f}
Gini係数:         {metrics['gini']:.4f}

【集中度】
上位  1%:  {metrics['top_1_pct']*100:>5.1f}%
上位  5%:  {metrics['top_5_pct']*100:>5.1f}%
上位 10%:  {metrics['top_10_pct']*100:>5.1f}%
上位 20%:  {metrics['pareto_20']*100:>5.1f}%

【基本統計】
データ数:  {len(data):>10,}
最大値:    {np.max(data):>10,}
平均値:    {np.mean(data):>10,.1f}
中央値:    {np.median(data):>10,.0f}
合計:      {np.sum(data):>10,}
    """
    
    plt.text(0.1, 0.9, summary_text, transform=ax9.transAxes,
             fontsize=10, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Steamレビュー数のべき分布分析', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"📊 グラフ保存: {output_path}")
    
    return fig


def evaluate_power_law(metrics):
    """べき分布への適合度を評価"""
    
    print("\n" + "="*70)
    print("📈 べき分布適合度の評価")
    print("="*70)
    
    score = 0
    max_score = 5
    
    # 1. R²の評価
    print(f"\n1️⃣  決定係数 (R²): {metrics['r_squared']:.4f}")
    if metrics['r_squared'] > 0.95:
        print("   ✅ 非常に良好な適合 (R² > 0.95)")
        score += 1
    elif metrics['r_squared'] > 0.90:
        print("   ✅ 良好な適合 (R² > 0.90)")
        score += 0.8
    elif metrics['r_squared'] > 0.80:
        print("   ⚠️  やや弱い適合 (R² > 0.80)")
        score += 0.5
    else:
        print("   ❌ 適合が弱い")
    
    # 2. αの範囲
    print(f"\n2️⃣  べき指数 (α): {metrics['alpha']:.3f}")
    if 1.0 < metrics['alpha'] < 3.0:
        print("   ✅ 典型的なべき分布の範囲 (1 < α < 3)")
        score += 1
    elif 0.5 < metrics['alpha'] <= 1.0:
        print("   ⚠️  極端な不平等 (α ≤ 1)")
        score += 0.7
    elif 3.0 <= metrics['alpha'] < 4.0:
        print("   ⚠️  やや均等寄り (α ≥ 3)")
        score += 0.5
    else:
        print("   ❌ 典型的な範囲外")
    
    # 3. Gini係数
    print(f"\n3️⃣  Gini係数: {metrics['gini']:.4f}")
    if metrics['gini'] > 0.8:
        print("   ✅ 極端な不平等 (べき分布的)")
        score += 1
    elif metrics['gini'] > 0.6:
        print("   ✅ 高い不平等")
        score += 0.7
    else:
        print("   ⚠️  やや均等")
        score += 0.3
    
    # 4. パレート分析
    print(f"\n4️⃣  パレート分析 (上位20%): {metrics['pareto_20']*100:.1f}%")
    if metrics['pareto_20'] > 0.8:
        print("   ✅ パレートの法則を大きく超える (>80%)")
        score += 1
    elif metrics['pareto_20'] > 0.7:
        print("   ✅ パレートの法則に近い")
        score += 0.8
    else:
        print("   ⚠️  パレートの法則ほど極端ではない")
        score += 0.5
    
    # 5. 集中度の極端さ
    print(f"\n5️⃣  上位1%の集中度: {metrics['top_1_pct']*100:.1f}%")
    if metrics['top_1_pct'] > 0.5:
        print("   ✅ 極端な集中 (>50%)")
        score += 1
    elif metrics['top_1_pct'] > 0.3:
        print("   ✅ 高い集中")
        score += 0.7
    else:
        print("   ⚠️  やや分散")
        score += 0.3
    
    # 総合評価
    print("\n" + "="*70)
    print(f"📊 総合スコア: {score:.1f} / {max_score}")
    print("="*70)
    
    if score >= 4.5:
        print("✅ 結論: レビュー数は非常に強いべき分布に従っています")
    elif score >= 3.5:
        print("✅ 結論: レビュー数は明確なべき分布に従っています")
    elif score >= 2.5:
        print("⚠️  結論: レビュー数はべき分布的な傾向がありますが、やや弱いです")
    else:
        print("❌ 結論: レビュー数はべき分布に従っているとは言えません")
    
    print("="*70)


def main():
    """メイン実行"""
    
    # CSVファイルパス
    csv_file = Path(__file__).parent.parent / 'data' / 'steam_simple_49847_20260118_182744.csv'
    
    if not csv_file.exists():
        print(f"❌ ファイルが見つかりません: {csv_file}")
        return
    
    print("="*70)
    print("🎮 Steam レビュー数べき分布分析")
    print("="*70)
    
    # データ読み込み
    reviews = load_review_data(csv_file)
    
    if len(reviews) == 0:
        print("❌ レビューデータがありません")
        return
    
    # 基本統計
    print("\n📊 基本統計:")
    print(f"  レビューありゲーム数: {len(reviews):,}")
    print(f"  最大レビュー数:       {np.max(reviews):,}")
    print(f"  最小レビュー数:       {np.min(reviews):,}")
    print(f"  平均レビュー数:       {np.mean(reviews):,.1f}")
    print(f"  中央値:               {np.median(reviews):,.0f}")
    print(f"  総レビュー数:         {np.sum(reviews):,}")
    
    # べき分布分析
    print("\n🔍 べき分布分析を実行中...")
    metrics = calculate_power_law_metrics(reviews)
    
    # グラフ作成
    output_path = Path(__file__).parent.parent / 'review_power_law_analysis.png'
    create_analysis_plots(reviews, metrics, output_path)
    
    # 評価
    evaluate_power_law(metrics)
    
    print(f"\n✅ 分析完了！")
    print(f"📊 グラフ: {output_path}")


if __name__ == "__main__":
    main()
