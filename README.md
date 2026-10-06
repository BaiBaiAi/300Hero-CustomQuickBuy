# 300Hero 自定义快捷购买

独立的六格装备栏项目，基于现有项目确认过的游戏 Lua 回调重新实现。没有复制原 `entry.lua`、商城或背包覆盖脚本。

## 功能

- 六格栏在战斗装备界面可见后挂到 `EquipArea`，位置为相对坐标 `(8, -55)`。商城关闭时只显示已配置槽位并向左排列，全部未配置时隐藏；商城打开时显示全部六格。
- 商城打开时右键六格中的装备可清空该格，并立即保存当前英雄配置；商城关闭时右键无效。
- 原来购买传送卷轴的单购槽位于预购槽正上方，默认装备 ID 为 `27829`。也可把商城装备拖到该槽替换；单购槽允许重复购买，按 `O` 键也可触发购买。
- 单击每格购买一件装备。装备在当前背包六格中时显示遮罩并禁止重复购买；卖出后恢复。
- 从商城物品列表或推荐列表拖到自定义栏即可设置该格。商城列表在官方禁用拖动的界面状态下也会启用这个拖动入口；未落到自定义栏时按原商城逻辑处理。
- 七个槽位按英雄 ID 保存到 `external_lua/custom_quickbuy/heroes/<ID>.txt`，下一次选择该英雄自动读取；各英雄相互独立。
- 当前英雄 ID 另存到 `external_lua/custom_quickbuy/last_hero.txt`。游戏进程结束后直接重连对局、没有选英雄回调时，会先用此 ID 加载装备；若随后收到游戏的英雄回调，会自动改用回调中的 ID。
- 只有预购槽下方显示尚缺金币；金币达到目标时闪光并可单击购买。快捷栏和单购槽不显示金额。
- 通知使用原脚本相同的大厅聊天、对局聊天与系统提示入口；另写入 `quickbuy.log`。

## 安装

本项目自带当前客户端版本的 JMP 启动引导。安装器按完整资源路径扫描游戏目录下的所有 `Data*.jmp`，只修改 `..\data\script\gamehall\setup\setup.lua`，不会修改 PVE 或 tiyan 路径。安装前会校验原资源 MD5；客户端更新后若版本不匹配，安装器会停止。

1. 关闭游戏。
2. 在本项目目录运行 `python install.py "F:\JumpGame\300Hero"`，按实际游戏目录修改路径。
3. 启动游戏，选择英雄并进入对局。首次进入角色时打开商城会看到六个空槽，将商城装备拖入槽位配置。

安装器备份原入口、脚本和 JMP 资源记录到游戏目录的 `custom_quickbuy_backups/<时间戳>/`，然后部署本项目的独立入口和 JMP 引导。原项目其他自动化功能不会随这个独立入口启动。角色配置文件和上次角色 ID 不会被安装器覆盖。

仓库中的 Lua 源码使用 UTF-8；安装器会将界面通知文本转换为游戏所用的 GBK 编码。

查看引导状态：`python install.py "F:\JumpGame\300Hero" --status`。恢复 JMP：`python install.py "F:\JumpGame\300Hero" --restore-jmp "<备份目录>\setup_jmp.json"`。恢复入口和脚本时使用同一备份目录中的文件。

Windows 安装器 EXE 可通过 `python build_exe.py` 构建，输出位于 `dist/300Hero-QuickBuy-Installer.exe`。双击后选择游戏目录，点击“安装并验证”，再进入对局测试。EXE 包含本项目的 Lua 脚本和 JMP 安装逻辑；安装前请退出游戏。

如果游戏更新后校验失败，请更新本项目的版本适配后再安装；不要把旧版本清单 XML 覆盖到新客户端。

## 工作原理与边界

角色 ID 来自选人回调，加载画面通过本人头像路径补抓；有 `XGetHeroNameByID` 时会验证 ID。商城拖动来源由 `Market_pullPicbyUstID` 记录，在 `Market_pullPicXLUP` 松手时检测槽位坐标。购买使用 `XClickMarketGoods(id, 1)` 后再调用 `XClickMarketBuyAndSell(1)`，沿用商城确认逻辑。

预购差额使用预购回调下发的需求金币与 `FightBag_ReciveMoney` 的当前金币计算。单购槽默认传送卷轴时沿用 145 金币的本地不足提示；换成其他装备后由商城处理购买条件。

保存文件采用 `槽位=装备ID`，七行，`1` 至 `6` 为快捷栏，`7` 为单购槽；未配置的单购槽默认 `27829`。可以在游戏关闭时手动编辑。运行日志、配置文件不会提交到 Git。

## 开发与验证

本仓库独立管理 Git 历史；不会自动设置远端或推送。语法检查可用 Lua 5.1：

```powershell
lua.exe -e "assert(loadfile('external_lua/entry.lua')); assert(loadfile('external_lua/custom_quickbuy/quickbuy.lua'))"
python -m py_compile install.py
python -m unittest discover -s tests -p "test_*.py"
```

实际 UI 拖放、购买和通知需要在游戏客户端内验证，建议先用训练对局测试。
