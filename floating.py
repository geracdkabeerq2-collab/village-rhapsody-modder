# -*- coding: utf-8 -*-
"""
乡村狂想曲 · 游戏内悬浮窗修改器
基于 pywebview + WebView2，创建置顶无边框悬浮窗，边玩边改
"""
import os
import sys
import io
import json
import threading
import webview

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入存档核心逻辑
import modder_core as core

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'modder_data.json')
HTML_FILE = os.path.join(BASE_DIR, 'floating.html')

MOD_DATA = json.load(open(DATA_FILE, encoding='utf-8'))


class Api:
    """暴露给 JS 的 API"""

    def _pick_file(self, name=None):
        """根据文件名选择存档，找不到则返回最新修改的"""
        files = core.find_save_files()
        if not files:
            return None
        if name:
            for f in files:
                if os.path.basename(f) == name:
                    return f
        return files[0]

    def get_data(self):
        files = core.find_save_files()
        # 所有存档的详情列表
        saves = [core.get_save_info(f) for f in files]
        result = {'meta': MOD_DATA, 'saves': saves, 'cur': None, 'game_running': core.is_game_running()}
        if files:
            try:
                target = files[0]
                _, datas = core.load_save(target)
                result['cur'] = {
                    'file': os.path.basename(target),
                    'props': core.get_props(datas, exclude_money=True),
                    'npcs': core.get_npcs(datas),
                    'cg': core.get_cg_list(datas),
                    'physical': core.get_physical(datas),
                    'money': core.get_money(datas),
                }
            except Exception as e:
                result['error'] = str(e)
        return result

    def get_save(self, name):
        """切换查看指定存档"""
        target = self._pick_file(name)
        if not target:
            return {'ok': False, 'error': '未找到存档'}
        try:
            _, datas = core.load_save(target)
            return {
                'ok': True,
                'cur': {
                    'file': os.path.basename(target),
                    'props': core.get_props(datas, exclude_money=True),
                    'npcs': core.get_npcs(datas),
                    'cg': core.get_cg_list(datas),
                    'physical': core.get_physical(datas),
                    'money': core.get_money(datas),
                }
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def do_action(self, action, body=None):
        body = body or {}
        # 游戏运行时阻止修改（会被游戏内存数据覆盖）
        if core.is_game_running():
            return {'ok': False, 'error': '⚠️ 游戏正在运行！请先完全退出游戏，再点修改（游戏开着会被覆盖）'}
        target = self._pick_file(body.get('file'))
        if not target:
            return {'ok': False, 'error': '未找到存档，请先启动游戏'}
        try:
            data, datas = core.load_save(target)
            result = {'ok': True, 'action': action, 'file': os.path.basename(target)}

            if action == 'set_prop':
                core.set_prop_num(datas, body.get('id'), int(body.get('num', 0)))
                result['msg'] = f'道具已设为 {body.get("num")}'
            elif action == 'set_all_props':
                num = int(body.get('num', 999))
                core.set_all_props_num(datas, num)
                result['msg'] = f'全部道具已设为 {num}'
            elif action == 'set_npc_star':
                core.set_npc_star(datas, body.get('id'), int(body.get('star', 0)))
                result['msg'] = f'好感度已设为 {body.get("star")} 星'
            elif action == 'set_all_npc_star':
                star = int(body.get('star', 5))
                core.set_all_npc_star(datas, star)
                result['msg'] = f'全部 NPC 已设为 {star} 星'
            elif action == 'unlock_all_cg':
                cg_keys = [c['key'] for c in MOD_DATA.get('cg', [])]
                core.unlock_all_cg(datas, cg_keys)
                result['msg'] = f'已解锁全部 CG'
            elif action == 'fill_physical':
                core.fill_physical(datas)
                result['msg'] = '体力已补满'
            elif action == 'set_money':
                num = int(body.get('num', 0))
                core.set_money(datas, num)
                result['msg'] = f'金钱已设为 {num}'
            elif action == 'add_money':
                delta = int(body.get('delta', 0))
                new = core.add_money(datas, delta)
                result['msg'] = f'金钱 {("+" if delta>=0 else "")}{delta}，当前 {new}'
            else:
                return {'ok': False, 'error': '未知操作: ' + action}

            core.save_save(target, data, datas)
            return result
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def minimize(self):
        try:
            window.minimize()
        except Exception:
            pass
        return {'ok': True}

    def close(self):
        try:
            window.destroy()
        except Exception:
            os._exit(0)
        return {'ok': True}


def main():
    api = Api()
    global window
    window = webview.create_window(
        '狂想曲修改器',
        HTML_FILE,
        js_api=api,
        width=320,
        height=460,
        x=None,
        y=None,
        frameless=True,       # 无边框
        on_top=True,          # 置顶
        easy_drag=True,       # 可拖拽
        background_color='#1c1814',
        min_size=(260, 300),
    )
    webview.start(debug=False)


if __name__ == '__main__':
    main()
