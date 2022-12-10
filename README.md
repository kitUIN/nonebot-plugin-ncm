

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
  <a href="https://github.com/nonebot/nonebot2/releases/tag/v2.0.0rc2">
    <img src="https://img.shields.io/static/v1?label=nonebot2&message=v2.0.0rc2&color=brightgreen" alt="nonebot">
  </a>
  <a href="https://github.com/kitUIN/nonebot-plugin-ncm/releases">
    <img src="https://img.shields.io/github/v/release/kitUIN/nonebot-plugin-ncm" alt="release">
  </a>
  <a href="https://wakatime.com/badge/user/3b5608c7-e0b6-44a2-a217-cad786040b48/project/2a431792-e82f-48f5-839c-9ee566910fe5"><img src="https://wakatime.com/badge/user/3b5608c7-e0b6-44a2-a217-cad786040b48/project/2a431792-e82f-48f5-839c-9ee566910fe5.svg" alt="wakatime"></a>
</p>


## 安装
### 使用pip安装
1.`pip install nonebot-plugin-ncm` 进行安装  
2.并在`bot.py`添加`nonebot.load_plugin('nonebot-plugin-ncm')`
### 使用nb-cli安装(推荐)
`nb plugin install nonebot-plugin-ncm` 进行安装

<details>
  <summary>如果希望使用`nonebot2 a16`及以下版本 </summary>
  请使用`pip install nonebot-plugin-ncm==1.1.0`进行安装
</details>

## 升级
1.`pip install nonebot-plugin-ncm --upgrade` 进行升级  
2. 低于`1.5.0`版本升级请删除`db`文件夹内`ncm`开头文件  
3. 根据新的`config`项配置`.env`文件
## 快速使用
将链接或者卡片分享到聊天群或机器人,回复分享的消息并输入`下载`即可进行下载  
**默认下载状态为关闭，请在每个群内使用`/ncm t`开启,私聊则默认开启**
![img](https://files.catbox.moe/g7c230.png)
### 命令列表：
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

## 注意说明
- 使用的网易云账号**需要拥有黑胶VIP** 
- 默认下载最高音质的音乐 
- 本程序实质为调用web接口下载音乐上传  

## 配置文件说明
```
ncm_admin_level=1 # 设置命令权限(1:仅限superusers和群主,2:在1的基础上+管理员,3:所有用户)
ncm_ctcode="86" # 手机号区域码,默认86
ncm_phone=  # 手机登录
ncm_password=  # 密码
ncm_playlist_zip=False # 上传歌单时是否压缩
```

## 功能列表
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
