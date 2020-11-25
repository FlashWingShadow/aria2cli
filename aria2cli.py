#!/usr/bin/env python

import requests
import fire
import re

# --- config ---
token = 'your_token'
host = '127.0.0.1'
port = 6800
# --------------

def size_str(size):
    if size >= 1_000_000_000:
        return '{:.2f} GB'.format(size/1_000_000_000)
    if size >= 1_000_000:
        return '{:.2f} MB'.format(size/1_000_000)
    if size >= 1_000:
        return '{:.2f} KB'.format(size/1_000)
    return '{}  B'.format(size)

def progressbar(progress, bar_length):
    completed_length = int(bar_length*progress)
    return '[{}{}]'.format('#' * completed_length, '-' * (bar_length - completed_length))

def get_wide_char_num(string):
    l = re.findall('[\u4e00-\u9fa5,\u0800-\u4e00,\uac00-\ud7ff]', string)
    return len(l)

def is_wide_char(c):
    return '\u0800'<c<'\u9fa5' or '\uac00'<c<'\ud7ff'

def cut_v_str(string, length):
    wide_char_num = get_wide_char_num(string)
    v_len = len(string) + wide_char_num
    if v_len > length:
        l = 0
        for i, c in enumerate(string):
            l += 2 if is_wide_char(c) else 1
            if l > length:
                string = string[:i]
                if is_wide_char(c) and l - length == 1:
                    string += ' '
                    v_len += 1
                break;
    return string, v_len

