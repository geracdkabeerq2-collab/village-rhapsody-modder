# -*- coding: utf-8 -*-
"""
乡村狂想曲 存档修改器 - HTTP 后端服务
提供 REST API 供 HTML 前端读写存档
"""
import json
import os
import sys
import io
import http.server
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入核心逻辑
import modder_core as core

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modder_data.json')
MOD_DATA = json.load(open(DATA_FILE, encoding='utf-8'))

PORT = 8765


def json_response(handler, obj, status=200):
    body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(body)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 静默

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/status':
            files = core.find_save_files()
            json_response(self, {'ok': True, 'files': [os.path.basename(f) for f in files]})
            return

        if path == '/api/data':
            # 返回所有存档数据
            files = core.find_save_files()
            result = {'ok': True, 'saves': []}
            for f in files:
                try:
                    _, datas = core.load_save(f)
                    result['saves'].append({
                        'file': os.path.basename(f),
                        'nickname': datas.get('playerData_100001', {}).get('nickName', '?'),
                        'day': datas.get('playerData_100001', {}).get('day', 0),
                        'props': core.get_props(datas, exclude_money=True),
                        'npcs': core.get_npcs(datas),
                        'cg': core.get_cg_list(datas),
                        'physical': core.get_physical(datas),
                        'money': core.get_money(datas),
                    })
                except Exception as e:
                    result['saves'].append({'file': os.path.basename(f), 'error': str(e)})
            result['meta'] = MOD_DATA
            json_response(self, result)
            return

        if path == '/':
            # 返回 HTML 界面
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modder.html')
            with open(html_path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        json_response(self, {'ok': False, 'error': 'not found'}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw.decode('utf-8'))
        except:
            req = {}

        file_name = req.get('file', '')
        # 找到对应存档
        files = core.find_save_files()
        target = None
        for f in files:
            if os.path.basename(f) == file_name:
                target = f
                break
        if target is None and files:
            target = files[0]

        if target is None:
            json_response(self, {'ok': False, 'error': '未找到存档文件，请先启动一次游戏生成存档'}, 400)
            return

        try:
            data, datas = core.load_save(target)
            action = req.get('action', '')
            result = {'ok': True, 'action': action, 'file': os.path.basename(target)}

            if action == 'set_prop':
                pid = req.get('id')
                num = int(req.get('num', 0))
                core.set_prop_num(datas, pid, num)
                result['msg'] = f'道具 {pid} 数量已设为 {num}'

            elif action == 'set_all_props':
                num = int(req.get('num', 0))
                count = core.set_all_props_num(datas, num)
                result['msg'] = f'已设置 {count} 个道具数量为 {num}'

            elif action == 'set_npc_star':
                nid = req.get('id')
                star = int(req.get('star', 0))
                core.set_npc_star(datas, nid, star)
                result['msg'] = f'NPC {nid} 好感度已设为 {star} 星'

            elif action == 'set_all_npc_star':
                star = int(req.get('star', 0))
                count = core.set_all_npc_star(datas, star)
                result['msg'] = f'已设置 {count} 个 NPC 好感度为 {star} 星'

            elif action == 'unlock_all_cg':
                cg_keys = [c['key'] for c in MOD_DATA.get('cg', [])]
                added = core.unlock_all_cg(datas, cg_keys)
                result['msg'] = f'已解锁 {added} 个 CG（共 {len(cg_keys)} 个）'

            elif action == 'fill_physical':
                core.fill_physical(datas)
                result['msg'] = '体力已补满'

            elif action == 'set_money':
                num = int(req.get('num', 0))
                core.set_money(datas, num)
                result['msg'] = f'金钱已设为 {num}'

            elif action == 'add_money':
                delta = int(req.get('delta', 0))
                new = core.add_money(datas, delta)
                result['msg'] = f'金钱 {("+" if delta>=0 else "")}{delta}，当前 {new}'

            else:
                json_response(self, {'ok': False, 'error': '未知操作: ' + action}, 400)
                return

            # 写回（传入 datas，把修改同步回存档文件）
            backup = core.save_save(target, data, datas)
            result['backup'] = backup
            result['msg'] += f'（已备份到 {os.path.basename(backup)}）'
            json_response(self, result)
        except Exception as e:
            json_response(self, {'ok': False, 'error': str(e)}, 500)


def main():
    print(f'乡村狂想曲修改器后端已启动: http://127.0.0.1:{PORT}')
    print('按 Ctrl+C 退出')
    server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已退出')


if __name__ == '__main__':
    main()
