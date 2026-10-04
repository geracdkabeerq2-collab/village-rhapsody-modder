# -*- coding: utf-8 -*-
"""
乡村狂想曲 存档修改器 - 核心逻辑
读取/修改 data/villagedb_*.qt 存档文件（明文 JSON）
"""
import json
import os
import shutil
import glob
import sys
import time
import subprocess

# 自动定位游戏根目录（修改器位于游戏目录的"修改器"子目录下）
_MODDER_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(_MODDER_DIR)
DATA_DIR = os.path.join(GAME_DIR, 'data')
BACKUP_DIR = os.path.join(DATA_DIR, '_backup')

# 存档中的 key 名
KEY_GAME = 'gameData'
KEY_NAP = 'knapData_100001'        # 道具
KEY_NPC = 'npcData_100001'         # 好感度
KEY_ATTR = 'attributeData_100001'  # 体力

PHYSICAL_MAX = 100
MAX_STAR = 5

# 金钱相关道具 ID（来自游戏 PropType 枚举：COIN=1）
MONEY_ID = 1       # 金币（主货币，PropType.COIN=1）
MONEY_ITEM_ID = 9  # 私房钱（PropType.POCKET_MONEY=9）


def find_save_files():
    """查找所有存档文件"""
    files = glob.glob(os.path.join(DATA_DIR, 'villagedb_*.qt'))
    # 排除备份
    files = [f for f in files if '_backup' not in f and 'backup' not in os.path.basename(f).lower()]
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)  # 最新的在前
    return files


def is_game_running():
    """检测游戏进程（village.exe）是否在运行"""
    try:
        if os.name == 'nt':
            out = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq village.exe'],
                capture_output=True, text=True, timeout=5
            ).stdout
            return 'village.exe' in out
        else:
            out = subprocess.run(
                ['pgrep', '-f', 'village'],
                capture_output=True, text=True, timeout=5
            ).stdout
            return bool(out.strip())
    except Exception:
        return False


def get_save_info(path):
    """获取存档的简要信息（昵称、天数、金币、道具数），用于存档选择"""
    try:
        _, datas = load_save(path)
        pd = datas.get('playerData_100001', {})
        return {
            'file': os.path.basename(path),
            'nickname': pd.get('nickName', '?'),
            'day': pd.get('day', 0),
            'money': get_money(datas),
            'prop_count': len(get_props(datas)),
        }
    except Exception:
        return {
            'file': os.path.basename(path),
            'nickname': '?',
            'day': 0,
            'money': 0,
            'prop_count': 0,
        }


