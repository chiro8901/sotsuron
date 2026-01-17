# Steam Data Collection Project Makefile

.PHONY: clean clean-checkpoints clean-logs clean-all help

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  make clean              - チェックポイントファイルをすべて削除"
	@echo "  make clean-checkpoints  - チェックポイントファイルのみ削除"
	@echo "  make clean-logs         - ログファイルを削除"
	@echo "  make clean-all          - すべての中間ファイルを削除"
	@echo "  make help               - このヘルプを表示"

# チェックポイントファイルを削除
clean: clean-checkpoints
	@echo "✅ クリーンアップ完了"

# チェックポイントファイルのみ削除
clean-checkpoints:
	@echo "🗑️  チェックポイントファイルを削除中..."
	@powershell -Command "if (Test-Path '*checkpoint*.json') { Remove-Item '*checkpoint*.json' -Verbose } else { Write-Host '削除するチェックポイントファイルが見つかりません' }"
	@powershell -Command "if (Test-Path '*processed_ids.json') { Remove-Item '*processed_ids.json' -Verbose } else { Write-Host '削除する処理済みIDファイルが見つかりません' }"

# ログファイルを削除
clean-logs:
	@echo "🗑️  ログファイルを削除中..."
	@powershell -Command "if (Test-Path '*.log') { Remove-Item '*.log' -Verbose } else { Write-Host '削除するログファイルが見つかりません' }"

# すべての中間ファイルを削除（データファイルは保持）
clean-all: clean-checkpoints clean-logs
	@echo "🗑️  すべての中間ファイルを削除しました"
	@echo "⚠️  注意: .csv, .json, .xlsx などのデータファイルは保持されています"

# データファイルも含めてすべて削除（危険！）
clean-dangerous:
	@echo "⚠️  警告: すべてのデータファイルを削除します！"
	@powershell -Command "$$confirm = Read-Host '本当に削除しますか？ (yes/no)'; if ($$confirm -eq 'yes') { Remove-Item '*.json', '*.csv', '*.xlsx', '*.log', '*.png' -Verbose } else { Write-Host 'キャンセルしました' }"

# 統計情報表示
stats:
	@echo "📊 ファイル統計:"
	@powershell -Command "$$checkpoints = (Get-ChildItem '*checkpoint*.json' -ErrorAction SilentlyContinue).Count; Write-Host \"  チェックポイントファイル: $$checkpoints 個\""
	@powershell -Command "$$processed = (Get-ChildItem '*processed_ids.json' -ErrorAction SilentlyContinue).Count; Write-Host \"  処理済みIDファイル: $$processed 個\""
	@powershell -Command "$$logs = (Get-ChildItem '*.log' -ErrorAction SilentlyContinue).Count; Write-Host \"  ログファイル: $$logs 個\""
	@powershell -Command "$$csv = (Get-ChildItem '*.csv' -ErrorAction SilentlyContinue).Count; Write-Host \"  CSVファイル: $$csv 個\""
	@powershell -Command "$$json = (Get-ChildItem 'steam_*.json' -Exclude '*checkpoint*', '*processed*' -ErrorAction SilentlyContinue).Count; Write-Host \"  データJSONファイル: $$json 個\""
