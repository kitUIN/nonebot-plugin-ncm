#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Tuple, Any, Union
import nonebot
from nonebot.rule import Rule
from nonebot.log import logger
from nonebot import on_regex, on_command, on_message
from nonebot.adapters.onebot.v11 import (Message, Bot,
                                         MessageSegment,
                                         ActionFailed,
                                         GroupMessageEvent,
                                         PrivateMessageEvent)
import re

from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup, Arg
from .data_source import nncm, music, ncm_config, playlist, setting, Q, cmd

# =======nonebot-plugin-help=======
__plugin_meta__ = nonebot.plugin.PluginMetadata(
    name='✨ 基于go-cqhttp与nonebot2的 网易云 无损音乐下载 ✨',
    description='您的简单插件描述',
    usage=f'''将网易云歌曲/歌单分享到群聊即可自动解析\n回复机器人解析消息即可自动下载(需要时间)\n
            {cmd}ncm t 开启解析\n{cmd}ncm t 关闭解析\n{cmd}点歌 歌名:点歌''',
    extra={'version': '1.4.0'}
)


# ========nonebot-plugin-ncm======
# ===============Rule=============
async def song_is_open(event: GroupMessageEvent) -> bool:
    info = setting.search(Q["group_id"] == event.dict()["group_id"])
    if info:
        if info[0]["song"]:
            return ncm_config.ncm_song
    else:
        setting.insert({"group_id": event.dict()["group_id"], "song": False, "list": False})
    return False


async def playlist_is_open(event: GroupMessageEvent) -> bool:
    info = setting.search(Q["group_id"] == event.dict()["group_id"])
    if info:
        if info[0]["list"]:
            return ncm_config.ncm_list
    else:
        setting.insert({"group_id": event.dict()["group_id"], "song": False, "list": False})
    return False


async def search_check() -> bool:
    return ncm_config.ncm_search


async def music_reply_rule(event: GroupMessageEvent):
    return event.reply and event.reply.sender.user_id == event.self_id


# ============Matcher=============
ncm_set = on_command("ncm",
                     priority=1, block=False)
'''功能设置'''
music_regex = on_regex("(song|url)\?id=([0-9]+)(|&)",
                       rule=Rule(song_is_open),
                       priority=2, block=False)
'''歌曲id识别'''
playlist_regex = on_regex("playlist\?id=([0-9]+)&",
                          rule=Rule(playlist_is_open),
                          priority=2, block=False)
'''歌单识别'''
music_reply = on_message(priority=2,
                         rule=Rule(music_reply_rule),
                         block=False)
'''回复下载'''
search = on_command("点歌",
                    rule=Rule(search_check),
                    priority=2, block=False)
'''点歌'''


@search.handle()
async def search_receive(matcher: Matcher, args: Message = CommandArg()):
    if args:
        matcher.set_arg("song", args)  # 如果用户发送了参数则直接赋值


@search.got("song", prompt="要点什么歌捏?")
async def receive_song(bot: Bot,
                       event: Union[GroupMessageEvent, PrivateMessageEvent],
                       song: Message = Arg(),
                       ):
    nncm.get_session(bot, event)
    _id = await nncm.search_song(keyword=song.__str__(), limit=1)
    try:
        await bot.send(event=event, message=Message(MessageSegment.music(type_="163", id_=_id)))
        if isinstance(event, GroupMessageEvent):
            await nncm.parse_song(_id)
    except ActionFailed:
        await search.finish(event=event, message="[WARNING]: 合并转发(群)消息发送失败: 账号可能被风控")


@music_regex.handle()
async def music_receive(bot: Bot, event: GroupMessageEvent, regroup: Tuple[Any, ...] = RegexGroup()):
    nid = regroup[1]
    logger.debug(f"已识别NID:{nid}的歌曲")
    nncm.get_session(bot, event)
    await nncm.parse_song(nid)


@playlist_regex.handle()
async def music_receive(bot: Bot, event: GroupMessageEvent, regroup: Tuple[Any, ...] = RegexGroup()):
    lid = regroup[0]
    logger.debug(f"已识别LID:{lid}的歌单")
    nncm.get_session(bot, event)
    msg = await nncm.playlist(lid=lid)
    await bot.send(event=event, message=Message(MessageSegment.text(msg)))


@music_reply.handle()
async def music_reply_receive(bot: Bot, event: GroupMessageEvent):
    try:  # 防止其他回复状况报错
        message: str = event.dict()["reply"]["message"][0].data["text"]
    except Exception:
        return
    nncm.get_session(bot, event)
    nid = re.search("ID:([0-9]*)", message)
    if nid:
        await bot.send(event=event, message="少女祈祷中🙏...")
        await nncm.download(ids=[int(nid[1])])
        data = music.search(Q["id"] == int(nid[1]))
        if data:
            await nncm.upload_group_file(data)
        else:
            logger.error("数据库中未有该音乐地址数据")
    else:
        lid = re.search("LIST:([0-9]*)", message)
        info = playlist.search(Q["playlist_id"] == lid[1])
        if info:
            await nncm.download(ids=info[0]["ids"])
            for i in info[0]["ids"]:
                data = music.search(Q["id"] == i)
                if data:
                    await nncm.upload_group_file(data)
                else:
                    logger.error("数据库中未有该音乐地址数据")
        else:
            logger.error("数据库中未发现该歌单ID")


@ncm_set.handle()
async def set_receive(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):  # 功能设置接收
    true = ["True", "T", "true", "t"]
    false = ["False", "F", "false", "f"]
    logger.debug(f"权限为{event.sender.role}的用户<{event.sender.nickname}>尝试使用命令{cmd}ncm {args}")
    if event.sender.role not in ncm_config.ncm_admin:
        logger.debug(f"执行错误:用户<{event.sender.nickname}>权限{event.sender.role}不在{ncm_config.ncm_admin}中")
    elif event.get_user_id() not in ncm_config.superusers:
        logger.debug(f"执行错误:用户<{event.sender.nickname}>非超级管理员(SUPERUSERS)")
    if event.sender.role in ncm_config.ncm_admin or event.get_user_id() in ncm_config.superusers:
        if args:
            args = args.__str__().split()
            mold = args[0]
        else:
            msg = f"{cmd}ncm:获取命令菜单\r\n说明:网易云歌曲分享到群内后回复机器人即可下载\r\n" \
                  f"{cmd}ncm t:开启解析\r\n{cmd}ncm f:关闭解析\n{cmd}点歌 歌名:点歌"
            return await ncm_set.finish(message=MessageSegment.text(msg))

        info = setting.search(Q["group_id"] == event.dict()["group_id"])
        # logger.info(info)
        if info:
            if mold in true:
                # logger.info(info)
                info[0]["song"] = True
                info[0]["list"] = True
                setting.update(info[0], Q["group_id"] == event.dict()["group_id"])
                msg = "已开启自动下载功能"
                await bot.send(event=event, message=Message(MessageSegment.text(msg)))
            elif mold in false:
                info[0]["song"] = False
                info[0]["list"] = False
                setting.update(info[0], Q["group_id"] == event.dict()["group_id"])
                msg = "已关闭自动下载功能"
                await bot.send(event=event, message=Message(MessageSegment.text(msg)))
            logger.debug(f"用户<{event.sender.nickname}>执行操作成功")
        else:
            if mold in true:
                setting.insert({"group_id": event.dict()["group_id"], "song": True, "list": True})
            elif mold in false:
                setting.insert({"group_id": event.dict()["group_id"], "song": False, "list": False})

    else:
        await bot.send(event=event, message=Message(MessageSegment.text("你咩有权限哦~")))
