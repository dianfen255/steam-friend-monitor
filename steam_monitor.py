import requests
import time
import threading
import json
import os
import csv
import sys
import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog

# ===== 托盘依赖 =====
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("请安装 pystray 和 Pillow：pip install pystray Pillow")
    sys.exit(1)

# ========== 基础目录 ==========
def get_base_dir():
    """获取程序运行的基础目录（打包后为 exe 所在目录，未打包为脚本所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_data_path(filename):
    return os.path.join(get_base_dir(), filename)

# ========== 日志配置 ==========
def setup_logging():
    log_file = get_data_path('debug.log')
    handlers = [logging.FileHandler(log_file, encoding='utf-8', mode='w')]
    if not getattr(sys, 'frozen', False):
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__name__)

logger = setup_logging()
logger.info("========== 程序启动 (v2.5.0) ==========")

# ========== 版本号 ==========
VERSION = "2.5.0"

# ========== 国际化 (i18n) ==========
# 'zh' = 中文；'en' = English
LANG = 'zh'

I18N = {
    'zh': {
        'app_title': 'Steam好友视奸器 v{version}',
        'col_friend': '好友名称', 'col_status': '状态', 'col_game': '游戏',
        'log_frame': '最近状态/时长变化',
        'btn_settings': '设置', 'btn_game_names': '游戏名称', 'btn_track': '追踪设置',
        'btn_refresh': '立即刷新', 'btn_clear_log': '清空日志区',
        'interval': '刷新间隔: {n} 秒',
        'status_wait': '状态: 等待配置...',
        'status_no_api': '状态: 未配置 API 密钥，请点击“设置”',
        'status_loading': '状态: 正在加载好友列表...',
        'status_loaded': '状态: 共 {total} 位好友，追踪 {tracked} 人',
        'status_load_fail': '状态: 无法获取好友列表，请检查API密钥和网络',
        'status_fetching': '状态: 正在获取数据...',
        'status_no_tracked': '状态: 未设置追踪好友，请打开追踪设置',
        'status_updated': '状态: 最后更新 {time} | 追踪 {n} 人',
        'status_error': '状态: 出错 {err}',
        'menu_view_status': '查看状态记录', 'menu_view_playtime': '查看时长记录',
        'tray_tip': 'Steam好友视奸器', 'tray_show': '显示窗口', 'tray_refresh': '立即刷新',
        'tray_settings': '打开设置', 'tray_quit': '退出程序',
        'set_title': '设置 Steam API 密钥和 ID',
        'set_api': 'Steam Web API Key:', 'set_id': 'Steam 64位 ID:',
        'set_lang': '界面语言:',
        'set_close': '点击关闭按钮时:',
        'set_close_tray': '最小化至系统托盘（默认）', 'set_close_exit': '直接退出程序',
        'btn_save': '保存', 'btn_cancel': '取消', 'btn_close': '关闭', 'btn_apply': '应用',
        'err': '错误', 'ok': '成功', 'info': '提示', 'warn': '警告',
        'err_api_empty': 'API Key 和 Steam ID 不能为空',
        'ok_config_saved': '配置已保存。请重新启动监控或点击确定后手动刷新。',
        'gn_title': '编辑游戏名称映射',
        'gn_empty': '当前没有游戏映射数据。',
        'gn_col_id': '游戏ID', 'gn_col_name': '游戏名称',
        'gn_refresh': '刷新列表', 'gn_saved': '游戏名称映射已更新并生效！',
        'gn_edit_title': '编辑游戏名称',
        'gn_edit_prompt': '游戏ID: {appid}\n输入新名称：',
        'gn_dlg_saved': '游戏名称映射已更新！',
        'tr_title': '选择要追踪的好友',
        'tr_all': '全选', 'tr_none': '全不选',
        'tr_empty_warn': '未选中任何好友，这将导致没有数据显示。是否继续？',
        'tr_not_ready': '请稍等，好友列表尚未加载完成',
        'sr_title': '{name} - 状态记录',
        'sr_missing': '该好友尚无状态记录文件。\n{path}',
        'sr_col_ts': '时间戳', 'sr_col_type': '变更类型', 'sr_col_detail': '详情',
        'sr_col_game': '相关游戏',
        'pr_title': '{name} - 时长记录（增量）',
        'pr_missing': '该好友尚无时长记录文件。\n{path}',
        'pr_col_time': '时间', 'pr_col_game': '游戏名称', 'pr_col_delta': '本次增量(h)',
        'pr_col_total': '累计总时长(h)', 'pr_first': '首次',
        'pr_no_rows': 'CSV文件中没有数据行',
        'pr_rename': '重命名游戏',
        'pr_rename_prompt': '将游戏「{name}」重命名为：',
        'pr_no_id': '缺少游戏ID',
        'pr_no_id_prompt': '未找到「{name}」的游戏ID，请手动输入（数字）：',
        'err_read_fail': '读取文件失败：{err}',
        'log_started': '程序已启动，正在加载配置...',
        'log_loaded': '已加载 {total} 位好友，追踪 {tracked} 人',
        'log_status_change': '{name} 状态变更: {old} → {new}',
        'log_start_play': '{name} 开始游玩《{game}》',
        'log_missing': '{name} 连续{n}次未获取到数据（可能已移除或私密）',
        'log_first': '{name} 首次游玩《{game}》已累计 {h} 小时',
        'log_unprivate': '{name} 的游戏《{game}》已取消私密（公开）',
        'log_playtime': '{name} 在《{game}》中游戏总时长更新为 {h} 小时',
        'log_private': '{name} 的游戏《{game}》已被设为私密（隐藏）',
    },
    'en': {
        'app_title': 'Steam Friend Monitor v{version}',
        'col_friend': 'Friend', 'col_status': 'Status', 'col_game': 'Game',
        'log_frame': 'Recent Status / Playtime Changes',
        'btn_settings': 'Settings', 'btn_game_names': 'Game Names', 'btn_track': 'Tracking',
        'btn_refresh': 'Refresh Now', 'btn_clear_log': 'Clear Log',
        'interval': 'Refresh: {n}s',
        'status_wait': 'Status: Waiting for configuration...',
        'status_no_api': 'Status: API key not set, click "Settings"',
        'status_loading': 'Status: Loading friend list...',
        'status_loaded': 'Status: {total} friends, tracking {tracked}',
        'status_load_fail': 'Status: Failed to load friends, check API key and network',
        'status_fetching': 'Status: Fetching data...',
        'status_no_tracked': 'Status: No tracked friends, open Tracking',
        'status_updated': 'Status: Last update {time} | Tracking {n}',
        'status_error': 'Status: Error {err}',
        'menu_view_status': 'View Status Log', 'menu_view_playtime': 'View Playtime Log',
        'tray_tip': 'Steam Friend Monitor', 'tray_show': 'Show Window',
        'tray_refresh': 'Refresh Now', 'tray_settings': 'Open Settings', 'tray_quit': 'Exit',
        'set_title': 'Settings - Steam API Key & ID',
        'set_api': 'Steam Web API Key:', 'set_id': 'Steam 64-bit ID:',
        'set_lang': 'Language:',
        'set_close': 'When closing the window:',
        'set_close_tray': 'Minimize to system tray (default)', 'set_close_exit': 'Exit the program',
        'btn_save': 'Save', 'btn_cancel': 'Cancel', 'btn_close': 'Close', 'btn_apply': 'Apply',
        'err': 'Error', 'ok': 'Success', 'info': 'Notice', 'warn': 'Warning',
        'err_api_empty': 'API Key and Steam ID cannot be empty',
        'ok_config_saved': 'Configuration saved. Restart monitoring or refresh manually.',
        'gn_title': 'Edit Game Name Mapping',
        'gn_empty': 'No game mapping data available.',
        'gn_col_id': 'App ID', 'gn_col_name': 'Game Name',
        'gn_refresh': 'Refresh List', 'gn_saved': 'Game name mapping updated!',
        'gn_edit_title': 'Edit Game Name',
        'gn_edit_prompt': 'App ID: {appid}\nEnter new name:',
        'gn_dlg_saved': 'Game name mapping updated!',
        'tr_title': 'Select Friends to Track',
        'tr_all': 'Select All', 'tr_none': 'Select None',
        'tr_empty_warn': 'No friends selected, no data will be shown. Continue?',
        'tr_not_ready': 'Please wait, the friend list is still loading',
        'sr_title': '{name} - Status Log',
        'sr_missing': 'No status log file for this friend.\n{path}',
        'sr_col_ts': 'Timestamp', 'sr_col_type': 'Change Type', 'sr_col_detail': 'Detail',
        'sr_col_game': 'Related Game',
        'pr_title': '{name} - Playtime Log (Delta)',
        'pr_missing': 'No playtime log file for this friend.\n{path}',
        'pr_col_time': 'Time', 'pr_col_game': 'Game Name', 'pr_col_delta': 'Delta (h)',
        'pr_col_total': 'Total (h)', 'pr_first': 'First',
        'pr_no_rows': 'No data rows in CSV file',
        'pr_rename': 'Rename Game',
        'pr_rename_prompt': 'Rename "{name}" to:',
        'pr_no_id': 'Missing App ID',
        'pr_no_id_prompt': 'App ID not found for "{name}", please enter it (number):',
        'err_read_fail': 'Failed to read file: {err}',
        'log_started': 'Program started, loading configuration...',
        'log_loaded': 'Loaded {total} friends, tracking {tracked}',
        'log_status_change': '{name} status changed: {old} → {new}',
        'log_start_play': '{name} started playing "{game}"',
        'log_missing': '{name} has no data for {n} consecutive checks (removed or private?)',
        'log_first': '{name} first recorded playing "{game}", {h}h total',
        'log_unprivate': '{name}\'s game "{game}" is now public',
        'log_playtime': '{name}\'s playtime in "{game}" updated to {h}h',
        'log_private': '{name}\'s game "{game}" has been set to private',
    },
}

# 状态文本（parse_status 产生的中文）到英文的映射
_STATUS_EN = {
    '在线': 'Online', '忙碌': 'Busy', '离开': 'Away', '打盹': 'Snooze',
    '想交易': 'Looking to Trade', '想玩游戏': 'Looking to Play', '离线': 'Offline',
}
_STATUS_SUB_EN = {'离开': 'Away', '打盹': 'Snooze'}


def t(key, **kwargs):
    """按当前语言取界面文本；缺失时回退中文，再回退 key 本身。"""
    table = I18N.get(LANG) or I18N['zh']
    text = table.get(key) or I18N['zh'].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def translate_status(text):
    """把 parse_status 产生的中文状态文本转换为当前语言（中文环境原样返回）。"""
    if LANG == 'zh':
        return text
    m = re.match(r'^游戏中\((离开|打盹)\) - (.*)$', text)
    if m:
        return f"In-Game ({_STATUS_SUB_EN.get(m.group(1), m.group(1))}) - {m.group(2)}"
    m = re.match(r'^游戏中 - (.*)$', text)
    if m:
        return f"In-Game - {m.group(1)}"
    return _STATUS_EN.get(text, text)


# ========== 配置文件路径 ==========
CONFIG_FILE = get_data_path('config.json')
logger.debug(f"配置文件路径: {CONFIG_FILE}")
# ========== 配置管理 ==========
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            lang = config.get('LANG', 'zh')
            if lang not in ('zh', 'en'):
                lang = 'zh'
            close_action = config.get('CLOSE_ACTION', 'tray')
            if close_action not in ('tray', 'exit'):
                close_action = 'tray'
            refresh_interval = config.get('REFRESH_INTERVAL', 60)
            api_key = config.get('API_KEY', '').strip()
            steam_id = config.get('STEAM_ID', '').strip()
            if api_key and steam_id and api_key != "YOUR_API_KEY_HERE":
                logger.info("配置加载成功")
                return api_key, steam_id, refresh_interval, close_action, lang
            # 即使未配置 API，也保留语言与关闭行为设置
            return None, None, refresh_interval, close_action, lang
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
    logger.warning("配置无效或不存在")
    return None, None, 60, 'tray', 'zh'

def save_config(api_key, steam_id, refresh_interval=60, close_action='tray', lang='zh'):
    config = {
        "API_KEY": api_key,
        "STEAM_ID": steam_id,
        "REFRESH_INTERVAL": refresh_interval,
        "CLOSE_ACTION": close_action,
        "LANG": lang
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
    logger.info("配置已保存")

# ========== 全局变量 ==========
API_KEY = None
STEAM_ID = None
REFRESH_INTERVAL = 60
CLOSE_ACTION = 'tray'  # 点击关闭按钮的行为：'tray' 缩到系统托盘（默认）；'exit' 直接退出程序

# ========== 其他配置文件路径 ==========
TRACKED_FILE = get_data_path("tracked_friends.json")
PLAYTIME_HISTORY_FILE = get_data_path("playtime_history.json")
GAME_NAMES_FILE = get_data_path("game_names.json")
LOG_DIR = get_data_path("logs")
# ========== 游戏名称映射文件管理 ==========
def ensure_game_names_file():
    if not os.path.exists(GAME_NAMES_FILE):
        logger.info("game_names.json 不存在，创建默认文件")
        initial_data = {
            "_comment": "在此文件中添加游戏ID到名称的映射。格式：\"游戏ID\": \"游戏名称\"。例如：\"730\": \"Counter-Strike 2\""
        }
        with open(GAME_NAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=4, ensure_ascii=False)
    with open(GAME_NAMES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_game_names_file(data):
    if "_comment" not in data:
        data["_comment"] = "在此文件中添加游戏ID到名称的映射。格式：\"游戏ID\": \"游戏名称\"。例如：\"730\": \"Counter-Strike 2\""
    with open(GAME_NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_mapping_batch(new_names, missing_ids):
    """批量更新映射文件（一次性读写，避免逐条 IO）。
    new_names: {appid_str: name}，仅在映射中无该 ID 或名称为空时写入（不覆盖手动自定义）。
    missing_ids: 可迭代的 appid，缺失时写入空串占位。"""
    if not new_names and not missing_ids:
        return
    try:
        with open(GAME_NAMES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    changed = False
    for appid_str, name in new_names.items():
        existing = data.get(appid_str, '')
        if (not existing) and name:
            data[appid_str] = name
            changed = True
            logger.info(f"自动写入游戏名称: {appid_str} -> {name}")
    for appid_str in missing_ids:
        if appid_str not in data and appid_str != "_comment":
            data[appid_str] = ""
            changed = True
            logger.info(f"添加缺失游戏ID: {appid_str}")
    if changed:
        save_game_names_file(data)

def load_game_name_mapping():
    ensure_game_names_file()
    with open(GAME_NAMES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if "_comment" in data:
        del data["_comment"]
    logger.debug(f"加载游戏映射，共 {len(data)} 条")
    return data

def update_game_name(appid, new_name):
    data = load_game_name_mapping()
    data[str(appid)] = new_name
    full_data = {"_comment": "在此文件中添加游戏ID到名称的映射。格式：\"游戏ID\": \"游戏名称\"。例如：\"730\": \"Counter-Strike 2\""}
    full_data.update(data)
    save_game_names_file(full_data)
    logger.info(f"更新游戏名称: {appid} -> {new_name}")

# ========== API 函数 ==========
def get_steam_friends():
    if not API_KEY or not STEAM_ID:
        logger.error("API_KEY 或 STEAM_ID 未设置")
        return []
    url = f"http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={API_KEY}&steamid={STEAM_ID}&relationship=friend"
    try:
        logger.debug(f"请求好友列表: {url}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        friends = [f['steamid'] for f in data.get('friendslist', {}).get('friends', [])]
        logger.info(f"获取到 {len(friends)} 位好友")
        return friends
    except Exception as e:
        logger.error(f"获取好友列表失败: {e}")
        return []

def get_player_summaries(steam_ids):
    if not steam_ids or not API_KEY:
        return []
    all_players = []
    batch_size = 100
    for i in range(0, len(steam_ids), batch_size):
        batch = steam_ids[i:i+batch_size]
        ids_param = ','.join(batch)
        url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={API_KEY}&steamids={ids_param}"
        try:
            logger.debug(f"请求好友状态，数量: {len(batch)}")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            players = resp.json().get('response', {}).get('players', [])
            all_players.extend(players)
            logger.info(f"本批次获取到 {len(players)} 位好友状态")
        except Exception as e:
            logger.error(f"获取好友状态批次失败: {e}")
    logger.info(f"总共获取到 {len(all_players)} 位好友状态")
    return all_players

def parse_status(player):
    personastate = player.get('personastate', 0)
    if personastate == 1:
        status = '在线'
    elif personastate == 2:
        status = '忙碌'
    elif personastate == 3:
        status = '离开'
    elif personastate == 4:
        status = '打盹'
    elif personastate == 5:
        status = '想交易'
    elif personastate == 6:
        status = '想玩游戏'
    else:
        status = '离线'
    game = player.get('gameextrainfo', '')
    if game:
        if personastate in (3, 4):
            # 好友处于离开/打盹状态，但同时正在玩游戏
            status = f'游戏中({status}) - {game}'
        else:
            status = f'游戏中 - {game}'
    return status, game

def get_friends_lifetime_playtime(steam_ids, game_name_mapping):
    if not steam_ids or not API_KEY:
        return {}
    all_data = {}
    new_names = {}
    missing_ids = set()

    def fetch_one(sid):
        """拉取好友的游戏时长。合并两个数据源：
        1) GetOwnedGames：玩家拥有的游戏（含付费/免费游戏）
        2) GetRecentlyPlayedGames：最近两周玩过的应用，用于覆盖家庭共享游戏和免费软件（如 OBS）
        两者都提供 playtime_forever 总时长字段。"""
        merged = {}
        # 数据源 1：拥有的游戏
        owned_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={API_KEY}&steamid={sid}&include_played_free_games=true&include_appinfo=true"
        resp = requests.get(owned_url, timeout=15)
        resp.raise_for_status()
        for g in resp.json().get('response', {}).get('games', []):
            merged[g['appid']] = {
                'appid': g['appid'],
                'name': g.get('name', '').strip(),
                'playtime_forever': g.get('playtime_forever', 0),
                'source': 'owned',
            }
        # 数据源 2：最近玩过的游戏（补充共享游戏和免费软件）
        try:
            recent_url = f"http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?key={API_KEY}&steamid={sid}"
            r = requests.get(recent_url, timeout=15)
            r.raise_for_status()
            for g in r.json().get('response', {}).get('games', []):
                appid = g['appid']
                if appid not in merged:
                    merged[appid] = {
                        'appid': appid,
                        'name': g.get('name', '').strip(),
                        'playtime_forever': g.get('playtime_forever', 0),
                        'source': 'recent',
                    }
                else:
                    # 已存在时取两者较大的总时长，并补全缺失的名称
                    merged[appid]['playtime_forever'] = max(
                        merged[appid]['playtime_forever'], g.get('playtime_forever', 0))
                    if not merged[appid]['name'] and g.get('name'):
                        merged[appid]['name'] = g.get('name', '').strip()
        except Exception as e:
            logger.warning(f"获取好友 {sid} 最近游玩列表失败（忽略，继续）: {e}")
        return list(merged.values())

    # 并发拉取所有好友的游戏列表
    raw_results = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(steam_ids)))) as executor:
        future_to_sid = {executor.submit(fetch_one, sid): sid for sid in steam_ids}
        for future in as_completed(future_to_sid):
            sid = future_to_sid[future]
            try:
                raw_results[sid] = future.result()
            except Exception as e:
                logger.error(f"获取好友 {sid} 游戏时长失败: {e}")
                raw_results[sid] = []

    # 统一解析名称并收集映射更新
    for sid in steam_ids:
        games = raw_results.get(sid, [])
        play_dict = {}
        for g in games:
            appid = g['appid']
            appid_str = str(appid)
            game_name_from_api = g.get('name', '').strip()
            mapping_name = game_name_mapping.get(appid_str, '').strip()
            if mapping_name:
                # 映射文件中已有（手动自定义的）名称，优先使用
                final_name = mapping_name
            elif game_name_from_api:
                # 映射中没有，但 API 返回了名称：使用它、同步进内存映射并批量写入文件
                final_name = game_name_from_api
                new_names[appid_str] = game_name_from_api
                game_name_mapping[appid_str] = game_name_from_api
            else:
                # 映射和 API 都没有名称：记录缺失 ID，用 ID 兜底
                missing_ids.add(appid_str)
                final_name = f"游戏ID:{appid}"
            play_dict[appid] = {
                'name': final_name,
                'playtime_minutes': g.get('playtime_forever', 0),
                'source': g.get('source', 'owned'),
            }
        all_data[sid] = play_dict
        logger.debug(f"好友 {sid} 共有 {len(play_dict)} 款游戏")

    # 一次性批量写入映射文件
    update_mapping_batch(new_names, missing_ids)
    return all_data

# ========== 日志与配置 ==========
def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

def log_friend_change(steam_id, friend_name, change_type, detail, game_name=""):
    ensure_log_dir()
    safe_name = "".join(c for c in friend_name if c not in r'\/:*?"<>|')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if change_type == "状态变更":
        filename = os.path.join(LOG_DIR, f"{safe_name}_{steam_id}_status.csv")
        header = ["时间戳", "变更类型", "详情", "相关游戏"]
        row = [timestamp, change_type, detail, game_name]
    else:
        filename = os.path.join(LOG_DIR, f"{safe_name}_{steam_id}_playtime.csv")
        header = ["时间戳", "游戏名称", "详情", "总时长(小时)"]
        if change_type == "时长变化":
            match = re.search(r'(\d+(?:\.\d+)?)\s*小时$', detail)
            new_hours = match.group(1) if match else ""
            row = [timestamp, game_name, detail, new_hours]
        else:
            row = [timestamp, game_name, detail, ""]
    
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row)
    logger.debug(f"记录变更: {friend_name} {change_type}")

def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_tracked(tracked_set):
    with open(TRACKED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(tracked_set), f, indent=2)

def load_playtime_history():
    if os.path.exists(PLAYTIME_HISTORY_FILE):
        with open(PLAYTIME_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for sid, games in data.items():
            for appid, value in games.items():
                if isinstance(value, (int, float)):
                    games[appid] = {"minutes": value, "visible": True}
        return data
    return {}

def save_playtime_history(history):
    with open(PLAYTIME_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ========== 状态记录窗口 ==========
def show_status_records(friend_name, steam_id):
    logger.debug(f"打开状态记录窗口: {friend_name} ({steam_id})")
    safe_name = "".join(c for c in friend_name if c not in r'\/:*?"<>|')
    filename = os.path.join(LOG_DIR, f"{safe_name}_{steam_id}_status.csv")
    if not os.path.exists(filename):
        logger.warning(f"状态记录文件不存在: {filename}")
        messagebox.showinfo(t('info'), t('sr_missing', path=filename))
        return
    win = tk.Toplevel()
    win.title(t('sr_title', name=friend_name))
    win.geometry("900x500")
    win.resizable(True, True)
    columns = ("ts", "type", "detail", "game")
    headings = {"ts": t('sr_col_ts'), "type": t('sr_col_type'),
                "detail": t('sr_col_detail'), "game": t('sr_col_game')}
    tree = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=headings[col])
        tree.column(col, width=180)
    tree.column("detail", width=250)
    tree.column("game", width=150)
    vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(win, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            row_count = 0
            for row in reader:
                if len(row) >= 4:
                    tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3]))
                else:
                    tree.insert("", tk.END, values=(row[0], row[1], row[2], ""))
                row_count += 1
        logger.info(f"状态记录窗口显示 {row_count} 条记录")
    except Exception as e:
        logger.error(f"读取状态记录文件失败: {e}")
        messagebox.showerror(t('err'), t('err_read_fail', err=e))

# ========== 时长记录窗口（显示增量） ==========
def show_playtime_records(friend_name, steam_id):
    logger.debug(f"打开时长记录窗口: {friend_name} ({steam_id})")
    safe_name = "".join(c for c in friend_name if c not in r'\/:*?"<>|')
    filename = os.path.join(LOG_DIR, f"{safe_name}_{steam_id}_playtime.csv")
    if not os.path.exists(filename):
        logger.warning(f"时长记录文件不存在: {filename}")
        messagebox.showinfo(t('info'), t('pr_missing', path=filename))
        return

    records = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 2:
                    ts = row[0].strip()
                    game_raw = row[1].strip()
                    hours = row[3].strip() if len(row) > 3 else ""
                    if ts and game_raw:
                        records.append((ts, game_raw, hours))
        logger.info(f"从CSV读取到 {len(records)} 条记录")
    except Exception as e:
        logger.error(f"读取时长记录文件失败: {e}")
        messagebox.showerror(t('err'), t('err_read_fail', err=e))
        return

    if not records:
        logger.warning("CSV文件中没有数据行")
        messagebox.showinfo(t('info'), t('pr_no_rows'))
        return

    # 计算每条记录的增量（相邻两次同游戏总时长的差值）
    last_total = {}
    detail_rows = []  # (ts, game_raw, delta_str, total_str)
    for ts, game_raw, hours in records:
        try:
            total = float(hours) if hours else 0.0
        except (ValueError, TypeError):
            total = 0.0
        prev = last_total.get(game_raw)
        if prev is None:
            delta_str = t('pr_first')
        else:
            delta = total - prev
            if delta < 0:
                delta = 0.0
            delta_str = f"+{delta:.1f}"
        last_total[game_raw] = total
        # 时间戳去掉秒，便于阅读
        try:
            ts_disp = ts[:16]
        except:
            ts_disp = ts
        detail_rows.append((ts_disp, game_raw, delta_str, f"{total:.1f}"))

    if not detail_rows:
        logger.warning("没有时长数据")
        messagebox.showinfo(t('info'), t('pr_no_rows'))
        return

    # 最新记录在前
    detail_rows.reverse()

    win = tk.Toplevel()
    win.title(t('pr_title', name=friend_name))
    win.geometry("760x560")
    win.resizable(True, True)

    columns = ("time", "gname", "delta", "total")
    tree = ttk.Treeview(win, columns=columns, show="headings")
    tree.heading("time", text=t('pr_col_time'))
    tree.heading("gname", text=t('pr_col_game'))
    tree.heading("delta", text=t('pr_col_delta'))
    tree.heading("total", text=t('pr_col_total'))
    tree.column("time", width=140, anchor="center")
    tree.column("gname", width=260, anchor="w")
    tree.column("delta", width=90, anchor="center")
    tree.column("total", width=100, anchor="center")

    vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    for ts, game_raw, delta_str, total_str in detail_rows:
        tree.insert("", tk.END, values=(ts, game_raw, delta_str, total_str))

    logger.info(f"时长记录表格插入 {len(detail_rows)} 行")

    def on_right_click(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        values = tree.item(item, "values")
        if not values or len(values) < 2:
            return
        game_name = values[1]
        # 先尝试「游戏ID:xxx」格式直接提取
        m = re.match(r'^游戏ID:(\d+)$', game_name)
        if m:
            appid = m.group(1)
        else:
            # 否则从映射文件反查游戏名对应的 appid
            appid = None
            mapping = load_game_name_mapping()
            for aid, name in mapping.items():
                if name == game_name:
                    appid = aid
                    break
        if not appid:
            appid = simpledialog.askstring(t('pr_no_id'), t('pr_no_id_prompt', name=game_name), parent=win)
        if appid:
            new_name = simpledialog.askstring(t('pr_rename'), t('pr_rename_prompt', name=game_name), initialvalue=game_name, parent=win)
            if new_name and new_name.strip():
                update_game_name(appid, new_name.strip())
                win.destroy()
                show_playtime_records(friend_name, steam_id)
    tree.bind("<Button-3>", on_right_click)

# ========== 游戏名称编辑窗口 ==========
def edit_game_names(parent, refresh_callback):
    logger.info("打开游戏名称编辑窗口")
    mapping = load_game_name_mapping()
    if not mapping:
        messagebox.showinfo(t('info'), t('gn_empty'))
        return

    win = tk.Toplevel(parent)
    win.title(t('gn_title'))
    win.geometry("600x500")
    win.resizable(True, True)

    main_frame = ttk.Frame(win)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    columns = ("appid", "gname")
    tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)
    tree.heading("appid", text=t('gn_col_id'))
    tree.heading("gname", text=t('gn_col_name'))
    tree.column("appid", width=100, anchor="center")
    tree.column("gname", width=400)

    vsb = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    for appid, name in sorted(mapping.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        tree.insert("", tk.END, values=(appid, name))

    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)

    def save_changes():
        logger.info("保存游戏名称修改（增量更新）")
        current_items = {}
        for item in tree.get_children():
            values = tree.item(item, "values")
            if len(values) == 2:
                appid = values[0].strip()
                name = values[1].strip()
                if appid:
                    current_items[appid] = name
        try:
            with open(GAME_NAMES_FILE, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
        except:
            full_data = {}
        for appid, name in current_items.items():
            if name:
                full_data[appid] = name
            else:
                full_data[appid] = ""
        if "_comment" not in full_data:
            full_data["_comment"] = "在此文件中添加游戏ID到名称的映射。格式：\"游戏ID\": \"游戏名称\"。例如：\"730\": \"Counter-Strike 2\""
        save_game_names_file(full_data)
        logger.info("游戏名称映射已保存（增量更新）")
        if refresh_callback:
            refresh_callback()
        messagebox.showinfo(t('ok'), t('gn_saved'))

    ttk.Button(btn_frame, text=t('btn_save'), command=save_changes).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text=t('gn_refresh'), command=lambda: refresh_tree()).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text=t('btn_close'), command=win.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_tree():
        new_mapping = load_game_name_mapping()
        for item in tree.get_children():
            tree.delete(item)
        for appid, name in sorted(new_mapping.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            tree.insert("", tk.END, values=(appid, name))

    def on_double_click(event):
        item = tree.selection()[0] if tree.selection() else None
        if not item:
            return
        col = tree.identify_column(event.x)
        if col == "#2":
            values = tree.item(item, "values")
            if len(values) == 2:
                appid = values[0]
                current_name = values[1]
                new_name = simpledialog.askstring(t('gn_edit_title'), t('gn_edit_prompt', appid=appid), initialvalue=current_name, parent=win)
                if new_name is not None:
                    tree.item(item, values=(appid, new_name.strip()))

    tree.bind("<Double-1>", on_double_click)

# ========== 设置窗口 ==========
def open_settings(parent, on_save_callback):
    win = tk.Toplevel(parent)
    win.title(t('set_title'))
    win.geometry("430x390")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    ttk.Label(win, text=t('set_api')).pack(pady=(10,0), anchor=tk.W, padx=10)
    api_entry = ttk.Entry(win, width=54)
    api_entry.pack(pady=5, padx=10)
    api_entry.insert(0, API_KEY if API_KEY else "")
    ttk.Label(win, text=t('set_id')).pack(pady=(10,0), anchor=tk.W, padx=10)
    id_entry = ttk.Entry(win, width=54)
    id_entry.pack(pady=5, padx=10)
    id_entry.insert(0, STEAM_ID if STEAM_ID else "")

    #----- 界面语言 -----
    ttk.Label(win, text=t('set_lang')).pack(pady=(10,0), anchor=tk.W, padx=10)
    lang_var = tk.StringVar(value=LANG if LANG in ('zh', 'en') else 'zh')
    lang_frame = ttk.Frame(win)
    lang_frame.pack(pady=5, padx=10, anchor=tk.W)
    ttk.Radiobutton(lang_frame, text='中文', variable=lang_var, value='zh').pack(side=tk.LEFT, padx=(0, 15))
    ttk.Radiobutton(lang_frame, text='English', variable=lang_var, value='en').pack(side=tk.LEFT)

    #----- 关闭行为 -----
    ttk.Label(win, text=t('set_close')).pack(pady=(10,0), anchor=tk.W, padx=10)
    close_action_var = tk.StringVar(value=CLOSE_ACTION if CLOSE_ACTION in ('tray', 'exit') else 'tray')
    close_frame = ttk.Frame(win)
    close_frame.pack(pady=5, padx=10, anchor=tk.W)
    ttk.Radiobutton(close_frame, text=t('set_close_tray'), variable=close_action_var, value='tray').pack(anchor=tk.W)
    ttk.Radiobutton(close_frame, text=t('set_close_exit'), variable=close_action_var, value='exit').pack(anchor=tk.W)

    def save():
        new_api = api_entry.get().strip()
        new_id = id_entry.get().strip()
        if not new_api or not new_id:
            messagebox.showerror(t('err'), t('err_api_empty'))
            return
        global API_KEY, STEAM_ID, CLOSE_ACTION, LANG
        API_KEY = new_api
        STEAM_ID = new_id
        CLOSE_ACTION = close_action_var.get()
        LANG = lang_var.get()
        save_config(API_KEY, STEAM_ID, REFRESH_INTERVAL, CLOSE_ACTION, LANG)
        messagebox.showinfo(t('ok'), t('ok_config_saved'))
        win.destroy()
        if on_save_callback:
            on_save_callback()
    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=18)
    ttk.Button(btn_frame, text=t('btn_save'), command=save).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text=t('btn_cancel'), command=win.destroy).pack(side=tk.LEFT, padx=10)

# ========== GUI 应用 ==========
class SteamMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1300x700")
        self.root.resizable(True, True)
        logger.info("GUI 初始化")

        global API_KEY, STEAM_ID, REFRESH_INTERVAL, CLOSE_ACTION, LANG
        loaded_api, loaded_id, loaded_interval, loaded_close_action, loaded_lang = load_config()
        LANG = loaded_lang
        self._applied_lang = loaded_lang
        if loaded_api and loaded_id:
            API_KEY = loaded_api
            STEAM_ID = loaded_id
            REFRESH_INTERVAL = loaded_interval
            CLOSE_ACTION = loaded_close_action
        else:
            API_KEY = None
            STEAM_ID = None
            REFRESH_INTERVAL = 60
            CLOSE_ACTION = 'tray'
        self.root.title(t('app_title', version=VERSION))

        self.last_status = {}
        self.last_playtime_history = load_playtime_history()
        self.tracked_set = load_tracked()
        self.all_friends_ids = []
        self.all_friends_info = {}
        self.game_name_mapping = load_game_name_mapping()

        self.running = True
        self.refresh_lock = threading.Lock()
        self.refresh_thread = None
        self._refresh_running = False

        # 连续缺失计数
        self.missing_count = {}

        # ----- 托盘相关 -----
        self.tray_icon = None
        self.tray_thread = None
        self.create_tray_icon()
        self.start_tray_icon()

        self.create_widgets()
        self.add_log(t('log_started'))

        if not API_KEY or not STEAM_ID:
            logger.warning("API_KEY 或 STEAM_ID 缺失，弹出设置窗口")
            self.root.after(100, lambda: open_settings(self.root, self.on_settings_saved))
        else:
            self.start_monitoring()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ===== 托盘相关方法 =====
    def _build_tray_menu(self):
        """按当前语言构建托盘菜单（语言切换时可重建）。"""
        return (
            pystray.MenuItem(t('tray_show'), self.show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t('tray_refresh'), self.tray_refresh),
            pystray.MenuItem(t('tray_settings'), self.tray_open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t('tray_quit'), self.quit_app),
        )

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='#2d89ef')
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 54, 54), fill='white')
        self.tray_icon = pystray.Icon("steam_monitor", image, t('tray_tip'), self._build_tray_menu())

    def refresh_tray_menu(self):
        """语言切换后刷新已运行托盘图标的菜单与提示文字。"""
        if not self.tray_icon:
            return
        try:
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.title = t('tray_tip')
            self.tray_icon.update_menu()
        except Exception as e:
            logger.warning(f"刷新托盘菜单失败: {e}")

    def start_tray_icon(self):
        """程序启动时即运行托盘图标（后台线程）。"""
        if self.tray_icon and not self.tray_icon._running:
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def tray_refresh(self, icon=None, item=None):
        """托盘菜单：立即刷新。"""
        self.show_window()
        self.async_refresh()

    def tray_open_settings(self, icon=None, item=None):
        """托盘菜单：打开设置窗口。"""
        self.show_window()
        open_settings(self.root, self.on_settings_saved)

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.running = False
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.refresh_thread.join(timeout=2)
        self.root.quit()
        self.root.destroy()

    def on_closing(self):
        """点击关闭按钮：根据 CLOSE_ACTION 决定缩到托盘还是退出。"""
        if CLOSE_ACTION == 'exit':
            self.quit_app()
        else:
            self.root.withdraw()
    # =========================

    def start_monitoring(self):
        logger.info("启动监控线程")
        if self.refresh_thread is None or not self.refresh_thread.is_alive():
            self.refresh_thread = threading.Thread(target=self.refresh_loop, daemon=True)
            self.refresh_thread.start()
        self.root.after(100, self.load_all_friends_for_setup)

    def on_settings_saved(self):
        self.apply_language()
        if API_KEY and STEAM_ID:
            self.start_monitoring()
        else:
            self.root.after(100, lambda: open_settings(self.root, self.on_settings_saved))

    def apply_language(self):
        """语言设置变更后重建主界面，使所有文本立即生效。"""
        if self._applied_lang == LANG:
            return
        self._applied_lang = LANG
        try:
            log_content = self.log_text.get("1.0", tk.END)
        except Exception:
            log_content = ""
        for w in self.root.winfo_children():
            w.destroy()
        self.root.title(t('app_title', version=VERSION))
        self.create_widgets()
        if log_content.strip():
            self.log_text.insert(tk.END, log_content)
            self.log_text.see(tk.END)
        self._update_table(self.last_status)
        # 恢复状态标签
        if not API_KEY or not STEAM_ID:
            self.status_label.config(text=t('status_no_api'), foreground="red")
        elif self.last_status:
            self.status_label.config(
                text=t('status_updated', time=datetime.now().strftime('%H:%M:%S'), n=len(self.tracked_set)),
                foreground="green")
        self.refresh_tray_menu()
        logger.info(f"界面语言已切换为 {LANG}")

    def refresh_game_mapping(self):
        logger.info("热更新游戏名称映射")
        self.game_name_mapping = load_game_name_mapping()
        if self.last_status:
            self._update_table(self.last_status)
        messagebox.showinfo(t('info'), t('gn_dlg_saved'))

    def create_widgets(self):
        logger.debug("创建界面组件")
        # ----- 顶部工具栏 -----
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        self.interval_label = ttk.Label(toolbar, text=t('interval', n=REFRESH_INTERVAL))
        self.interval_label.pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(toolbar, text=t('status_wait'), foreground="orange")
        self.status_label.pack(side=tk.LEFT, padx=20)
        ttk.Button(toolbar, text=t('btn_settings'), command=lambda: open_settings(self.root, self.on_settings_saved)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text=t('btn_game_names'), command=lambda: edit_game_names(self.root, self.refresh_game_mapping)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text=t('btn_track'), command=self.open_track_manager).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text=t('btn_refresh'), command=self.async_refresh).pack(side=tk.RIGHT, padx=5)

        # ----- 左右可拖动分栏：左=好友状态，右=日志 -----
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # 左侧：好友状态表
        left = ttk.Frame(self.paned)
        self.paned.add(left, weight=1)
        columns = ("friend", "status", "game")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=12)
        self.tree.heading("friend", text=t('col_friend'))
        self.tree.heading("status", text=t('col_status'))
        self.tree.heading("game", text=t('col_game'))
        self.tree.column("friend", width=120, minwidth=70, stretch=False)
        self.tree.column("status", width=130, minwidth=70, stretch=False)
        self.tree.column("game", width=200, minwidth=70)
        tree_vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        tree_hsb = ttk.Scrollbar(left, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_vsb.grid(row=0, column=1, sticky="ns")
        tree_hsb.grid(row=1, column=0, sticky="ew")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # 右侧：日志
        self.log_frame = ttk.LabelFrame(self.paned, text=t('log_frame'), padding=5)
        self.paned.add(self.log_frame, weight=1)
        log_toolbar = ttk.Frame(self.log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 3))
        ttk.Button(log_toolbar, text=t('btn_clear_log'), command=self.clear_log).pack(side=tk.RIGHT)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 初始分割位置：左侧约占 42%，右侧日志更宽
        self.root.after(80, self._init_sash)

    def _init_sash(self):
        try:
            self.paned.sashpos(0, int(self.root.winfo_width() * 0.42))
        except Exception:
            pass

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        tags = self.tree.item(item, "tags")
        if not tags:
            return
        sid = tags[0]
        values = self.tree.item(item, "values")
        if not values or len(values) < 2:
            return
        friend_name = values[0]
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=t('menu_view_status'),
                         command=lambda: show_status_records(friend_name, sid))
        menu.add_command(label=t('menu_view_playtime'),
                         command=lambda: show_playtime_records(friend_name, sid))
        menu.post(event.x_root, event.y_root)

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def load_all_friends_for_setup(self):
        if not API_KEY or not STEAM_ID:
            self.status_label.config(text=t('status_no_api'), foreground="red")
            return
        self.status_label.config(text=t('status_loading'), foreground="orange")
        def fetch():
            friend_ids = get_steam_friends()
            if friend_ids:
                players = get_player_summaries(friend_ids)
                for p in players:
                    sid = p['steamid']
                    name = p.get('personaname', '未知')
                    self.all_friends_info[sid] = name
                self.all_friends_ids = friend_ids
                if not self.tracked_set:
                    self.tracked_set = set(friend_ids)
                    save_tracked(self.tracked_set)
                self.root.after(0, lambda: self.status_label.config(text=t('status_loaded', total=len(friend_ids), tracked=len(self.tracked_set)), foreground="green"))
                self.root.after(0, lambda: self.add_log(t('log_loaded', total=len(friend_ids), tracked=len(self.tracked_set))))
                self.async_refresh()
            else:
                self.root.after(0, lambda: self.status_label.config(text=t('status_load_fail'), foreground="red"))
        threading.Thread(target=fetch, daemon=True).start()

    def open_track_manager(self):
        if not self.all_friends_ids:
            messagebox.showinfo(t('info'), t('tr_not_ready'))
            return
        manager = tk.Toplevel(self.root)
        manager.title(t('tr_title'))
        manager.geometry("450x600")
        manager.resizable(True, True)

        main_frame = ttk.Frame(manager)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tool = ttk.Frame(main_frame)
        tool.pack(fill=tk.X, pady=2)
        ttk.Button(tool, text=t('tr_all'), command=lambda: self._toggle_all_checkboxes(var_dict, True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(tool, text=t('tr_none'), command=lambda: self._toggle_all_checkboxes(var_dict, False)).pack(side=tk.LEFT, padx=2)

        canvas = tk.Canvas(main_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        var_dict = {}
        sorted_friends = sorted(self.all_friends_info.items(), key=lambda x: x[1])
        for sid, name in sorted_friends:
            var = tk.BooleanVar(value=(sid in self.tracked_set))
            cb = ttk.Checkbutton(scrollable_frame, text=name, variable=var)
            cb.pack(anchor=tk.W, padx=5, pady=2)
            var_dict[sid] = var

        def save_selection():
            new_tracked = set([sid for sid, var in var_dict.items() if var.get()])
            if not new_tracked:
                if messagebox.askyesno(t('warn'), t('tr_empty_warn')):
                    self.tracked_set = new_tracked
                    save_tracked(self.tracked_set)
                    self.async_refresh()
                    manager.destroy()
            else:
                self.tracked_set = new_tracked
                save_tracked(self.tracked_set)
                self.async_refresh()
                manager.destroy()

        ttk.Button(main_frame, text=t('btn_apply'), command=save_selection).pack(pady=5)

    def _toggle_all_checkboxes(self, var_dict, select):
        for var in var_dict.values():
            var.set(select)

    def async_refresh(self):
        if not API_KEY or not STEAM_ID:
            self.status_label.config(text=t('status_no_api'), foreground="red")
            return
        if not self._refresh_running:
            self._refresh_running = True
            threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        with self.refresh_lock:
            self.root.after(0, lambda: self.status_label.config(text=t('status_fetching'), foreground="orange"))
            try:
                if not self.tracked_set:
                    self.root.after(0, lambda: self.status_label.config(text=t('status_no_tracked'), foreground="red"))
                    self._refresh_running = False
                    return

                tracked_ids = list(self.tracked_set)
                players = get_player_summaries(tracked_ids)
                current_data = {}
                for p in players:
                    sid = p['steamid']
                    name = p.get('personaname', '未知')
                    status_text, game = parse_status(p)
                    current_data[sid] = (name, status_text, game)

                old_status = self.last_status.copy()

                # ----- 状态变更记录（含首次游戏中） -----
                for sid, (name, new_status, new_game) in current_data.items():
                    if sid in old_status:
                        old_name, old_status_text, old_game = old_status[sid]
                        if new_status != old_status_text:
                            log_friend_change(sid, name, "状态变更", f"{old_status_text} → {new_status}", new_game if "游戏中" in new_status else "")
                            self.root.after(0, lambda n=name, o=old_status_text, ns=new_status: self.add_log(
                                t('log_status_change', name=n, old=translate_status(o), new=translate_status(ns))))
                    else:
                        # 首次出现，只记录游戏中
                        if "游戏中" in new_status:
                            game_name = new_game
                            log_friend_change(sid, name, "状态变更", f"开始游玩 {game_name}", game_name)
                            self.root.after(0, lambda n=name, gn=game_name: self.add_log(t('log_start_play', name=n, game=gn)))

                # 连续缺失检测（阈值2）
                threshold = 2
                for sid in old_status.keys():
                    if sid in current_data:
                        self.missing_count[sid] = 0
                    else:
                        self.missing_count[sid] = self.missing_count.get(sid, 0) + 1
                        if self.missing_count[sid] == threshold:
                            name = old_status[sid][0]
                            self.root.after(0, lambda n=name: self.add_log(t('log_missing', name=n, n=threshold)))

                self.last_status = current_data

                # ========== 时长监控 + 隐私检测 ==========
                try:
                    self.game_name_mapping = load_game_name_mapping()
                    current_playtime = get_friends_lifetime_playtime(tracked_ids, self.game_name_mapping)
                    history = self.last_playtime_history
                    is_first_run = (len(history) == 0)
                    changed = False
                    mapping = self.game_name_mapping

                    for sid, games in current_playtime.items():
                        if not games:
                            continue
                        friend_name = current_data.get(sid, ('未知',))[0]
                        friend_history = history.get(sid, {})
                        current_appids = set(str(appid) for appid in games.keys())
                        history_appids = set(friend_history.keys())

                        for appid, info in games.items():
                            appid_str = str(appid)
                            game_name = info['name']
                            new_minutes = info['playtime_minutes']
                            old_entry = friend_history.get(appid_str)
                            source = info.get('source', 'owned')
                            if old_entry is None:
                                if new_minutes > 0:
                                    new_hours = round(new_minutes / 60, 1)
                                    detail = f"首次记录总时长 {new_hours} 小时"
                                    log_friend_change(sid, friend_name, "时长变化", detail, game_name)
                                    self.root.after(0, lambda n=friend_name, gn=game_name, nh=new_hours:
                                                    self.add_log(t('log_first', name=n, game=gn, h=nh)))
                                    friend_history[appid_str] = {"minutes": new_minutes, "visible": True, "source": source}
                                    changed = True
                            else:
                                old_minutes = old_entry.get("minutes", 0)
                                old_visible = old_entry.get("visible", True)
                                if not old_visible:
                                    log_friend_change(sid, friend_name, "可见性变更", "游戏取消私密", game_name)
                                    self.root.after(0, lambda n=friend_name, gn=game_name:
                                                    self.add_log(t('log_unprivate', name=n, game=gn)))
                                diff = abs(new_minutes - old_minutes)
                                if diff > 0.5 and not is_first_run:
                                    new_hours = round(new_minutes / 60, 1)
                                    old_hours = round(old_minutes / 60, 1)
                                    detail = f"总时长 {old_hours} → {new_hours} 小时"
                                    log_friend_change(sid, friend_name, "时长变化", detail, game_name)
                                    self.root.after(0, lambda n=friend_name, gn=game_name, nh=new_hours:
                                                    self.add_log(t('log_playtime', name=n, game=gn, h=nh)))
                                friend_history[appid_str] = {"minutes": new_minutes, "visible": True, "source": source}
                                changed = True

                        for appid in history_appids - current_appids:
                            old_entry = friend_history.get(appid)
                            if old_entry is None:
                                continue
                            # 只有「拥有的游戏」消失才视为设为私密；
                            # 「最近游玩」来源的共享游戏/免费软件会随两周窗口自然消失，静默跳过
                            if old_entry.get('source', 'owned') != 'owned':
                                continue
                            old_visible = old_entry.get("visible", True)
                            if old_visible:
                                game_name = mapping.get(appid) or f"游戏ID:{appid}"
                                log_friend_change(sid, friend_name, "可见性变更", "游戏设为私密", game_name)
                                self.root.after(0, lambda n=friend_name, gn=game_name:
                                                self.add_log(t('log_private', name=n, game=gn)))
                                old_entry["visible"] = False
                                friend_history[appid] = old_entry
                                changed = True

                        if changed:
                            history[sid] = friend_history

                    if changed:
                        self.last_playtime_history = history
                        save_playtime_history(history)
                except Exception as e:
                    logger.error(f"时长检测错误: {e}")

                # 更新表格和状态标签
                self.root.after(0, lambda: self._update_table(current_data))
                self.root.after(0, lambda: self.status_label.config(
                    text=t('status_updated', time=datetime.now().strftime('%H:%M:%S'), n=len(tracked_ids)),
                    foreground="green"))
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(text=t('status_error', err=str(e)[:50]), foreground="red"))
                logger.error(f"刷新错误: {e}")
            finally:
                self._refresh_running = False

    def _update_table(self, current_data):
        logger.debug(f"更新表格，数据条数: {len(current_data)}")
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not current_data:
            logger.warning("当前数据为空，表格未更新")
            return
        for sid, (name, status_text, game) in current_data.items():
            try:
                self.tree.insert("", tk.END, values=(name, translate_status(status_text), game), tags=(sid,))
            except Exception as e:
                logger.error(f"插入行失败: {e}")
        logger.info(f"表格更新完成，共 {len(current_data)} 行")

    def refresh_loop(self):
        while self.running:
            time.sleep(REFRESH_INTERVAL)
            if self.running:
                self.root.after(0, self.async_refresh)

if __name__ == "__main__":
    root = tk.Tk()
    app = SteamMonitorApp(root)
    root.mainloop()