def load_save(path):
    """加载存档，返回 (data, datas_dict)

    data 是原始完整结构 {version, datas:[{key,val},...]}
    datas 是按 key 索引的 dict，方便读写。
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    datas = {item['key']: item['val'] for item in data.get('datas', [])}
    return data, datas


def save_save(path, data, datas=None):
    """写回存档（紧凑 JSON，UTF-8）

    关键修复：
    1. 若传入 datas（修改后的 dict），先回写进 data['datas'] 数组，
       否则对 datas 的修改会全部丢失（这是之前"修改失败"的根本原因）。
    2. 必须提高 version 字段。游戏读档时同时读 localStorage 和 .qt 文件，
       比较 version 选高的用；不提 version 会被 localStorage 旧数据覆盖。
    """
    # 【根因修复】把修改后的 datas dict 同步回 data['datas'] 数组
    if datas is not None:
        # 保留原有 key 顺序，更新已存在的 val
        data['datas'] = [
            {'key': k, 'val': datas[k]}
            for k in datas.keys()
        ]
    # 备份（时间戳命名，避免覆盖）
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, os.path.basename(path) + f'.{ts}.bak')
    shutil.copy2(path, backup_path)
    # 【关键修复】提高 version，确保游戏读档时优先采用本文件的修改
    data['version'] = data.get('version', 0) + 100000
    # 写回
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    return backup_path


# ============ 读取功能 ============

def get_props(datas, exclude_money=False):
    """获取道具列表 [{id, num}]；exclude_money=True 时排除金币(id=1)"""
    knap = datas.get(KEY_NAP, {})
    props = knap.get('props', [])
    if exclude_money:
        props = [p for p in props if p.get('id') != MONEY_ID]
    return props


def get_npcs(datas):
    """获取 NPC 好感度 [{npcId, starNum, talkIdx, ...}]"""
    npc = datas.get(KEY_NPC, {})
    return npc.get('npcDatas', [])


def get_cg_list(datas):
    """获取已解锁 CG 列表 [key, ...]"""
    gd = datas.get(KEY_GAME, {})
    return gd.get('unlockCgList', [])


def get_physical(datas):
    """获取体力值"""
    attr = datas.get(KEY_ATTR, {})
    for a in attr.get('attrbuteList', []):
        if a.get('id') == 1:  # PHYSICAL
            return a.get('num', 0)
    return 0


# ============ 修改功能 ============

def set_prop_num(datas, prop_id, num):
    """设置单个道具数量（不存在则新增）"""
    prop_id = int(prop_id)
    num = int(num)
    knap = datas.setdefault(KEY_NAP, {})
    props = knap.setdefault('props', [])
    for p in props:
        if p.get('id') == prop_id:
            p['num'] = num
            return True
    props.append({'id': prop_id, 'num': num, 'new': False})
    return True


def set_all_props_num(datas, num):
    """设置所有道具为指定数量（跳过金币 id=1，金币单独修改）"""
    num = int(num)
    knap = datas.setdefault(KEY_NAP, {})
    props = knap.setdefault('props', [])
    count = 0
    for p in props:
        if p.get('id') == MONEY_ID:
            continue  # 金币不在这里批量改，避免误动
        p['num'] = num
        count += 1
    return count


def get_money(datas):
    """获取金钱（金币 id=1 的数量，PropType.COIN=1）"""
    knap = datas.get(KEY_NAP, {})
    for p in knap.get('props', []):
        if p.get('id') == MONEY_ID:
            return p.get('num', 0)
    return 0


def set_money(datas, num):
    """设置金钱（金币 id=1），数量支持到亿级"""
    num = max(0, int(num))
    knap = datas.setdefault(KEY_NAP, {})
    props = knap.setdefault('props', [])
    for p in props:
        if p.get('id') == MONEY_ID:
            p['num'] = num
            return num
    props.append({'id': MONEY_ID, 'num': num, 'new': False})
    return num


def add_money(datas, delta):
    """增加金钱（可正可负），返回新值"""
    cur = get_money(datas)
    new = max(0, cur + int(delta))
    set_money(datas, new)
    return new


def set_npc_star(datas, npc_id, star):
    """设置 NPC 好感度星级（0-5）"""
    npc_id = int(npc_id)
    star = max(0, min(MAX_STAR, int(star)))
    npc = datas.setdefault(KEY_NPC, {})
    for n in npc.get('npcDatas', []):
        if n.get('npcId') == npc_id:
            n['starNum'] = star
            return True
    return False


def set_all_npc_star(datas, star):
    """设置所有 NPC 好感度星级"""
    star = max(0, min(MAX_STAR, int(star)))
    npc = datas.setdefault(KEY_NPC, {})
    count = 0
    for n in npc.get('npcDatas', []):
        n['starNum'] = star
        count += 1
    return count


def unlock_cg(datas, cg_key):
    """解锁单个 CG"""
    gd = datas.setdefault(KEY_GAME, {})
    cglist = gd.setdefault('unlockCgList', [])
    if cg_key not in cglist:
        cglist.append(cg_key)
        return True
    return False


def unlock_all_cg(datas, cg_keys):
    """解锁全部 CG"""
    gd = datas.setdefault(KEY_GAME, {})
    cglist = gd.setdefault('unlockCgList', [])
    added = 0
    for k in cg_keys:
        if k not in cglist:
            cglist.append(k)
            added += 1
    return added


def fill_physical(datas):
    """补满体力"""
    attr = datas.setdefault(KEY_ATTR, {})
    attrs = attr.setdefault('attrbuteList', [])
    found = False
    for a in attrs:
        if a.get('id') == 1:
            a['num'] = PHYSICAL_MAX
            found = True
    if not found:
        attrs.append({'id': 1, 'num': PHYSICAL_MAX})
    attr['physicalCache'] = 0
    return PHYSICAL_MAX


# ============ 命令行入口（供调试） ============
if __name__ == '__main__':
    files = find_save_files()
    if not files:
        print('未找到存档文件！')
        sys.exit(1)
    print('找到存档文件:')
    for f in files:
        print(' ', f, f'(修改时间: {os.path.getmtime(f)})')
