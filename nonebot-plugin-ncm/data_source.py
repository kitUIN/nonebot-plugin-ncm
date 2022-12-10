#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Union
import re

import qrcode
import time
from aiofile import async_open

import httpx
import nonebot
from nonebot.utils import run_sync

from pyncm import apis, Session, GetCurrentSession, DumpSessionAsString, LoadSessionFromString, SetCurrentSession
from pyncm.apis.cloudsearch import SONG, USER, PLAYLIST

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import (MessageSegment, Message,
                                         ActionFailed, NetworkError, Bot,
                                         GroupMessageEvent, PrivateMessageEvent)

from .config import ncm_config
from tinydb import TinyDB, Query

# ============数据库导入=============
dbPath = Path("db")
musicPath = Path("music")

if not musicPath.is_dir():
    musicPath.mkdir()
    logger.success("ncm音乐库创建成功")
if not dbPath.is_dir():
    dbPath.mkdir()
    logger.success("ncm数据库目录创建成功")
music = TinyDB("./db/ncm_musics.json")
setting = TinyDB("./db/ncm_setting.json")
ncm_user_cache = TinyDB("./db/ncm_cache.json")
ncm_check_cache = TinyDB("./db/ncm_check_cache.json")
Q = Query()
cmd = list(nonebot.get_driver().config.command_start)[0]


class NcmLoginFailedException(Exception): pass


