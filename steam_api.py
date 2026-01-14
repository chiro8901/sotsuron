import requests

def get_current_players(app_id):
    """現在のプレイヤー数を取得"""
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {'appid': app_id}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 取得できるデータ: 
    # - player_count: 現在のプレイヤー数
    # - result: APIレスポンスの成否
    
    return data

# 例:  Counter-Strike 2
result = get_current_players(730)
print(result)
# 出力例: {'response': {'player_count': 850000, 'result': 1}}