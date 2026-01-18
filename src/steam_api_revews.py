import requests
import json
import time
import random
from datetime import datetime
import pandas as pd
import logging
from typing import List, Dict, Optional

# API Key（https://steamcommunity.com/dev/apikey で取得）
STEAM_API_KEY = "942710D8C9D88DF9C28ED5E25B03CFED"

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SteamDataCollector:
    """Steam APIからapp_id、プレイヤー数、レビュー数を収集"""
    
    def __init__(self, api_key=None, delay=1.3, timeout=10):
        self.api_key = api_key
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_all_app_ids(self) -> List[int]:
        """全アプリIDを取得"""
        logger.info("全アプリケーションリストを取得中...")
        
        if self.api_key:
            return self._get_app_ids_via_store_service()
        
        try:
            url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            apps = data['applist']['apps']
            app_ids = [app['appid'] for app in apps if app.get('appid')]
            
            logger.info(f"{len(app_ids):,}個のアプリIDを取得")
            return app_ids
        except Exception as e:
            logger.error(f"エラー: {e}")
            return []
    
    def _get_app_ids_via_store_service(self) -> List[int]:
        """IStoreServiceでアプリID取得"""
        url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
        app_ids = []
        last_appid = 0
        has_more = True
        
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
                
                logger.info(f"  現在 {len(app_ids)} 件...")
                time.sleep(1)
            except Exception as e:
                logger.error(f"エラー: {e}")
                break
        
        if app_ids:
            logger.info(f"{len(app_ids):,}個のアプリIDを取得")
        
        return app_ids
    
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
    
    def get_review_count(self, app_id: int) -> Optional[Dict]:
        """レビュー数を取得"""
        try:
            url = f"https://store.steampowered.com/appreviews/{app_id}"
            params = {
                'json': 1,
                'language': 'all',
                'purchase_type': 'all',
                'num_per_page': 0
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                query_summary = data.get('query_summary', {})
                
                return {
                    'total_reviews': query_summary.get('total_reviews', 0),
                    'positive_reviews': query_summary.get('total_positive', 0),
                    'negative_reviews': query_summary.get('total_negative', 0)
                }
        except:
            pass
        
        return None
    
    def is_game(self, app_id: int) -> bool:
        """ゲームかどうかを確認"""
        try:
            url = "https://store.steampowered.com/api/appdetails"
            response = self.session.get(
                url,
                params={'appids': app_id},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get(str(app_id), {}).get('success'):
                    details = data[str(app_id)]['data']
                    return details.get('type') == 'game'
        except:
            pass
        
        return False
    
    def collect_single_game(self, app_id: int) -> Optional[Dict]:
        """1つのゲームのデータを収集"""
        
        # ゲームかどうか確認
        if not self.is_game(app_id):
            return None
        
        time.sleep(0.3)
        
        # プレイヤー数取得
        player_count = self.get_player_count(app_id)
        
        time.sleep(0.3)
        
        # レビュー数取得
        review_data = self.get_review_count(app_id)
        
        if review_data is None:
            review_data = {
                'total_reviews': None,
                'positive_reviews': None,
                'negative_reviews': None
            }
        
        return {
            'app_id': app_id,
            'player_count': player_count,
            'total_reviews': review_data['total_reviews'],
            'positive_reviews': review_data['positive_reviews'],
            'negative_reviews': review_data['negative_reviews'],
            'collected_at': datetime.now().isoformat()
        }
    
    def collect_bulk(self, app_ids: List[int]) -> List[Dict]:
        """大量のゲームデータを収集"""
        logger.info(f"🚀 {len(app_ids):,}ゲームのデータ収集を開始")
        
        all_data = []
        successful = 0
        failed = 0
        
        for i, app_id in enumerate(app_ids, 1):
            if i % 50 == 0:
                logger.info(f"進捗: {i}/{len(app_ids)} ({i/len(app_ids)*100:.1f}%) | 成功: {successful}")
            
            game_data = self.collect_single_game(app_id)
            
            if game_data:
                all_data.append(game_data)
                successful += 1
                
                if i % 10 == 0:
                    logger.info(f"✅ [{i}] AppID {app_id}: 収集完了")
            else:
                failed += 1
            
            # レート制限対策
            if i < len(app_ids):
                time.sleep(self.delay)
        
        logger.info(f"\n✨ 完了！ 成功: {successful}, 失敗: {failed}")
        return all_data
    
    def save_to_json(self, data: List[Dict], filename: str):
        """JSONに保存"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON保存: {filename} ({len(data):,}件)")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """CSVに保存"""
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"💾 CSV保存: {filename} ({len(data):,}件)")


def main():
    """メイン実行"""
    
    print("="*70)
    print("🎮 Steam データ収集ツール（シンプル版）")
    print("="*70)
    print("\n取得データ:")
    print("  - app_id")
    print("  - player_count（現在のプレイヤー数）")
    print("  - total_reviews（総レビュー数）")
    print("  - positive_reviews（好評数）")
    print("  - negative_reviews（不評数）")
    print("="*70)
    
    # コレクター初期化
    api_key = STEAM_API_KEY if STEAM_API_KEY else None
    collector = SteamDataCollector(api_key=api_key, delay=1.3, timeout=10)
    
    # 全アプリID取得
    all_app_ids = collector.get_all_app_ids()
    
    if not all_app_ids:
        logger.error("アプリIDの取得に失敗")
        return
    
    print(f"\n📊 利用可能なアプリID数: {len(all_app_ids):,}")
    
    # 収集数を選択
    print("\n収集数を選択:")
    print("1. 100ゲーム（テスト用）")
    print("2. 500ゲーム")
    print("3. 1,000ゲーム")
    print("4. 5,000ゲーム")
    print("5. カスタム")
    
    choice = input("\n選択 (1-5): ").strip()
    
    if choice == '1':
        target_count = 100
    elif choice == '2':
        target_count = 500
    elif choice == '3':
        target_count = 1000
    elif choice == '4':
        target_count = 5000
    elif choice == '5':
        target_count = int(input("収集するゲーム数: "))
    else:
        target_count = 100
    
    # ランダムサンプリング
    sampled_ids = random.sample(all_app_ids, min(target_count, len(all_app_ids)))
    
    print(f"\n🎲 {len(sampled_ids):,}個のゲームをランダムサンプリング")
    print(f"⏱️  推定所要時間: 約{len(sampled_ids) * 2.0 / 60:.1f}分")
    
    confirm = input("\n収集を開始しますか？ (y/n): ")
    
    if confirm.lower() != 'y':
        logger.info("中止しました")
        return
    
    # データ収集
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    collected_data = collector.collect_bulk(sampled_ids)
    
    # 保存
    if collected_data:
        prefix = f'steam_simple_{len(collected_data)}_{timestamp}'
        
        collector.save_to_json(collected_data, f'{prefix}.json')
        collector.save_to_csv(collected_data, f'{prefix}.csv')
        
        # サマリー表示
        print("\n" + "="*70)
        print("📈 データサマリー")
        print("="*70)
        
        total = len(collected_data)
        with_players = sum(1 for g in collected_data if g.get('player_count') and g['player_count'] > 0)
        with_reviews = sum(1 for g in collected_data if g.get('total_reviews') and g['total_reviews'] > 0)
        
        print(f"総ゲーム数: {total:,}")
        print(f"プレイヤー数あり: {with_players:,} ({with_players/total*100:.1f}%)")
        print(f"レビューあり: {with_reviews:,} ({with_reviews/total*100:.1f}%)")
        
        if with_players > 0:
            players = [g['player_count'] for g in collected_data if g.get('player_count') and g['player_count'] > 0]
            print(f"\nプレイヤー数統計:")
            print(f"  最大: {max(players):,}")
            print(f"  平均: {sum(players)/len(players):.1f}")
        
        if with_reviews > 0:
            reviews = [g['total_reviews'] for g in collected_data if g.get('total_reviews') and g['total_reviews'] > 0]
            print(f"\nレビュー数統計:")
            print(f"  最大: {max(reviews):,}")
            print(f"  平均: {sum(reviews)/len(reviews):.1f}")
        
        print("="*70)
    else:
        logger.warning("⚠️ データが収集できませんでした")


if __name__ == "__main__":
    main()