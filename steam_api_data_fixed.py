import requests
import json
import time
import random
from datetime import datetime
import pandas as pd
import logging
from typing import List, Dict, Optional
# API Key（https://steamcommunity.com/dev/apikey で取得）
STEAM_API_KEY = ""
# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging. FileHandler('steam_random_collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SteamRandomCollector: 
    """Steam APIからランダムにゲームデータを収集"""
    
    def __init__(self, api_key=None, delay=0.6, timeout=10, checkpoint_interval=100):
        """
        Args:
            delay: API呼び出し間隔（秒）
            timeout: リクエストタイムアウト（秒）
            checkpoint_interval: 何件ごとに中間保存するか
        """
        self.delay = delay
        self.api_key = api_key
        self.timeout = timeout
        self.checkpoint_interval = checkpoint_interval
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent':  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 統計情報
        self. stats = {
            'total_requested': 0,
            'successful':  0,
            'failed':  0,
            'with_players': 0,
            'with_metacritic': 0,
            'start_time':  None,
            'end_time': None
        }
    
    
    def get_all_app_ids(self) -> List[int]:
        """Steam上の全アプリケーションIDを取得"""
        logger.info(" 全アプリケーションリストを取得中...")
        
        # 1. APIキーがある場合は新しいIStoreServiceを使用
        if self.api_key:
            return self._get_app_ids_via_store_service()
            
        # 2. 従来のAPIを試行
        try:
            logger.info(" APIキー未指定: 旧API(ISteamApps)を試行します...")
            url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            apps = data['applist']['apps']
            app_ids = [app['appid'] for app in apps if app.get('appid')]
            
            logger.info(f" {len(app_ids):,}個のアプリケーションIDを取得しました")
            return app_ids
            
        except Exception as e:
            logger.error(f" 旧API取得エラー: {e}")
            logger.warning(" ヒント: Steam APIの仕様変更により、APIキーが必要な場合があります。")
            logger.warning("   https://steamcommunity.com/dev/apikey でキーを取得し、ファイルの先頭にある STEAM_API_KEY に設定してください。")
            return []

    def _get_app_ids_via_store_service(self) -> List[int]:
        """IStoreService (v1) を使用してアプリIDを取得（APIキー必須）"""
        url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
        app_ids = []
        last_appid = 0
        has_more = True
        
        logger.info(" IStoreService(v1)経由でリスト取得中...")
        
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
                logger.error(f" IStoreServiceエラー: {e}")
                break
        
        if app_ids:
            logger.info(f" {len(app_ids):,}個のアプリケーションIDを取得しました")
        
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
            logger.info(f"🎲 乱数シード:  {seed}（結果の再現が可能）")
        
        actual_sample_size = min(sample_size, len(all_app_ids))
        sampled_ids = random.sample(all_app_ids, actual_sample_size)
        
        logger.info(f"🎯 {len(all_app_ids):,}個から{actual_sample_size:,}個をランダムサンプリングしました")
        logger.info(f"📊 サンプルID範囲: {min(sampled_ids)} 〜 {max(sampled_ids)}")
        
        return sampled_ids
    
    def get_player_count(self, app_id: int) -> Optional[int]:
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
                    return data['response']['player_count']
        except:
            pass
        
        return None
    
    def get_achievement_count(self, app_id: int) -> Optional[int]:
        """実績数を取得"""
        try: 
            url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"
            response = self.session.get(
                url,
                params={'gameid': app_id},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                achievements = data.get('achievementpercentages', {}).get('achievements', [])
                return len(achievements)
        except:
            pass
        
        return None
    
    def get_game_details(self, app_id: int) -> Optional[Dict]:
        """
        指定された項目のみを取得:
        - type
        - is_free
        - categories
        - genres
        - price_jpy
        - metacritic_score
        """
        try: 
            url = "https://store.steampowered.com/api/appdetails"
            response = self.session.get(
                url,
                params={'appids': app_id, 'l': 'japanese'},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get(str(app_id), {}).get('success'):
                    details = data[str(app_id)]['data']
                    
                    result = {
                        'app_id': app_id,
                        'type': details.get('type'),
                        'is_free': details.get('is_free', False),
                    }
                    
                    # カテゴリー
                    categories = details.get('categories', [])
                    result['categories'] = [cat.get('description') for cat in categories] if categories else []
                    
                    # ジャンル
                    genres = details.get('genres', [])
                    result['genres'] = [genre.get('description') for genre in genres] if genres else []
                    
                    # 価格（円）
                    price_overview = details.get('price_overview')
                    if price_overview: 
                        result['price_jpy'] = price_overview.get('final', 0) / 100
                    else:
                        result['price_jpy'] = 0 if result['is_free'] else None
                    
                    # メタスコア
                    metacritic = details.get('metacritic')
                    result['metacritic_score'] = metacritic.get('score') if metacritic else None
                    
                    return result
                    
        except Exception as e: 
            logger.debug(f"詳細取得エラー (AppID {app_id}): {e}")
        
        return None
    
    def collect_single_game(self, app_id: int) -> Optional[Dict]:
        """1つのゲームの全データを収集"""
        
        # 1. ゲーム詳細を取得
        game_data = self.get_game_details(app_id)
        
        if not game_data:
            return None
        
        # ゲームタイプのみをフィルタリング
        if game_data.get('type') != 'game':
            return None
        
        time.sleep(0.2)
        
        # 2. プレイヤー数を取得
        player_count = self.get_player_count(app_id)
        game_data['player_count'] = player_count
        if player_count is not None and player_count > 0:
            self.stats['with_players'] += 1
        
        time.sleep(0.2)
        
        # 3. 実績数を取得
        achievement_count = self.get_achievement_count(app_id)
        game_data['total_achievements'] = achievement_count
        
        # メタスコア統計
        if game_data.get('metacritic_score'):
            self.stats['with_metacritic'] += 1
        
        # 収集日時
        game_data['collected_at'] = datetime.now().isoformat()
        
        return game_data
    
    def collect_bulk(self, app_ids: List[int], output_prefix='steam_random') -> List[Dict]:
        """
        大量のゲームデータを収集
        """
        self.stats['total_requested'] = len(app_ids)
        self.stats['start_time'] = datetime.now()
        
        logger.info("="*70)
        logger.info(f"🚀 {len(app_ids):,}ゲームのデータ収集を開始します")
        logger.info(f"⏱️  推定所要時間: {len(app_ids) * self.delay / 60:.1f}分 ({len(app_ids) * self.delay / 3600:.1f}時間)")
        logger.info("="*70)
        
        all_data = []
        
        for i, app_id in enumerate(app_ids, 1):
            # 進捗表示
            if i % 50 == 0 or i == 1:
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                speed = i / elapsed if elapsed > 0 else 0
                remaining = (len(app_ids) - i) / speed if speed > 0 else 0
                
                logger.info(f"\n{'='*70}")
                logger.info(f"進捗: {i:,}/{len(app_ids):,} ({i/len(app_ids)*100:.1f}%)")
                logger.info(f"成功: {self.stats['successful']:,} | 失敗: {self.stats['failed']:,}")
                logger.info(f"速度: {speed:.2f}ゲーム/秒")
                logger.info(f"残り時間: 約{remaining/60:.1f}分")
                logger.info(f"{'='*70}")
            
            # データ収集
            game_data = self.collect_single_game(app_id)
            
            if game_data:
                all_data.append(game_data)
                self.stats['successful'] += 1
                
                if i % 10 == 0:
                    logger.info(f"✅ [{i}] AppID {app_id}: {self.stats['successful']}件収集完了")
            else:
                self.stats['failed'] += 1
                logger.debug(f"⚠️ [{i}] AppID {app_id}: スキップ")
            
            # チェックポイント保存
            if i % self.checkpoint_interval == 0:
                checkpoint_file = f'{output_prefix}_checkpoint_{i}. json'
                self._save_checkpoint(all_data, checkpoint_file)
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
    
    def _print_final_stats(self):
        """最終統計を表示"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("\n" + "="*70)
        logger.info("📊 収集完了 - 最終統計")
        logger.info("="*70)
        logger.info(f"総リクエスト数:      {self.stats['total_requested']:,}")
        logger.info(f"成功:                {self.stats['successful']:,}")
        logger.info(f"失敗:               {self.stats['failed']:,}")
        logger.info(f"成功率:             {self.stats['successful']/self.stats['total_requested']*100:.1f}%")
        logger.info(f"プレイヤー数あり:   {self.stats['with_players']:,} ({self.stats['with_players']/max(self.stats['successful'], 1)*100:.1f}%)")
        logger.info(f"メタスコアあり:     {self.stats['with_metacritic']:,} ({self.stats['with_metacritic']/max(self.stats['successful'], 1)*100:.1f}%)")
        logger.info(f"処理時間:           {duration:.1f}秒 ({duration/60:.1f}分 / {duration/3600:.2f}時間)")
        logger.info(f"平均速度:           {self.stats['successful']/duration:.2f}ゲーム/秒")
        logger.info("="*70)
    
    def save_to_json(self, data: List[Dict], filename: str):
        """JSONファイルに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON保存完了: {filename} ({len(data):,}件)")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """CSVファイルに保存"""
        if data:
            # リスト型のフィールドを文字列に変換
            data_for_csv = []
            for game in data:
                game_copy = game.copy()
                if isinstance(game_copy.get('categories'), list):
                    game_copy['categories'] = '|'.join(game_copy['categories'])
                if isinstance(game_copy.get('genres'), list):
                    game_copy['genres'] = '|'.join(game_copy['genres'])
                data_for_csv.append(game_copy)
            
            df = pd.DataFrame(data_for_csv)
            
            # カ���ムの順序を指定
            column_order = [
                'app_id',
                'player_count',
                'type',
                'is_free',
                'categories',
                'genres',
                'price_jpy',
                'metacritic_score',
                'total_achievements',
                'collected_at'
            ]
            
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"💾 CSV保存完了: {filename} ({len(data):,}件)")
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """Excelファイルに保存"""
        if data:
            data_for_excel = []
            for game in data:
                game_copy = game.copy()
                if isinstance(game_copy.get('categories'), list):
                    game_copy['categories'] = '|'.join(game_copy['categories'])
                if isinstance(game_copy.get('genres'), list):
                    game_copy['genres'] = '|'.join(game_copy['genres'])
                data_for_excel.append(game_copy)
            
            df = pd.DataFrame(data_for_excel)
            
            column_order = [
                'app_id',
                'player_count',
                'type',
                'is_free',
                'categories',
                'genres',
                'price_jpy',
                'metacritic_score',
                'total_achievements',
                'collected_at'
            ]
            
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"💾 Excel保存完了:  {filename} ({len(data):,}件)")


def print_data_summary(data: List[Dict]):
    """収集データの簡易分析"""
    print("\n" + "="*70)
    print("📈 データ分析サマリー")
    print("="*70)
    
    total = len(data)
    free_games = sum(1 for g in data if g.get('is_free'))
    with_price = sum(1 for g in data if g.get('price_jpy') and g['price_jpy'] > 0)
    with_metacritic = sum(1 for g in data if g.get('metacritic_score'))
    with_players = sum(1 for g in data if g.get('player_count') and g['player_count'] > 0)
    with_achievements = sum(1 for g in data if g.get('total_achievements'))
    
    print(f"総ゲーム数:            {total:,}")
    print(f"無料ゲーム:            {free_games:,} ({free_games/total*100:.1f}%)")
    print(f"有料ゲーム:           {with_price:,} ({with_price/total*100:.1f}%)")
    print(f"メタスコアあり:       {with_metacritic:,} ({with_metacritic/total*100:.1f}%)")
    print(f"プレイヤー数あり:     {with_players:,} ({with_players/total*100:.1f}%)")
    print(f"実績あり:             {with_achievements:,} ({with_achievements/total*100:.1f}%)")
    
    # 価格統計
    prices = [g['price_jpy'] for g in data if g.get('price_jpy') and g['price_jpy'] > 0]
    if prices:
        print(f"\n価格統計:")
        print(f"  平均価格:    ¥{sum(prices)/len(prices):,.0f}")
        print(f"  最高価格:    ¥{max(prices):,.0f}")
        print(f"  最低価格:    ¥{min(prices):,.0f}")
    
    # メタスコア統計
    scores = [g['metacritic_score'] for g in data if g.get('metacritic_score')]
    if scores:
        print(f"\nメタスコア統計:")
        print(f"  平均スコア:  {sum(scores)/len(scores):.1f}")
        print(f"  最高スコア:  {max(scores)}")
        print(f"  最低スコア:  {min(scores)}")
    
    print("="*70)


def main():
    """メイン実行関数"""
    
    print("="*70)
    print("🎲 Steam ランダムゲームデータ収集ツール")
    print("="*70)
    print("\n取得項目:")
    print("  - app_id")
    print("  - player_count")
    print("  - type")
    print("  - is_free")
    print("  - categories")
    print("  - genres")
    print("  - price_jpy")
    print("  - metacritic_score")
    print("  - total_achievements")
    print("="*70)
    
    # コレクター初期化
    # APIキーを設定
    api_key_to_use = STEAM_API_KEY if STEAM_API_KEY else None
    collector = SteamRandomCollector(
        api_key=api_key_to_use,
        delay=0.6,
        timeout=10,
        checkpoint_interval=100
    )
    
    # 全アプリIDを取得
    all_app_ids = collector.get_all_app_ids()
    
    if not all_app_ids: 
        logger.error("アプリIDの取得に失敗しました")
        return
    
    print(f"\n📊 利用可能なアプリID数: {len(all_app_ids):,}")
    
    # 収集数を選択
    print("\n収集数を選択:")
    print("1. 100ゲーム（テスト用 - 約1-2分）")
    print("2. 1,000ゲーム（約10-15分）")
    print("3. 5,000ゲーム（約50-75分）")
    print("4. 10,000ゲーム（約100-150分 = 1.5-2.5時間）")
    print("5. カスタム数")
    
    choice = input("\n選択 (1-5): ").strip()
    
    if choice == '1':
        target_count = 100
    elif choice == '2':
        target_count = 1000
    elif choice == '3':
        target_count = 5000
    elif choice == '4':
        target_count = 10000
    elif choice == '5':
        target_count = int(input("収集するゲーム数を入力: "))
    else:
        target_count = 100
    
    # 乱数シード設定（オプション）
    use_seed = input("\n乱数シードを設定しますか？（再現性が必要な場合）(y/n): ").lower() == 'y'
    seed = None
    if use_seed:
        seed = int(input("シード値を入力（整数）: "))
    
    # ランダムサンプリング
    app_ids_to_collect = collector.random_sample_app_ids(all_app_ids, target_count, seed=seed)
    
    # 確認
    estimated_time = len(app_ids_to_collect) * 0.6 / 60
    print(f"\n⏱️  推定所要時間: 約{estimated_time:.1f}分 ({estimated_time/60:.1f}時間)")
    print(f"🎲 ランダムに選ばれた最初の10個のapp_id: {app_ids_to_collect[:10]}")
    confirm = input("\n収集を開始しますか？ (y/n): ")
    
    if confirm.lower() != 'y':
        logger.info("収集を中止しました")
        return
    
    # データ収集開始
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_prefix = f'steam_random_{len(app_ids_to_collect)}_{timestamp}'
    
    collected_data = collector.collect_bulk(app_ids_to_collect, output_prefix=output_prefix)
    
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
        # サンプルデータ表示
        print("\n📊 取得データのサンプル（最初の3件）:")
        print("="*70)
        for game in collected_data[:3]: 
            print(json.dumps(game, ensure_ascii=False, indent=2))
            print("-"*70)
        
        logger.info(f"\n✨ 完了！ {len(collected_data):,}件のゲームデータを保存しました")
        
        # データ分析サマリー
        print_data_summary(collected_data)
    else:
        logger.warning("⚠️ データが収集できませんでした")


if __name__ == "__main__":
    main()