def v_str(string, length, align='<'):
    assert align in ['<', '>', '^']
    string, v_len = cut_v_str(string, length)
    extra = length - v_len if length >= v_len else 0
    if align == '<':
        return string + ' ' * extra
    elif align == '>':
        return ' ' * extra + string
    elif align == '^':
        return (extra // 2) * ' ' + string + (extra - extra // 2) * ' '

class Aria2Rpc():
    def __init__(self, host, port, token):
        self.host = host
        self.port = port
        self.token = token
        self.itemList = ['gid', 'bittorrent', 'totalLength', 'completedLength',  'downloadSpeed', 'files', 'infoHash', 'status']
        #  options = ['gid','totalLength','completedLength','uploadSpeed','downloadSpeed','connections','numSeeders','seeder','status','errorCode','verifiedLength','verifyIntegrityPending','files','bittorrent','infoHash']

    def aria2_request(self, jsonrpc):
        headers = {
                'Content-Type': 'application/json',
            }
        url = f'http://{self.host}:{self.port}/jsonrpc'
        r = requests.post(url, headers=headers, json=jsonrpc)
        r.raise_for_status()
        return r.json()

    def get_jsonrpc(self, method, argList=[]):
        return {
                'jsonrpc': '2.0',
                'id': 'aria2cli',
                'method': f'aria2.{method}',
                'params': [f'token:{self.token}'] + argList
            }

    def getGlobalStat(self):
        jsonrpc = self.get_jsonrpc('getGlobalStat')
        return self.aria2_request(jsonrpc)['result']

    def addUri(self, url):
        argList = [[url], {}]
        jsonrpc = self.get_jsonrpc('addUri', argList)
        return self.aria2_request(jsonrpc)['result']

    def addTorrent(self, torrent: bytes):
        import base64
        argList = [base64.b64encode(torrent), [], {}]
        jsonrpc = self.get_jsonrpc('addTorrent', argList)
        return self.aria2_request(jsonrpc)['result']

    def tellActive(self):
        argList = [self.itemList]
        jsonrpc = self.get_jsonrpc('tellActive', argList)
        return self.aria2_request(jsonrpc)['result']

    def tellWaiting(self):
        argList = [0, 1000, self.itemList]
        jsonrpc = self.get_jsonrpc('tellWaiting', argList)
        return self.aria2_request(jsonrpc)['result']

    def tellStopped(self):
        argList = [-1, 1000, self.itemList]
        jsonrpc = self.get_jsonrpc('tellStopped', argList)
        return self.aria2_request(jsonrpc)['result']

    def purgeDownloadResult(self):
        jsonrpc = self.get_jsonrpc('purgeDownloadResult')
        return self.aria2_request(jsonrpc)['result']

    def removeDownloadResult(self, gid):
        jsonrpc = self.get_jsonrpc('removeDownloadResult', [gid])
        return self.aria2_request(jsonrpc)['result']

    def forcePause(self, gid):
        jsonrpc = self.get_jsonrpc('forcePause', [gid])
        return self.aria2_request(jsonrpc)['result']

    def unpause(self, gid):
        jsonrpc = self.get_jsonrpc('unpause', [gid])
        return self.aria2_request(jsonrpc)['result']

    def forceRemove(self, gid):
        jsonrpc = self.get_jsonrpc('forceRemove', [gid])
        return self.aria2_request(jsonrpc)['result']

    def tellStatus(self, gid):
        jsonrpc = self.get_jsonrpc('tellStatus', [gid])
        return self.aria2_request(jsonrpc)['result']

aria2rpc = Aria2Rpc(host, port, token)

def convert_item(item):
    bittorrent = item.get('bittorrent')
    if bittorrent:
        title = bittorrent['info']['name'] if bittorrent.get('info') else item['infoHash']
    else:
        title = item['files'][0]['path'].split('/')[-1]
    totalLength = int(item['totalLength'])
    completedLength = int(item['completedLength'])
    return {
            'gid': item['gid'],
            'title': title,
            'fileNum': len(item['files']),
            'speed': size_str(int(item['downloadSpeed'])) + '/s',
            'size': size_str(totalLength),
            'progress': completedLength / totalLength if totalLength else 0 ,
            'status': item['status']
        }

status_symbol = {
    'active': '>',
    'complete': 'O',
    'paused': '|',
    'error': 'X'
}

def item_default_format(item):
    item = convert_item(item)
    procentage = '{:.2f} %'.format(item['progress'] * 100)
    bar = progressbar(item['progress'], 10)
    title = v_str(item['title'], 40)
    status = status_symbol[item['status']]
    return f"{title}  {item['size']:>10}  {item['fileNum']}  [{status}] {item['speed']:>11} {bar} {procentage:>8}"

def item_detail_format(item):
    item = convert_item(item)
    procentage = '{:.2f} %'.format(item['progress'] * 100)
    bar = progressbar(item['progress'], 10)
    title = v_str(item['title'], 40)
    return f"{item['gid']}  {title}  {item['size']:>10}  {item['fileNum']}files  {item['speed']:>11} {bar} {procentage:>8} {item['status']}"

item_default_format_header = 'Name                                            Size  F  Status   Speeds              Progress'

def item_info_format(item):
    bittorrent = item['bittorrent']
    name = bittorrent['info']['name'] if bittorrent.get('info') else None
    infoHash = item['infoHash']
    totalLength = size_str(int(item['totalLength']))
    dir_path = item['dir']
    def file_format(file):
        size = size_str(int(file['length']))
        procentage = '{:.2f} %'.format(int(file['completedLength'])*100/int(file['length']))
        name = v_str(file['path'].replace(dir_path, ''), 60)
        return f'{name}  {size:>9}  {procentage:>8}'
    files_str = '\n'.join(map(lambda file: f'    {file_format(file)}', item['files']))
    return (f'Name    : {name}\n'
            f'InfoHash: {infoHash}\n'
            f'Size    : {totalLength}\n' 
            f'Files   :\n'
            f'{files_str}\n')

class ListCommand():
    'list task'

    def __init__(self, format='default'):
        if format == 'detail':
            self.item_format = item_detail_format
        else:
            self.item_format = item_default_format

    def all(self, format='default'):
        'list all task'
        print(item_default_format_header)
        self.active()
        self.waiting()
        self.stopped()

    def active(self):
        'list active task'
        items_show = '\n'.join([self.item_format(i) for i in aria2rpc.tellActive()])
        if items_show:
            print(items_show)

    def waiting(self):
        'list waiting task'
        items_show = '\n'.join([self.item_format(i) for i in aria2rpc.tellWaiting()])
        if items_show:
            print(items_show)

    def stopped(self):
        'list stopped task'
        items_show = '\n'.join([self.item_format(i) for i in aria2rpc.tellStopped()])
        if items_show:
            print(items_show)

    def __call__(self):
        self.all()

class Command():
    'aria2 rpc cli'
    def __init__(self, format='default'):
        self.list = ListCommand(format)

    def new(self, *urls):
        'new task for urls'
        for url in urls:
            aria2rpc.addUri(url)
            print(f'INFO: new task for {url}')

    def bt(self, *torrent_paths):
        'new task for torrent files'
        import os
        for torrent_path in torrent_paths:
            torrent_realpath = os.path.realpath(torrent_path)
            if not os.path.isfile(torrent_realpath):
                print(f'ERROR: {torrent_path} is not exist')
                continue
            with open(torrent_realpath, 'rb') as f:
                torrent = f.read()
            aria2rpc.addTorrent(torrent)
            print(f'INFO: new task for {torrent_path}')

    def purge(self):
        'purge download result'
        if aria2rpc.purgeDownloadResult() == 'OK':
            print('INFO: purge completed')
        else:
            print('ERROR: in purge')

    def status(self):
        'show global status'
        stat = aria2rpc.getGlobalStat()
        speed = size_str(int(stat['downloadSpeed'])) + '/s'
        msg = 'Active: {}    Stopped: {}    Speed: {}'.format(stat['numActive'], stat['numStopped'], speed)
        print(msg)

    def pause(self, gid):
        'pause a task'
        r = aria2rpc.forcePause(gid)
        print(f'INFO: pause task gid: {gid}')

    def unpause(self, gid):
        'unpause a task'
        r = aria2rpc.unpause(gid)
        print(f'INFO: unpause task gid: {gid}')

    def remove(self, gid):
        'remove a task'
        r = aria2rpc.forceRemove(gid)
        print(f'INFO: remove task gid: {gid}')

    def show(self, gid):
        item = aria2rpc.tellStatus(gid)
        print(item_info_format(item))

    def __call__(self):
        self.list.all()
        self.status()

if __name__ == '__main__':
    fire.Fire(Command)
