from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from datetime import datetime, timedelta
import pandas as pd
import time
import json
import requests
import os
import math
import re

# FUNCTIONS =====================================================================================================================================

# 名前からトリップを取得
def get_trip(name):
    player_data = get_players_data()

    for player in player_data['players'].values():
        if player['name'] == name:
            return player['trip']
    return None

# メッセージを送信
def speak(message):
    driver.get(f'https://zinro.net/m/player.php?mode=message&to_user=ALL&message={message}')

# 囁きで送信
def whisper(name,message):
    driver.get(f"https://zinro.net/m/player.php?mode=message&to_user={name}&message={message}")

# 霊界で発言
def speak_in_spirit_world(message):
    driver.get(f"https://zinro.net/m/player.php?mode=message&to_user=霊界&message={message}")

# 名前からidを取得
def get_id(name):
    player_data = get_players_data()

    for player in player_data['players'].values():
        if player['name'] == name:
            return player['id']
    return None

# ファイルにトリップがあれば1を返し、なければ0を返す
def check_player(file_path, tripcode):
    with open(file_path, 'r', encoding='utf-8') as file:
        words = file.readlines()
    words = [word.strip() for word in words]
    if tripcode in words:
        return 1
    else:
        return 0

# トリップからレートを参照してウデマエと人狼パワーを返す
def get_rank(trip):
    rate = rate_dict[trip]
    rank_index = sorted_rates.index(rate)
    total_ids = len(sorted_rates)
    z_power = math.floor(rate * 10) / 10

    if rank_index < total_ids * 0.2:
        return "S",z_power
    elif rank_index < total_ids * 0.5:
        return "A",z_power
    else:
        return "B",z_power

# ログをmessage.txtに記録
def log_message(json_data):
    all_log = [(entry['from_user'], entry['message']) for entry in json_data]
    with open(message_file, 'w', encoding='utf-8') as file:
        for name, message in all_log:
            file.write(f"{name}：{message}\n")

