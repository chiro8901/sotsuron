"""
ベタ打ちデータからべき指数を計算するシンプルツール
使い方: データを貼り付けて Enter → 空行で Enter → 結果表示
"""

import numpy as np
from scipy import stats
import sys


def calculate_power_law(data):
    """べき指数とR²を計算"""
    # 0を除外してソート
    data = np.array([x for x in data if x > 0])
    
    if len(data) == 0:
        return None, None, None
    
    # 降順ソート
    sorted_data = np.sort(data)[::-1]
    
    # ランクを付与 (1から始まる)
    ranks = np.arange(1, len(sorted_data) + 1)
    
    # 対数変換
    log_ranks = np.log10(ranks)
    log_values = np.log10(sorted_data)
    
    # 線形回帰 (log-log空間)
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_ranks, log_values)
    
    # べき指数α = -slope
    alpha = -slope
    r_squared = r_value ** 2
    
    return alpha, r_squared, len(data)


def main():
    print("=" * 70)
    print("📊 べき指数計算ツール")
    print("=" * 70)
    print("\n使い方:")
    print("  1. データを1行に1つずつ貼り付けてください")
    print("  2. 貼り付け終わったら空行(Enter)を押してください")
    print("  3. べき指数(α)とR²が表示されます")
    print("\n例:")
    print("  18024")
    print("  5432")
    print("  1234")
    print("  ...")
    print("  (空行)")
    print("=" * 70)
    print("\nデータを入力してください (終了は空行):\n")
    
    data = []
    line_count = 0
    
    while True:
        try:
            line = input().strip()
            
            # 空行で終了
            if not line:
                break
            
            # 数値に変換
            try:
                value = float(line)
                data.append(value)
                line_count += 1
                
                # 10個ごとに進捗表示
                if line_count % 10 == 0:
                    print(f"  → {line_count}個入力済み...", file=sys.stderr)
                
            except ValueError:
                print(f"⚠️  警告: '{line}' は数値ではありません (スキップ)", file=sys.stderr)
                continue
                
        except EOFError:
            # Ctrl+D または Ctrl+Z で終了
            break
    
    print(f"\n📥 入力完了: {len(data)}個のデータ")
    
    if len(data) == 0:
        print("❌ データがありません")
        return
    
    # べき指数を計算
    alpha, r_squared, valid_count = calculate_power_law(data)
    
    if alpha is None:
        print("❌ 計算できませんでした (正の値がありません)")
        return
    
    # 結果表示
    print("\n" + "=" * 70)
    print("📈 分析結果")
    print("=" * 70)
    print(f"総データ数:        {len(data):>10,}")
    print(f"有効データ数:      {valid_count:>10,} (> 0)")
    print(f"べき指数 (α):      {alpha:>10.3f}")
    print(f"決定係数 (R²):     {r_squared:>10.4f}")
    print("=" * 70)
    
    # 評価コメント
    print("\n💡 評価:")
    
    # R²の評価
    if r_squared > 0.95:
        print(f"  ✅ R²={r_squared:.4f} → 非常に良好なべき分布の適合")
    elif r_squared > 0.90:
        print(f"  ✅ R²={r_squared:.4f} → 良好なべき分布の適合")
    elif r_squared > 0.80:
        print(f"  ⚠️  R²={r_squared:.4f} → やや弱いべき分布の適合")
    else:
        print(f"  ❌ R²={r_squared:.4f} → べき分布への適合が弱い")
    
    # αの評価
    if 1.0 < alpha < 3.0:
        print(f"  ✅ α={alpha:.3f} → 典型的なべき分布の範囲 (1 < α < 3)")
    elif alpha <= 1.0:
        print(f"  ⚠️  α={alpha:.3f} → 極端な不平等 (α ≤ 1)")
    else:
        print(f"  ⚠️  α={alpha:.3f} → やや均等寄り (α > 3)")
    
    # 基本統計も表示
    positive_data = [x for x in data if x > 0]
    if positive_data:
        print("\n📊 基本統計:")
        print(f"  最大値:     {max(positive_data):>15,.0f}")
        print(f"  最小値:     {min(positive_data):>15,.0f}")
        print(f"  平均値:     {np.mean(positive_data):>15,.1f}")
        print(f"  中央値:     {np.median(positive_data):>15,.0f}")
        print(f"  合計:       {sum(positive_data):>15,.0f}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  中断されました")
        sys.exit(0)