# ============主类=============
class Ncm:
    def __init__(self):
        self.api = apis
        self.bot = None
        self.event = None

    def get_session(self, bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent]):
        self.bot = bot
        self.event = event

    @staticmethod
    def save_user(session: str):
        info = ncm_user_cache.search(Q["uid"] == "user")
        if info:
            info[0]['session'] = session
            ncm_user_cache.update(info[0], Q["uid"] == "user")
        else:
            ncm_user_cache.insert({"uid": "user", "session": session})

    @staticmethod
    def load_user(info):
        SetCurrentSession(LoadSessionFromString(info[0]['session']))

    def login(self):
        try:
            self.api.login.LoginViaCellphone(phone=ncm_config.ncm_phone, password=ncm_config.ncm_password)
            self.get_user_info()

        except Exception as e:
            if str(e) == str({'code': 400, 'message': '登陆失败,请进行安全验证'}):
                logger.error("缺少安全验证，请将账号留空进行二维码登录")
                logger.info("自动切换为二维码登录↓")
                self.get_qrcode()
            else:
                raise e

    def get_user_info(self):
        logger.success(f"欢迎您网易云用户:{GetCurrentSession().nickname} [{GetCurrentSession().uid}]")
        self.save_user(DumpSessionAsString(GetCurrentSession()))

    def get_phone_login(self):
        phone = ncm_config.ncm_phone
        ctcode = int(ncm_config.ncm_ctcode)
        result = self.api.login.SetSendRegisterVerifcationCodeViaCellphone(cell=phone, ctcode=ctcode)
        if not result.get('code', 0) == 200:
            logger.error(result)
        else:
            logger.success('已发送验证码,输入验证码:')
        while True:
            captcha = int(input())
            verified = self.api.login.GetRegisterVerifcationStatusViaCellphone(phone, captcha, ctcode)
            if verified.get('code', 0) == 200:
                break
        result = self.api.login.LoginViaCellphone(phone, captcha=captcha, ctcode=ctcode)
        self.get_user_info()

    def get_qrcode(self):
        # info = ncm_cache.search(Q["uid"] == "user")
        # if info:
        #     try:
        #         logger.info("检测到用户缓存")
        #         GetCurrentSession().cookies.set_cookie(dict_from_cookiejar(info[0]['cookie']))
        #         self.api.login.WriteLoginInfo(info[0]['st'])
        #         return logger.success("自动登录成功")
        #     except:
        #         logger.error("自动登录失败，进入手动二维码登录模式")
        uuid = self.api.login.LoginQrcodeUnikey()["unikey"]
        url = f"https://music.163.com/login?codekey={uuid}"
        img = qrcode.make(url)
        img.save('ncm.png')
        logger.info("二维码已经保存在当前目录下的ncm.png，请使用手机网易云客户端扫码登录。")
        while True:
            rsp = self.api.login.LoginQrcodeCheck(uuid)  # 检测扫描状态
            if rsp["code"] == 803 or rsp["code"] == 800:
                st = self.api.login.GetCurrentLoginStatus()
                logger.debug(st)
                self.api.login.WriteLoginInfo(st)
                self.get_user_info()
                return True
            time.sleep(1)

    def detail(self, ids: list) -> list:
        songs: list = self.api.track.GetTrackDetail(song_ids=ids)["songs"]
        detail = [(data["name"] + "-" + ",".join([names["name"] for names in data["ar"]])) for data in songs]
        return detail

    async def music_check(self, nid):
        nid = int(nid)
        info = music.search(Q["id"] == nid)
        if info:
            path = Path(info[0]["file"])
            if path.is_file():
                return info[0]
            else:
                return await self.download(ids=[nid], check=True)
        else:
            return None

    async def search_song(self, keyword: str, limit: int = 1) -> int:  # 搜索歌曲
        res = self.api.cloudsearch.GetSearchResult(keyword=keyword, stype=SONG, limit=limit)
        logger.debug(f"搜索歌曲{keyword},返回结果:{res}")
        if "result" in res.keys():
            data = res["result"]["songs"]
        else:
            data = res["songs"]
        if data:
            return data[0]["id"]

    async def search_user(self, keyword: str, limit: int = 1):  # 搜索用户
        self.api.cloudsearch.GetSearchResult(keyword=keyword, stype=USER, limit=limit)

    async def search_playlist(self, keyword: str, limit: int = 1):  # 搜索歌单
        self.api.cloudsearch.GetSearchResult(keyword=keyword, stype=PLAYLIST, limit=limit)

    def check_message(self):
        """检查缓存中是否存在解析
        :return:
        """
        info = ncm_check_cache.search(Q.message_id == self.event.dict()["reply"]["message_id"])
        return info[0] if info else None

    def get_song(self, nid: Union[int, str], message_id=None):
        """解析歌曲id,并且加入缓存

        :param message_id:
        :param nid:
        :return:
        """
        if message_id:
            mid = message_id
        else:
            mid = self.event.message_id
        ncm_check_cache.insert({"message_id": mid,
                                "type": "song",
                                "nid": nid,
                                "lid": 0,
                                "ids": [],
                                "lmsg": "",
                                "time": int(time.time())})

    def get_playlist(self, lid: Union[int, str]):
        data = self.api.playlist.GetPlaylistInfo(lid)
        # logger.info(data)
        if data["code"] == 200:
            raw = data["playlist"]
            tags = ",".join(raw['tags'])
            songs = [i['id'] for i in raw['trackIds']]
            ncm_check_cache.insert({"message_id": self.event.message_id,
                                    "type": "playlist",
                                    "nid": 0,
                                    "lid": lid,
                                    "ids": songs,
                                    "lmsg": f"歌单:{raw['name']}\r\n创建者:{raw['creator']['nickname']}\r\n歌曲总数:{raw['trackCount']}\r\n"
                                            f"标签:{tags}\r\n播放次数:{raw['playCount']}\r\n收藏:{raw['subscribedCount']}\r\n"
                                            f"评论:{raw['commentCount']}\r\n分享:{raw['shareCount']}\r\nListID:{lid}",
                                    "time": int(time.time())})

    async def upload_group_data_file(self, data):
        await self.upload_group_file(file=data["file"], name=data["filename"])

    async def upload_private_data_file(self, data):
        await self.upload_private_file(file=data["file"], name=data["filename"])

    async def upload_group_file(self, file, name):
        try:
            await self.bot.upload_group_file(group_id=self.event.group_id,
                                             file=file, name=name)
        except (ActionFailed, NetworkError) as e:
            logger.error(e)
            if isinstance(e, ActionFailed) and e.info["wording"] == "server" \
                                                                    " requires unsupported ftn upload":
                await self.bot.send(event=self.event, message=Message(MessageSegment.text(
                    "[ERROR]  文件上传失败\r\n[原因]  机器人缺少上传文件的权限\r\n[解决办法]  "
                    "请将机器人设置为管理员或者允许群员上传文件")))
            elif isinstance(e, NetworkError):
                await self.bot.send(event=self.event, message=Message(MessageSegment.text(
                    "[ERROR]  文件上传失败\r\n[原因]  上传超时(一般来说还在传,建议等待五分钟)")))

    async def upload_private_file(self, file, name):
        try:
            await self.bot.upload_private_file(user_id=self.event.user_id,
                                               file=file, name=name)
        except (ActionFailed, NetworkError) as e:
            logger.error(e)
            if isinstance(e, NetworkError):
                await self.bot.send(event=self.event, message=Message(MessageSegment.text(
                    "[ERROR]  文件上传失败\r\n[原因]  上传超时(一般来说还在传,建议等待五分钟)")))

    @run_sync
    def get_zip(self, lid, filenames: list):
        zip_file_new = f'{lid}.zip'
        with zipfile.ZipFile(str(Path.cwd().joinpath("music").joinpath(zip_file_new)), 'w', zipfile.ZIP_DEFLATED) as z:
            for f in filenames:
                z.write(str(f), f.name)
        return zip_file_new

    async def download(self, ids: list, check=False, lid=0, is_zip=False):  # 下载音乐
        data: list = self.api.track.GetTrackAudio(song_ids=ids, bitrate=3200 * 1000)["data"]
        name: list = self.detail(ids)
        filenames = []
        for i in range(len(ids)):
            if data[i]["code"] == 404:
                logger.error("未从网易云读取到下载地址")
                return
            url = data[i]["url"]
            nid = data[i]["id"]
            filename = f"{name[i]}.{data[i]['type']}"
            filename = re.sub('[\/:*?"<>|]', '-', filename)
            file = Path.cwd().joinpath("music").joinpath(filename)
            config = {
                "id": int(nid),
                "file": str(file),  # 获取文件位置
                "filename": filename,  # 获取文件名
                "from": "song" if len(ids) == 1 else "list",  # 判断来自单曲还是歌单
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取时间
            }
            filenames.append(file)
            info = music.search(Q["id"] == nid)
            if info:  # 数据库储存
                music.update(config, Q["id"] == nid)
            else:
                music.insert(config)
            async with httpx.AsyncClient() as client:  # 下载歌曲
                async with client.stream("GET", url=url) as r:
                    async with async_open(file, 'wb') as out_file:
                        async for chunk in r.aiter_bytes():
                            await out_file.write(chunk)
        if is_zip:
            await self.get_zip(lid=lid, filenames=filenames)
        return config


nncm = Ncm()
info = ncm_user_cache.search(Q.uid == "user")
if info:
    logger.info("检测到缓存，自动加载用户")
    nncm.load_user(info)
    nncm.get_user_info()
elif ncm_config.ncm_phone == "":
    logger.warning("您未填写账号,自动进入二维码登录模式")
    nncm.get_qrcode()
elif ncm_config.ncm_password == "":
    logger.warning("您未填写密码,自动进入手机验证码登录模式")
    nncm.get_phone_login()
else:
    nncm.login()
