#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Union, List, Dict, cast

import nonebot
import qrcode
from nonebot.adapters.onebot.v11 import (MessageSegment, Message,
                                         ActionFailed, NetworkError, Bot,
                                         GroupMessageEvent, PrivateMessageEvent)
from nonebot.log import logger
from nonebot.matcher import current_bot
from pyncm import apis, GetCurrentSession, DumpSessionAsString, LoadSessionFromString, SetCurrentSession
from pyncm.apis.cloudsearch import SONG, USER, PLAYLIST
from tinydb import TinyDB, Query

from .config import ncm_config

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

    @staticmethod
    def save_user(session: str):
        info = ncm_user_cache.search(Q["uid"] == "user")
        if info:
            info[0]['session'] = session
            ncm_user_cache.update(info[0], Q["uid"] == "user")
        else:
            ncm_user_cache.insert({"uid": "user", "session": session})

    @staticmethod
    def load_user(session: str):
        SetCurrentSession(LoadSessionFromString(session))

    def login(self) -> bool:
        try:
            self.api.login.LoginViaCellphone(phone=str(ncm_config.ncm_phone), password=ncm_config.ncm_password)
            self.get_user_info()
            return True
        except Exception as e:
            if str(e) == str({'code': 400, 'message': '登陆失败,请进行安全验证'}):
                logger.error("缺少安全验证，请将账号留空进行二维码登录")
                logger.info("自动切换为二维码登录↓")
                self.get_qrcode()
            else:
                raise e
            return False

    def get_user_info(self) -> str:
        message: str = f"欢迎您网易云用户:{GetCurrentSession().nickname} [{GetCurrentSession().uid}]"
        logger.success(message)
        self.save_user(DumpSessionAsString(GetCurrentSession()))
        return message

    def get_phone_login(self):
        phone: str = str(ncm_config.ncm_phone)
        ctcode: int = ncm_config.ncm_ctcode
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
                self.api.login.WriteLoginInfo(self.api.login.GetCurrentLoginStatus(), GetCurrentSession())
                self.get_user_info()
                return True
            time.sleep(1)

    def detail_names(self, ids: List[int]) -> List[str]:
        songs: list = self.api.track.GetTrackDetail(song_ids=ids)["songs"]
        detail = [(data["name"] + "-" + ",".join([names["name"] for names in data["ar"]])) for data in songs]
        return detail

    @logger.catch()
    def get_detail(self, ids: List[int]):
        data: list = self.api.track.GetTrackAudio(song_ids=ids, bitrate=ncm_config.ncm_bitrate * 1000)["data"]
        names: list = self.detail_names(ids)
        for i in range(len(ids)):
            data[i]['ncm_name'] = names[i]
        return data

    async def music_check(self, nid: Union[int, List[int]], event: Union[GroupMessageEvent, PrivateMessageEvent],
                          lid: int = None):
        """判断数据库中是否有缓存，有则使用缓存，没有则新下载"""
        tasks = []
        if lid:
            del_nid = []
            for i in nid:
                info = music.search(Q["id"] == i)
                if info:
                    try:
                        tasks.append(asyncio.create_task(self.upload_data_file(event=event, data=info[0])))
                        del_nid.append(i)
                    except Exception:
                        continue
            for j in del_nid:
                nid.remove(j)
        else:
            nid = int(nid)
            info = music.search(Q["id"] == nid)
            if info:
                try:
                    tasks.append(asyncio.create_task(self.upload_data_file(event=event, data=info[0])))
                    return
                except Exception as e:
                    if isinstance(e, ActionFailed) and e.info.get("retcode") != 10003:
                        logger.error(e)
                        return
        if tasks:
            await asyncio.gather(*tasks)
        if nid:
            if isinstance(nid, int):
                nid = [nid]
            await self.start_upload(ids=nid, event=event)

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

    @staticmethod
    def check_message(message_id: int):
        """检查缓存中是否存在解析
        :return:
        """
        flag = ncm_check_cache.search(Q.message_id == message_id)
        return flag[0] if flag else None

    @staticmethod
    def get_song(nid: int, message_id: int):
        """解析歌曲id,并且加入缓存
        :param message_id:
        :param nid:
        :return:
        """
        ncm_check_cache.insert({"message_id": message_id,
                                "type": "song",
                                "nid": int(nid),
                                "lid": 0,
                                "ids": [],
                                "lmsg": "",
                                "bot_id": "",
                                "time": int(time.time())})

    def get_playlist(self, lid: int, message_id: int):
        lid = int(lid)
        data = self.api.playlist.GetPlaylistInfo(lid)
        # logger.info(data)
        if data["code"] == 200:
            raw = data["playlist"]
            tags = ",".join(raw['tags'])
            songs = [int(i['id']) for i in raw['trackIds']]
            ncm_check_cache.insert({"message_id": message_id,
                                    "type": "playlist",
                                    "nid": 0,
                                    "lid": lid,
                                    "ids": songs,
                                    "lmsg": f"歌单:{raw['name']}\r\n创建者:{raw['creator']['nickname']}\r\n歌曲总数:{raw['trackCount']}\r\n"
                                            f"标签:{tags}\r\n播放次数:{raw['playCount']}\r\n收藏:{raw['subscribedCount']}\r\n"
                                            f"评论:{raw['commentCount']}\r\n分享:{raw['shareCount']}\r\nListID:{lid}",
                                    "bot_id": "",
                                    "time": int(time.time())})

    async def upload_data_file(self, event: Union[GroupMessageEvent, PrivateMessageEvent],
                               data: Dict[str, Union[str, int]]):
        if isinstance(event, GroupMessageEvent):
            await self.upload_group_file(group_id=event.group_id, file=data["file"], name=data["filename"])
        elif isinstance(event, PrivateMessageEvent):
            await self.upload_private_file(user_id=event.user_id, file=data["file"], name=data["filename"])

    @staticmethod
    async def upload_group_file(group_id: int, file: str, name: str):
        bot: Bot = cast(Bot, current_bot.get())
        try:
            await bot.upload_group_file(group_id=group_id, file=file, name=name)
        except (ActionFailed, NetworkError) as e:
            logger.error(e)
            if isinstance(e, ActionFailed) and e.info["wording"] == "server" \
                                                                    " requires unsupported ftn upload":
                await bot.send_group_msg(group_id=group_id, message=Message(MessageSegment.text(
                    "[ERROR]  文件上传失败\r\n[原因]  机器人缺少上传文件的权限\r\n[解决办法]  "
                    "请将机器人设置为管理员或者允许群员上传文件")))
            elif isinstance(e, NetworkError):
                await bot.send_group_msg(group_id=group_id,
                                         message=Message(MessageSegment.text("[ERROR]文件上传失败\r\n[原因]  "
                                                                             "上传超时(一般来说还在传,建议等待五分钟)")))

    @staticmethod
    async def upload_private_file(user_id: int, file: str, name: str):
        bot: Bot = cast(Bot, current_bot.get())
        try:
            await bot.upload_private_file(user_id=user_id, file=file, name=name)
        except (ActionFailed, NetworkError) as e:
            logger.error(e)
            if isinstance(e, NetworkError):
                await bot.send_private_msg(user_id=user_id, message=Message(MessageSegment.text(
                    "[ERROR]  文件上传失败\r\n[原因]  上传超时(一般来说还在传,建议等待五分钟)")))

    # @run_sync
    # def get_zip(self, lid: int, filenames: list):
    #     zip_file_new = f'{lid}.zip'
    #     with zipfile.ZipFile(str(Path.cwd().joinpath("music").joinpath(zip_file_new)), 'w', zipfile.ZIP_DEFLATED) as z:
    #         for f in filenames:
    #             z.write(str(f), f.name)
    #     return zip_file_new
    async def upload(self, data: dict, fr: str, event: Union[GroupMessageEvent, PrivateMessageEvent]):
        if data["code"] == 404:
            logger.error("未从网易云读取到下载地址")
            return None
        url = data["url"]
        nid = data["id"]
        filename = f"{data['ncm_name']}.{data['type']}"
        filename = re.sub('[\/:*?"<>|]', '-', filename)
        bot = cast(Bot, current_bot.get())
        download_ret: Dict[str, str] = await bot.download_file(url=url)
        file = download_ret["file"]
        cf = {
            "id": int(nid),
            "file": str(file),  # 获取文件位置
            "filename": filename,  # 获取文件名
            "from": fr,  # 判断来自单曲还是歌单
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取时间
        }
        info = music.search(Q["id"] == nid)
        if info:  # 数据库储存
            music.update(cf, Q["id"] == nid)
        else:
            music.insert(cf)
        logger.debug(f"Download:{filename}")
        await self.upload_data_file(event=event, data=cf)

    async def start_upload(self, ids: List[int], event: Union[GroupMessageEvent, PrivateMessageEvent]):
        """一般地 320k及以上即 flac, 320k及以下即 mp3,96k及以下即 m4a
        """
        data: list = self.get_detail(ids)
        for i in range(len(ids)):
            await self.upload(data[i], "song" if len(ids) == 1 else "list", event)

        # if is_zip:
        #     await self.get_zip(lid=lid, filenames=filenames)
        # return not_zips


nncm = Ncm()
info = ncm_user_cache.search(Q.uid == "user")
if info:
    logger.info("检测到缓存，自动加载用户")
    nncm.load_user(info[0]['session'])
    nncm.get_user_info()
elif ncm_config.ncm_phone is None:
    logger.warning("您未填写账号,自动进入二维码登录模式")
    nncm.get_qrcode()
elif ncm_config.ncm_password is None:
    logger.warning("您未填写密码,自动进入手机验证码登录模式")
    nncm.get_phone_login()
else:
    nncm.login()
