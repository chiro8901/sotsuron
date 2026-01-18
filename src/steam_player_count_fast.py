import requests
import json
import time
import random
import os
from datetime import datetime
import pandas as pd
import logging
from typing import List, Dict, Optional

# API Key（https://steamcommunity.com/dev/apikey で取得）
STEAM_API_KEY = "942710D8C9D88DF9C28ED5E25B03CFED"

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('steam_player_count_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SteamPlayerCountCollector:
    """Steam APIからプレイヤー数のみを高速収集"""
    
    def __init__(self, api_key=None, delay=0.3, timeout=10, checkpoint_interval=500):
        """
        Args:
            delay: API呼び出し間隔（秒） - プレイヤー数APIは制限が緩いため短く設定
            timeout: リクエストタイムアウト（秒）
            checkpoint_interval: 何件ごとに中間保存するか
        """
        self.delay = delay
        self.api_key = api_key
        self.timeout = timeout
        self.checkpoint_interval = checkpoint_interval
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 統計情報
        self.stats = {
            'total_requested': 0,
            'successful': 0,
            'failed': 0,
            'with_players': 0,
            'start_time': None,
            'end_time': None
        }
    
    def get_all_app_ids(self) -> List[int]:
        """Steam上の全アプリケーションIDを取得"""
        logger.info("📥 全アプリケーションリストを取得中...")
        
        # APIキーがある場合は新しいIStoreServiceを使用
        if self.api_key:
            return self._get_app_ids_via_store_service()
            
        # 従来のAPIを試行
        try:
            logger.info("ℹ️ APIキー未指定: 旧API(ISteamApps)を試行します...")
            url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            apps = data['applist']['apps']
            app_ids = [app['appid'] for app in apps if app.get('appid')]
            
            logger.info(f"✅ {len(app_ids):,}個のアプリケーションIDを取得しました")
            return app_ids
            
        except Exception as e:
            logger.error(f"❌ 旧API取得エラー: {e}")
            return []

    def _get_app_ids_via_store_service(self) -> List[int]:
        """IStoreService (v1) を使用してアプリIDを取得（APIキー必須）"""
        url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
        app_ids = []
        last_appid = 0
        has_more = True
        
        logger.info("📥 IStoreService(v1)経由でリスト取得中...")
        
        while has_more:
            params = {
                'key': self.api_key,
                'include_games': 1,
                'include_dlc': 0,
                'include_software': 0,
                'last_appid': last_appid,
                'max_results': 50000
            }
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                
                response_body = data.get('response', {})
                apps = response_body.get('apps', [])
                
                if not apps:
                    break
                
                new_ids = [app['appid'] for app in apps]
                app_ids.extend(new_ids)
                
                last_appid = response_body.get('last_appid')
                has_more = response_body.get('have_more_results', False)
                
                logger.info(f"  - 現在 {len(app_ids)} 件...")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ IStoreServiceエラー: {e}")
                break
        
        if app_ids:
            logger.info(f"✅ {len(app_ids):,}個のアプリケーションIDを取得しました")
        
        return app_ids

    def random_sample_app_ids(self, all_app_ids: List[int], sample_size: int, seed=None) -> List[int]:
        """
        ランダムにapp_idをサンプリング
        
        Args:
            all_app_ids: 全アプリIDのリスト
            sample_size: サンプル数
            seed: 乱数シード（再現性が必要な場合に指定）
        """
        if seed is not None:
            random.seed(seed)
            logger.info(f"🎲 乱数シード: {seed}（結果の再現が可能）")
        
        actual_sample_size = min(sample_size, len(all_app_ids))
        sampled_ids = random.sample(all_app_ids, actual_sample_size)
        
        logger.info(f"🎯 {len(all_app_ids):,}個から{actual_sample_size:,}個をランダムサンプリングしました")
        logger.info(f"📊 サンプルID範囲: {min(sampled_ids)} 〜 {max(sampled_ids)}")
        
        return sampled_ids
    
    def get_player_count(self, app_id: int) -> Optional[Dict]:
        """現在のプレイヤー数を取得"""
        try:
            url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
            response = self.session.get(
                url,
                params={'appid': app_id},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('response', {}).get('result') == 1:
                    player_count = data['response']['player_count']
                    return {
                        'app_id': app_id,
                        'player_count': player_count,
                        'collected_at': datetime.now().isoformat()
                    }
        except:
            pass
        
        return None
    
    def collect_bulk(self, app_ids: List[int], output_prefix='steam_players', resume=False) -> List[Dict]:
        """
        大量のプレイヤー数データを高速収集
        
        Args:
            app_ids: 収集するapp_idのリスト
            output_prefix: 出力ファイルのプレフィックス
            resume: Trueの場合、既存のチェックポイントから再開
        """
        all_data = []
        processed_ids = set()
        start_index = 0
        
        # 再開モード: 既存のチェックポイントを探す
        if resume:
            checkpoint_loaded = False
            # チェックポイントファイルを降順で探す
            for i in range(len(app_ids), 0, -self.checkpoint_interval):
                checkpoint_file = f'{output_prefix}_checkpoint_{i}.json'
                if os.path.exists(checkpoint_file):
                    logger.info(f"🔄 チェックポイント発見: {checkpoint_file}")
                    try:
                        with open(checkpoint_file, 'r', encoding='utf-8') as f:
                            all_data = json.load(f)
                        processed_ids = {game['app_id'] for game in all_data}
                        start_index = i
                        checkpoint_loaded = True
                        logger.info(f"✅ {len(all_data)}件のデータを復元しました")
                        logger.info(f"📍 {start_index}番目から再開します")
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ チェックポイント読み込みエラー: {e}")
            
            if not checkpoint_loaded:
                logger.info("ℹ️ チェックポイントが見つかりませんでした。最初から開始します")
        
        self.stats['total_requested'] = len(app_ids)
        self.stats['successful'] = len(all_data)
        self.stats['start_time'] = datetime.now()
        
        logger.info("="*70)
        logger.info(f"🚀 {len(app_ids):,}ゲームのプレイヤー数データ収集を開始します")
        if resume and start_index > 0:
            logger.info(f"🔄 再開モード: {start_index}/{len(app_ids)}から継続")
        logger.info(f"⏱️  推定所要時間: {len(app_ids) * self.delay / 60:.1f}分 ({len(app_ids) * self.delay / 3600:.1f}時間)")
        logger.info(f"⚡ 高速モード: 1ゲームあたり約{self.delay:.1f}秒（プレイヤー数のみ）")
        logger.info("="*70)
        
        for i, app_id in enumerate(app_ids, 1):
            # スキップ済みのIDはスキップ
            if app_id in processed_ids:
                continue
            
            # 進捗表示
            if i % 100 == 0 or i == 1:
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                speed = i / elapsed if elapsed > 0 else 0
                remaining = (len(app_ids) - i) / speed if speed > 0 else 0
                
                logger.info(f"\n{'='*70}")
                logger.info(f"進捗: {i:,}/{len(app_ids):,} ({i/len(app_ids)*100:.1f}%)")
                logger.info(f"成功: {self.stats['successful']:,} | 失敗: {self.stats['failed']:,}")
                logger.info(f"プレイヤーあり: {self.stats['with_players']:,} ({self.stats['with_players']/max(self.stats['successful'], 1)*100:.1f}%)")
                logger.info(f"速度: {speed:.2f}ゲーム/秒")
                logger.info(f"残り時間: 約{remaining/60:.1f}分")
                logger.info(f"{'='*70}")
            
            # データ収集
            player_data = self.get_player_count(app_id)
            
            if player_data:
                all_data.append(player_data)
                processed_ids.add(app_id)
                self.stats['successful'] += 1
                
                if player_data['player_count'] > 0:
                    self.stats['with_players'] += 1
                
                if i % 50 == 0:
                    logger.info(f"✅ [{i}] AppID {app_id}: プレイヤー数 {player_data['player_count']:,}")
            else:
                self.stats['failed'] += 1
                logger.debug(f"⚠️ [{i}] AppID {app_id}: 取得失敗")
            
            # チェックポイント保存
            if i % self.checkpoint_interval == 0:
                checkpoint_file = f'{output_prefix}_checkpoint_{i}.json'
                self._save_checkpoint(all_data, checkpoint_file)
                self._save_processed_ids(processed_ids, f'{output_prefix}_processed_ids.json')
                logger.info(f"💾 チェックポイント保存: {checkpoint_file}")
            
            # レート制限対策
            if i < len(app_ids):
                time.sleep(self.delay)
        
        self.stats['end_time'] = datetime.now()
        self._print_final_stats()
        
        return all_data
    
    def _save_checkpoint(self, data: List[Dict], filename: str):
        """中間保存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"チェックポイント保存エラー: {e}")
    
    def _save_processed_ids(self, processed_ids: set, filename: str):
        """処理済みIDリストを保存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(list(processed_ids), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"処理済みIDリスト保存エラー: {e}")
    
    def _print_final_stats(self):
        """最終統計を表示"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("\n" + "="*70)
        logger.info("📊 収集完了 - 最終統計")
        logger.info("="*70)
        logger.info(f"総リクエスト数:      {self.stats['total_requested']:,}")
        logger.info(f"成功:                {self.stats['successful']:,}")
        logger.info(f"失敗:                {self.stats['failed']:,}")
        logger.info(f"成功率:              {self.stats['successful']/self.stats['total_requested']*100:.1f}%")
        logger.info(f"プレイヤー数あり:    {self.stats['with_players']:,} ({self.stats['with_players']/max(self.stats['successful'], 1)*100:.1f}%)")
        logger.info(f"処理時間:            {duration:.1f}秒 ({duration/60:.1f}分 / {duration/3600:.2f}時間)")
        logger.info(f"平均速度:            {self.stats['successful']/duration:.2f}ゲーム/秒")
        logger.info("="*70)
    
    def save_to_json(self, data: List[Dict], filename: str):
        """JSONファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON保存完了: {filename} ({len(data):,}件)")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """CSVファイルに保存"""
        if data:
            df = pd.DataFrame(data)
            
            # カラムの順序を指定
            column_order = ['app_id', 'player_count', 'collected_at']
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # プレイヤー数で降順ソート
            df = df.sort_values('player_count', ascending=False)
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"💾 CSV保存完了: {filename} ({len(data):,}件)")
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """Excelファイルに保存"""
        if data:
            df = pd.DataFrame(data)
            
            column_order = ['app_id', 'player_count', 'collected_at']
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # プレイヤー数で降順ソート
            df = df.sort_values('player_count', ascending=False)
            
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"💾 Excel保存完了: {filename} ({len(data):,}件)")


def print_data_summary(data: List[Dict]):
    """収集データの簡易分析"""
    print("\n" + "="*70)
    print("📈 プレイヤー数データ分析サマリー")
    print("="*70)
    
    total = len(data)
    with_players = sum(1 for g in data if g.get('player_count', 0) > 0)
    zero_players = total - with_players
    
    print(f"総ゲーム数:            {total:,}")
    print(f"プレイヤーあり:        {with_players:,} ({with_players/total*100:.1f}%)")
    print(f"プレイヤー0人:         {zero_players:,} ({zero_players/total*100:.1f}%)")
    
    # プレイヤー数統計
    player_counts = [g['player_count'] for g in data if g.get('player_count', 0) > 0]
    if player_counts:
        print(f"\nプレイヤー数統計（0人除く）:")
        print(f"  総プレイヤー数:  {sum(player_counts):,}")
        print(f"  平均:            {sum(player_counts)/len(player_counts):,.1f}")
        print(f"  最大:            {max(player_counts):,}")
        print(f"  最小:            {min(player_counts):,}")
        
        # TOP 10
        sorted_data = sorted(data, key=lambda x: x.get('player_count', 0), reverse=True)
        print(f"\nTOP 10 プレイヤー数:")
        for i, game in enumerate(sorted_data[:10], 1):
            print(f"  {i}. AppID {game['app_id']}: {game['player_count']:,}人")
    
    print("="*70)


def main():
    """メイン実行関数"""
    
    print("="*70)
    print("⚡ Steam プレイヤー数高速収集ツール (再開機能付き)")
    print("="*70)
    print("\n特徴:")
    print("  ✅ プレイヤー数のみを高速収集")
    print("  ✅ 約0.3秒/ゲーム（通常版の約7倍高速）")
    print("  ✅ 500件ごとに自動保存")
    print("  ✅ 中断しても再開可能")
    print("="*70)
    
    # 再開モードの確認
    resume_mode = False
    checkpoint_files = [f for f in os.listdir('.') if f.startswith('steam_players_') and '_checkpoint_' in f and f.endswith('.json')]
    
    if checkpoint_files:
        print(f"\n💾 {len(checkpoint_files)}個のチェックポイントファイルが見つかりました")
        print("前回の収集を途中から再開しますか？")
        resume_choice = input("(y: 再開 / n: 新規開始): ").lower()
        if resume_choice == 'y':
            resume_mode = True
            print("✅ 再開モードで開始します")
    
    # コレクター初期化
    api_key_to_use = STEAM_API_KEY if STEAM_API_KEY else None
    collector = SteamPlayerCountCollector(
        api_key=api_key_to_use,
        delay=0.3,  # 高速化: プレイヤー数APIは制限が緩い
        timeout=10,
        checkpoint_interval=500  # 500件ごとに保存
    )
    
    # 全アプリIDを取得
    all_app_ids = collector.get_all_app_ids()
    
    if not all_app_ids:
        logger.error("アプリIDの取得に失敗しました")
        return
    
    print(f"\n📊 利用可能なアプリID数: {len(all_app_ids):,}")
    
    # 再開モードの場合、既存の設定を検出
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_prefix = None
    app_ids_to_collect = []
    
    if resume_mode:
        # 最新のチェックポイントから設定を復元
        latest_checkpoint = sorted(checkpoint_files, reverse=True)[0]
        parts = latest_checkpoint.split('_')
        if len(parts) >= 4:
            target_count = int(parts[2])
            timestamp_str = f"{parts[3]}_{parts[4]}"
            output_prefix = f"steam_players_{target_count}_{timestamp_str}"
            
            # 既存のapp_idリストがあれば読み込む
            processed_ids_file = f'{output_prefix}_processed_ids.json'
            if os.path.exists(processed_ids_file):
                with open(processed_ids_file, 'r', encoding='utf-8') as f:
                    processed_ids = set(json.load(f))
                    print(f"📋 {len(processed_ids)}個のapp_idがすでに処理済みです")
            
            print(f"✅ 前回の設定を復元: {target_count}ゲーム")
            app_ids_to_collect = collector.random_sample_app_ids(all_app_ids, target_count, seed=None)
    
    if not resume_mode or not output_prefix:
        # 新規開始
        print("\n収集数を選択:")
        print("1. 1,000ゲーム（約5分）")
        print("2. 5,000ゲーム（約25分）")
        print("3. 10,000ゲーム（約50分）")
        print("4. 50,000ゲーム（約4時間）")
        print("5. 100,000ゲーム（約8時間）")
        print("6. 全ゲーム（推定: 約{:.1f}時間）".format(len(all_app_ids) * 0.3 / 3600))
        print("7. カスタム数")
        
        choice = input("\n選択 (1-7): ").strip()
        
        if choice == '1':
            target_count = 1000
        elif choice == '2':
            target_count = 5000
        elif choice == '3':
            target_count = 10000
        elif choice == '4':
            target_count = 50000
        elif choice == '5':
            target_count = 100000
        elif choice == '6':
            target_count = len(all_app_ids)
        elif choice == '7':
            target_count = int(input("収集するゲーム数を入力: "))
        else:
            target_count = 1000
        
        # 乱数シード設定（オプション）
        use_seed = input("\n乱数シードを設定しますか？（再現性が必要な場合）(y/n): ").lower() == 'y'
        seed = None
        if use_seed:
            seed = int(input("シード値を入力（整数）: "))
        
        # ランダムサンプリング
        if target_count < len(all_app_ids):
            app_ids_to_collect = collector.random_sample_app_ids(all_app_ids, target_count, seed=seed)
        else:
            app_ids_to_collect = all_app_ids
            logger.info(f"✅ 全{len(all_app_ids):,}ゲームを収集します")
        
        # 出力ファイル名を生成
        output_prefix = f'steam_players_{len(app_ids_to_collect)}_{timestamp}'
    
    # 確認
    estimated_time = len(app_ids_to_collect) * 0.3 / 60
    print(f"\n⏱️  推定所要時間: 約{estimated_time:.1f}分 ({estimated_time/60:.1f}時間)")
    print(f"⚡ 高速モード: 1ゲームあたり約0.3秒")
    if not resume_mode:
        print(f"🎲 ランダムに選ばれた最初の10個のapp_id: {app_ids_to_collect[:10]}")
    print(f"💾 500件ごとに自動保存されます（中断しても再開可能）")
    confirm = input("\n収集を開始しますか？ (y/n): ")
    
    if confirm.lower() != 'y':
        logger.info("収集を中止しました")
        return
    
    # データ収集開始
    collected_data = collector.collect_bulk(app_ids_to_collect, output_prefix=output_prefix, resume=resume_mode)
    
    # データ保存
    if collected_data:
        logger.info("\n💾 データを保存中...")
        
        # JSON保存
        collector.save_to_json(collected_data, f'{output_prefix}.json')
        
        # CSV保存
        collector.save_to_csv(collected_data, f'{output_prefix}.csv')
        
        # Excel保存（オプション）
        save_excel = input("\nExcelファイルも保存しますか？ (y/n): ")
        if save_excel.lower() == 'y':
            collector.save_to_excel(collected_data, f'{output_prefix}.xlsx')
        
        # サンプルデータ表示
        print("\n📊 取得データのサンプル（プレイヤー数TOP 5）:")
        print("="*70)
        sorted_data = sorted(collected_data, key=lambda x: x.get('player_count', 0), reverse=True)
        for game in sorted_data[:5]:
            print(json.dumps(game, ensure_ascii=False, indent=2))
            print("-"*70)
        
        logger.info(f"\n✨ 完了！ {len(collected_data):,}件のプレイヤー数データを保存しました")
        
        # データ分析サマリー
        print_data_summary(collected_data)
    else:
        logger.warning("⚠️ データが収集できませんでした")


if __name__ == "__main__":
    main()
