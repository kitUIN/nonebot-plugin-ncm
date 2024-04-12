

<p align="center">
  <img src="https://files.catbox.moe/7cy61g.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# nonebot-plugin-ncm

✨ 基于go-cqhttp与nonebot2的 网易云 无损音乐 点歌/下载 ✨
</div>

<p align="center">
  <a href="https://github.com/kitUIN/nonebot-plugin-ncm/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-green" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-ncm">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-ncm" alt="pypi">
  </a>
  <a href="https://github.com/nonebot/nonebot2/releases/tag/v2.0.1">
    <img src="https://img.shields.io/static/v1?label=nonebot2&message=v2.0.1&color=brightgreen" alt="nonebot">
  </a>
  <a href="https://github.com/kitUIN/nonebot-plugin-ncm/releases">
    <img src="https://img.shields.io/github/v/release/kitUIN/nonebot-plugin-ncm" alt="release">
  </a>
  <a href="https://wakatime.com/badge/user/3b5608c7-e0b6-44a2-a217-cad786040b48/project/2a431792-e82f-48f5-839c-9ee566910fe5"><img src="https://wakatime.com/badge/user/3b5608c7-e0b6-44a2-a217-cad786040b48/project/2a431792-e82f-48f5-839c-9ee566910fe5.svg" alt="wakatime"></a>
</p>


## 安装 💿
 
<details>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-ncm  
    或者  
    python -m nb_cli plugin install nonebot-plugin-ncm  
    
</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-ncm
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-ncm
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-ncm
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot-plugin-ncm"]

</details>
<details>
  <summary>如果希望使用`nonebot2 a16`及以下版本 </summary>
  
    pip install nonebot-plugin-ncm==1.1.0
</details>

## 快速使用 ▶️
将链接或者卡片分享到聊天群或机器人,回复分享的消息并输入`下载`即可进行下载  
分享之后是没有反应的,只有对需要解析的消息回复`下载`才会响应  
**默认下载状态为关闭，请在每个群内使用`/ncm t`开启,私聊则默认开启**  
![a1v9gk.png](https://files.catbox.moe/a1v9gk.png)


## 注意说明 ⚠️
- 使用的网易云账号**需要拥有黑胶VIP** 
- 默认下载最高音质的音乐,可以修改`ncm_bitrate`项更改音乐品质  
- 本程序实质为调用web接口下载音乐上传

### 命令列表 📃
| 命令                 | 备注        |
|--------------------|-----------|
| /ncm               | 获取命令菜单    |
| /ncm t             | 开启下载      |
| /ncm f             | 关闭下载      |
| /ncm search t      | 开启点歌      |
| /ncm search f      | 关闭点歌      |
| /点歌 歌名             | 点歌        |
| /ncm private qq号 t | 开启该用户私聊下载 |
| /ncm private qq号 f | 关闭该用户私聊下载 |
- 命令开始符号会自动识别[`COMMAND_START`](https://v2.nonebot.dev/docs/api/config#Config-command_start)项


## 配置文件说明 ⚙️
| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| ncm_admin_level | 否 | 1 | 设置命令权限(1:仅限superusers和群主,2:在1的基础上+管理员,3:所有用户) |
| ncm_ctcode | 否 | 86 | 手机号区域码 |
| ncm_phone | 是 |   | 网易云绑定的手机号(留空则二维码登录) |
| ncm_password | 是 |   | 网易云账号密码(留空则短信登录) |
| ncm_bitrate | 否 | 320 | 下载码率(单位K) <=96: m4a, >=320:flac, 96< mp3 <320|
```
# 这是示例
ncm_admin_level=1 # 设置命令权限(1:仅限superusers和群主,2:在1的基础上+管理员,3:所有用户)
ncm_ctcode=86 # 手机号区域码,默认86
ncm_phone=  # 手机登录,不填的话把这行删了
ncm_password=  # 密码,不填的话把这行删了
ncm_playlist_zip=False # 上传歌单时是否压缩
ncm_bitrate=320 # 下载码率(单位K) 96及以下为m4a,320及以上为flac,中间mp3
```

## 功能列表 📃
- [x] 识别/下载 网易云单曲
    - 链接
    - 卡片
    - 卡片转发
- [x] 识别/下载 网易云歌单    
    - 链接
    - 卡片
    - 卡片转发
- [x] 点歌(网易云)
- [ ] QQ音乐无损下载

# 鸣谢
- [pyncm](https://github.com/greats3an/pyncm)
- [nonebot2](https://github.com/nonebot/nonebot2)