# message.txtの下からn行目を取得
def read_message(n):
    with open(message_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        return lines[-n]

# message.txtの行数をカウント
def count_message():
    with open(message_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        return len(lines)

# テキストファイルの上からn行目を取得
def read_nth_line(filename, n):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for current_line_number, line in enumerate(file, start=1):
                if current_line_number == n:
                    return line.strip()
        return None  # n行目が存在しない場合

    except FileNotFoundError:
        print(f"{filename} が見つかりません。")
        return None

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

# テキストファイルの上からn行目を書き換え
def write_nth_line(filename, n, content):
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if 1 <= n <= len(lines):
        lines[n - 1] = content + '\n'
    else:
        print(f"{filename} の{n}行目を書き換える際にエラーが発生しました")
        return

    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(lines)

# 役職から人狼陣営か村人陣営か判定
def categorize_team(job):
    wolf_team = ["人狼","狂人"]
    villager_team = ["占い師", "霊能者", "狩人", "村人"]
    if job in wolf_team:
        return "人狼"
    elif job in villager_team:
        return "村人"
    return None

# 配役　日時範囲　からログをnew_log.txtに書き加える
def get_logs(jobset, start, end):
    url = f"http://zinrostats.s205.xrea.com/log_search?jobset={jobset}&s_date={start}&e_date={end}&totsushi=0&one_night=0&word_wolf=0"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        results = []
        for entry in data["log_data"]:
            winner = entry["winner"]
            for player in entry["players"]:
                trip = player["trip"]
                job = player["job"]
                if not trip or job == "観戦者":
                    continue
                team = categorize_team(job)
                if team:
                    result = 1 if team == winner else 0
                    results.append({"id": entry["id"], "trip": trip, "result": result})

        with open(new_log_file, 'a', encoding='utf-8') as f:
            for result in results:
                f.write(f"{result['id']}   {result['trip']}   {result['result']}\n")
    else:
        print("ログの取得に失敗しました")

# new_log.txtからware.txtにあるトリップを除外
def remove_waretrip(log_file, ware_file):
    with open(ware_file, 'r', encoding='utf-8') as ware_f:
        ware_ids = {line.strip() for line in ware_f}

    with open(log_file, 'r', encoding='utf-8') as log_f:
        log_lines = log_f.readlines()

    filtered_lines = [line for line in log_lines if not any(ware_id in line for ware_id in ware_ids)]

    with open(log_file, 'w', encoding='utf-8') as log_f:
        log_f.writelines(filtered_lines)

# Eloレーティングで勝者を左、敗者を右に引数を取り、それぞれのレートの変動値を返す
def calculate_elo_change(winner_rating, loser_rating, k=160):
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

    actual_winner = 1  # 勝者の実際の結果
    actual_loser = 0  # 敗者の実際の結果

    change_winner = k * (actual_winner - expected_winner)
    change_loser = k * (actual_loser - expected_loser)

    return change_winner, change_loser

# レートを読み込む
def read_rates(rate_file):
    rates = {}
    with open(rate_file, 'r', encoding='utf-8') as file:
        for line in file:
            player, rate = line.strip().split()
            rates[player] = float(rate)
    print(f"[INFO] 現在のレートを読み込みました: {rates}")
    return rates

# レートを書き込む
def write_rates(rate_file, rates):
    with open(rate_file, 'w', encoding='utf-8') as file:
        for player, rate in sorted(rates.items(), key=lambda x: x[1], reverse=True):
            file.write(f"{player} {rate}\n")
    print(f"[INFO] レートを {rate_file} に保存しました")

# ログからレートを計算
def process_logs(log_file, input_rate_file, output_rate_file):
    rates = read_rates(input_rate_file)

    with open(log_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    game_logs = {}
    for line in lines:
        game_id, player, result = line.strip().split()
        if game_id not in game_logs:
            game_logs[game_id] = {'players': [], 'results': []}
        game_logs[game_id]['players'].append(player)
        game_logs[game_id]['results'].append(int(result))

    print(f"[INFO] {log_file} からゲームログを読み込みました。処理を開始します...")

    for game_id, data in game_logs.items():
        print(f"[INFO] ゲームID {game_id} の処理を開始します")

        players = data['players']
        results = data['results']

        if len(players) < 2:
            print(f"[WARNING] ゲームID {game_id} のプレイヤー数が足りないため、スキップします")
            continue

        winner_indices = [i for i, result in enumerate(results) if result == 1]
        loser_indices = [i for i, result in enumerate(results) if result == 0]

        if len(winner_indices) == 0 or len(loser_indices) == 0:
            print(f"[WARNING] ゲームID {game_id} の勝者または敗者が存在しないため、スキップします")
            continue

        winners = [players[i] for i in winner_indices]
        losers = [players[i] for i in loser_indices]

        print(f"[INFO] 勝者: {winners}, 敗者: {losers}")

        winner_ratings = [rates.get(winner, 1500) for winner in winners]
        loser_ratings = [rates.get(loser, 1500) for loser in losers]

        average_winner_rating = sum(winner_ratings) / len(winner_ratings)
        average_loser_rating = sum(loser_ratings) / len(loser_ratings)

        print(f"[INFO] 平均勝者レート: {average_winner_rating}, 平均敗者レート: {average_loser_rating}")

        change_winner, change_loser = calculate_elo_change(average_winner_rating, average_loser_rating)

        print(f"[INFO] 勝者レート変動: {change_winner}, 敗者レート変動: {change_loser}")

        for winner in winners:
            rates[winner] = rates.get(winner, 1500) + change_winner
            print(f"[INFO] プレイヤー {winner} の新しいレート: {rates[winner]}")

        for loser in losers:
            rates[loser] = rates.get(loser, 1500) + change_loser
            print(f"[INFO] プレイヤー {loser} の新しいレート: {rates[loser]}")

    # IDの計算が終わったらファイルに保存
    write_rates(output_rate_file, rates)
    print(f"[INFO] 処理が完了しました")

# kari_all_log.txtから戦績数をカウントして値を返す
def check_player_battle_num(player_trip):
    try:
        with open(kari_all_log_file, 'r', encoding='utf-8') as log_file:
            log_data = log_file.readlines()
    except FileNotFoundError:
        print("kari_all_log.txtから戦績数をカウントする際にエラーが発生しました")

    # プレイヤー名に対応する ID を探す
    player_id_count = 0
    for line in log_data:
        # 行がプレイヤー名を含むかチェック
        if player_trip in line:
            player_id_count += 1

    return player_id_count

# 入室した人が参戦だったら1を返し、観戦だったら0を返す
def check_player_to_play(name):
    player_data = get_players_data()

    for player_info in player_data['players'].values():
        if player_info.get('name') == name:
            if player_info.get('job') == '村人':
                return 1
            else:
                return 0
    return 0

# プレイヤー情報をAPIから取得し、json形式で返す(player_data)
def get_players_data():
    try:
        driver.get('https://zinro.net/m/api/?mode=players')
        html_tag = driver.find_element(By.TAG_NAME, 'pre')
        PL_json = html_tag.text
        return json.loads(PL_json)

    except Exception as e:
        print("プレイヤー情報を取得する際にエラーが発生しました")

# メッセージをAPIから取得し、message.txtに保存
def get_message_data():
    try:
        driver.get('https://zinro.net/m/api/?mode=message&id=all')
        html_tag = driver.find_element(By.TAG_NAME, 'pre')
        log_json = html_tag.text
        log_message(json.loads(log_json))

    except Exception as e:
        print("メッセージを取得する際にエラーが発生しました")

#仮ログを保存
def log_kari():
    player_data = get_players_data()

    trip_job_pairs = [(player_info['trip'], player_info['job']) for player_info in player_data['players'].values()
        if player_info.get('job') not in ["観戦者"] and player_info.get('trip')]

    with open(new_log_file, "w", encoding='utf-8') as file:
        for trip, job in trip_job_pairs:
            team = categorize_team(job)
            if team:
                result = 1 if team == win_team else 0
                file.write(f"1 {trip} {result}\n")

# ファイルを別のファイルにコピー
def copy(source_file,target_file):
    try:
        with open(source_file, 'r', encoding='utf-8') as src:
            content = src.read()

        with open(target_file, 'w', encoding='utf-8') as dest:
            dest.write(content)

        print(f"{source_file} の内容を {target_file} に上書きしました")

    except FileNotFoundError:
        print(f"{source_file} または {target_file} が見つかりません")
    except IOError:
        print(f"{source_file}を{target_file}にコピーする際にエラーが発生しました")

# ファイルを別のファイルに書き加える
def add(source_file,target_file):
    try:
        with open(source_file, 'r', encoding='utf-8') as src:
            content = src.read()
    except FileNotFoundError:
        print(f"{source_file} が見つかりません")

    try:
        with open(target_file, 'a', encoding='utf-8') as dest:
            dest.write(content)
            print(f"{source_file} の内容を {target_file} に書き加えました")
    except FileNotFoundError:
        print(f"{target_file} が見つかりません")

def write_rates(rate_file, rates):
    with open(rate_file, 'w', encoding='utf-8') as file:
        for player, rate in sorted(rates.items(), key=lambda x: x[1], reverse=True):
            file.write(f"{player} {rate}\n")
    print(f"[INFO] レートを {rate_file} に保存しました")
    print(f"[DEBUG] 現在のレート: {rates}")


#================================================================================================================================================

# ファイル名
setting_file = 'settings.txt'
rate_file = 'data/rate.txt'
all_log_file = 'data/all_log.txt'
kari_all_log_file = 'data/kari_all_log.txt'
ware_file = 'data/ware.txt'
message_file = 'data/message.txt'
new_log_file = 'data/new_log.txt'
use_rate_file = 'data/use_rate.txt'

# 実行されているディレクトリに移動
exe_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(exe_dir)

# 管理者を設定
root_trip = read_nth_line(setting_file,2)

# seleniumの設定
driver_path = os.path.join(exe_dir, 'chrome', 'chromedriver')
service = Service(driver_path)
driver = webdriver.Chrome(service=service)
driver.set_window_size(900, 800)

# 村に入る
while True:
    driver.get("https://zinro.net/m/room_list.php")
    time.sleep(40)
    try:
        driver.get('https://zinro.net/m/api/?mode=message&id=all')
        if driver.find_element(By.TAG_NAME, 'pre').text:
            break
        else:
            continue

    except WebDriverException:
        continue

# ウィンドウを最小化
driver.minimize_window()

"""人狼パワーを更新"""
# new_log.txtを空にする
with open(new_log_file, 'w', encoding='utf-8') as file:
    pass

# ログ取得の開始日時と終了日時を設定
date_format = "%Y-%m-%d %H:%M:%S"
start_str = read_nth_line(setting_file,8).strip()
time_obj = datetime.strptime(start_str, date_format)

# 最後に取得した時刻の1秒後の時刻から開始するようにする（同じログを2回取得しないため）
start = (time_obj + timedelta(seconds=1)).strftime(date_format)

# 1時間前までのログを取得
end = (datetime.now() - timedelta(hours=1)).strftime(date_format)

get_logs("人狼-2,占い師-1,狩人-1,霊能者-1,狂人-1,村人-4,役欠け:あり", start, end)
get_logs("人狼-2,占い師-1,狩人-1,霊能者-1,狂人-1,村人-4,役欠け:なし", start, end)

# new_log.txtをidが小さい順にソート
with open(new_log_file, 'r', encoding='utf-8') as file:
    lines = file.readlines()

sorted_lines = sorted(lines, key=lambda x: int(x.split()[0]))

with open(new_log_file, 'w', encoding='utf-8') as file:
    file.writelines(sorted_lines)

# new_log.txtから割れトリップを削除
remove_waretrip(new_log_file,ware_file)

# レートの計算処理
input_rate_file = rate_file
output_rate_file = rate_file
process_logs(new_log_file, input_rate_file, output_rate_file)

# rate.txtをuse_rate.txtにコピー
copy(rate_file,use_rate_file)

# new_log.txtをall_log.txtに追加
add(new_log_file,all_log_file)

# all_log.txtをkari_all_log.txtにコピー
copy(all_log_file,kari_all_log_file)

# settings.txtの計測済みの日時を更新
write_nth_line(setting_file,8,end)

# レート情報をuse_rate.txtから読み込み
rate_dict = {}
with open(use_rate_file, "r", encoding='utf-8') as file:
    for line in file:
        parts = line.split()
        id = parts[0]
        rate = float(parts[1])
        rate_dict[id] = rate
sorted_rates = sorted(rate_dict.values(), reverse=True)

# メッセージカウント変数
message_count = 0
# ゲーム中か判定（1はゲーム中、0はゲーム中でない）
game = 0
# 時刻の初期設定
start_time = time.time()

# メインの処理
while True:
    # メッセージを取得
    get_message_data()
    new_message_count = count_message()
    read_lines = new_message_count - message_count

    for read_line in range(1,read_lines + 1):
        line = read_message(message_count + read_line).strip()

        if '：' in line:
            speaker, message = line.split("：", 1)

            """一般コマンド"""
            # #ウデマエでウデマエ表示
            if "#ウデマエ" in message:

                speaker_trip = get_trip(speaker)
                battle_num = check_player_battle_num(speaker_trip)

                if battle_num < 7:
                    need_battle_num = 7 - battle_num

                    if game == 1:
                        speak_in_spirit_world(f"{speaker}（{speaker_trip}）さんのウデマエは C （10a狩をあと{need_battle_num}戦すると計測完了） です。")
                        time.sleep(2)
                    else:
                        whisper(speaker,f"{speaker}（{speaker_trip}）さんのウデマエは C （10a狩をあと{need_battle_num}戦すると計測完了） です。")
                        time.sleep(2)
                else:
                    udemae,z_power = get_rank(speaker_trip)

                    if game == 1:
                        speak_in_spirit_world(f"{speaker}（{speaker_trip}）さんのウデマエは {udemae} （{z_power}） です。")
                        time.sleep(2)
                    else:
                        whisper(speaker,f"{speaker}（{speaker_trip}）さんのウデマエは {udemae} （{z_power}） です。")
                        time.sleep(2)

            # #タイマーでカウント開始
            if "#タイマー" in message:
                parts = message.split()
                if len(parts) < 2:
                    speak("時間を設定できていません。")
                else:
                    wait_time = parts[1]

                    if wait_time.isdigit():
                        int_wait_time = int(wait_time)

                        if int_wait_time > 60:
                            speak("カウントできるのは60秒までです。")
                        else:
                            speak(f"計測を開始します。（{int_wait_time}秒）")
                            time.sleep(int_wait_time)
                            speak(f"{wait_time}秒が経過しました。")
                    else:
                        speak("時間を設定できていません。")

            """rootコマンド"""
            # #部屋パワー で部屋パワーを伝える
            if "#部屋パワー" in message:
                trip = get_trip(speaker)

                if trip == root_trip:
                    # 村人のtripを取得し、rate.txtからレートを取得
                    player_data = get_players_data()

                    # 'players'キーの下の辞書から、jobが「村人」であり、tripが空でないプレイヤーのtripを取得する
                    valid_trips = [player_info['trip'] for player_info in player_data['players'].values()
                        if player_info.get('job') == '村人' and player_info.get('trip')]

                    rates = [rate_dict.get(trip, 1500) for trip in valid_trips]
                    # ステップ3: 平均を計算
                    average_rate = sum(rates) / len(rates)
                    ave_zinro_power = math.floor(average_rate * 10) / 10

                    if game == 1:
                        speak_in_spirit_world(f"この部屋の平均人狼パワーは {ave_zinro_power} です。")
                        time.sleep(2)
                    else:
                        speak(f"この部屋の平均人狼パワーは {ave_zinro_power} です。")
                        time.sleep(2)

            # #退室でbotを退出させる
            if "#退室" in message:
                trip = get_trip(speaker)

                if trip == root_trip:
                    driver.get("http://zinro.net/m/player.php?mode=end")
                    time.sleep(3)
                    driver.quit()

            # #開始 でタイマーを開始する
            if "#開始" in message:
                trip = get_trip(speaker)

                if trip == root_trip:
                    speak("村の設定は【再投票:オン,白ランダム:オン】です。")

                    # 村人のtripを取得し、rate.txtからレートを取得
                    player_data = get_players_data()

                    # 'players'キーの下の辞書から、jobが「村人」であり、tripが空でないプレイヤーのtripを取得する
                    valid_trips = [player_info['trip'] for player_info in player_data['players'].values()
                        if player_info.get('job') == '村人' and player_info.get('trip')]

                    rates = [rate_dict.get(trip, 1500) for trip in valid_trips]
                    # ステップ3: 平均を計算
                    average_rate = sum(rates) / len(rates)
                    ave_zinro_power = math.floor(average_rate * 10) / 10

                    speak(f"この部屋の平均人狼パワーは {ave_zinro_power} です。")
                    time.sleep(2)

                    start_time = time.time()
                    game = 1

            """その他の機能"""
            # 割れトリップを検知
            if "さんが入室しました" in message:
                if speaker == '鯖':
                    # プレイヤー名を取得
                    parts = message.split('さん')
                    player_name = parts[0].strip()

                    # プレイヤーが参戦か観戦か判定
                    if check_player_to_play(player_name) == 1:
                        player_trip = get_trip(player_name)
                        # プレイヤー名がware.txtにあった場合、警告する
                        if check_player(ware_file,player_trip) == 1:
                            speak(f"【警告】{player_name}さんのトリップは割れトリップです。")

            # ゲームが終了したら試合時間を伝える
            if "の勝利です!" in message:
                if speaker == '鯖':
                    end_time = time.time()
                    elapsed_time_seconds = end_time - start_time
                    elapsed_time_minutes = elapsed_time_seconds / 60
                    gametime = math.floor(elapsed_time_minutes)
                    time.sleep(3)
                    speak(f"試合時間は{gametime}分でした。")
                    time.sleep(3)

                    game = 0

                    """結果から人狼パワーを更新する"""
                    # 勝ったチームを判定('人狼''村人'のどちらか)
                    match = re.search(r'【(.*?)】', message)
                    win_team = match.group(1).replace('チーム', '')

                    # 仮ログをnew_log.txtに上書き
                    log_kari()

                    # new_log.txtから割れトリップを削除
                    remove_waretrip(new_log_file,ware_file)

                    #仮ログからuse_rate.txtを更新
                    input_rate_file = use_rate_file
                    output_rate_file = use_rate_file
                    process_logs(new_log_file, input_rate_file, output_rate_file)

                    # レート情報をuse_rate.txtから読み込み
                    rate_dict = {}
                    with open(use_rate_file, "r", encoding='utf-8') as file:
                        for line in file:
                            parts = line.split()
                            id = parts[0]
                            rate = float(parts[1])
                            rate_dict[id] = rate

                    sorted_rates = sorted(rate_dict.values(), reverse=True)

                    # new_log.txtをkari_all_log.txtに加える
                    add(new_log_file,kari_all_log_file)

            elif "ゲームを中断しました" in message:
                if speaker == '鯖':
                    end_time = time.time()
                    elapsed_time_seconds = end_time - start_time
                    elapsed_time_minutes = elapsed_time_seconds / 60
                    gametime = math.floor(elapsed_time_minutes)
                    time.sleep(3)
                    speak(f"試合時間は{gametime}分でした。")
                    time.sleep(3)

                    game = 0

    message_count = message_count + read_lines
    time.sleep(5)
