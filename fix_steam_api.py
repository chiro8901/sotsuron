import sys
import os

input_path = "steam_api_data.py"
output_path = "steam_api_data_fixed.py"

if not os.path.exists(input_path):
    print(f"Error: {input_path} not found.")
    sys.exit(1)

with open(input_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
imports_done = False
in_get_all = False

new_methods = '''    
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
'''

for line in lines:
    if not imports_done and line.startswith('from typing import'):
        new_lines.append(line)
        new_lines.append("\\n# API Key（https://steamcommunity.com/dev/apikey で取得）\\n")
        new_lines.append("STEAM_API_KEY = \"\"\\n\\n")
        imports_done = True
        continue
        
    if "def __init__(self, delay=0.6" in line:
        new_lines.append("    def __init__(self, api_key=None, delay=0.6, timeout=10, checkpoint_interval=100):\\n")
        continue
    if "self.timeout = timeout" in line:
        new_lines.append("        self.api_key = api_key\\n")
        new_lines.append(line)
        continue
        
    if "def get_all_app_ids(self) -> List[int]:" in line:
        in_get_all = True
        new_lines.append(new_methods)
        continue
    
    if in_get_all:
        if "def random_sample_app_ids" in line:
            in_get_all = False
            new_lines.append("\\n" + line)
        continue

    if "collector = SteamRandomCollector(" in line:
        new_lines.append("    # APIキーを設定\\n")
        new_lines.append("    api_key_to_use = STEAM_API_KEY if STEAM_API_KEY else None\\n")
        new_lines.append("    collector = SteamRandomCollector(\\n")
        new_lines.append("        api_key=api_key_to_use,\\n")
        continue

    new_lines.append(line)

with open(output_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print(f"Created {output_path}")
