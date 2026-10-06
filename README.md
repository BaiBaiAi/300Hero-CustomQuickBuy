# 300Hero 自定义快捷购买

独立的六格装备栏项目，基于现有项目确认过的游戏 Lua 回调重新实现。没有复制原 `entry.lua`、商城或背包覆盖脚本。

## 功能

- 六格栏挂在 `EquipArea`，位置为相对坐标 `(10, -55)`；使用游戏物品图标和边框。
- 单击每格购买一件装备。装备在当前背包六格中时显示遮罩并禁止重复购买；卖出后恢复。
- 从商城物品列表或推荐列表拖到自定义栏即可设置该格。原商城拖动在未落到自定义栏时照常执行。
- 按英雄 ID 保存到 `external_lua/custom_quickbuy/heroes/<ID>.txt`，下一次选择该英雄自动读取；各英雄相互独立。
- 商城给出价格后，栏位下方显示距离当前价格所差的金币。原预购槽下方也显示差额；金币达到目标时闪光并可单击购买。
- 通知使用原脚本相同的大厅聊天、对局聊天与系统提示入口；另写入 `quickbuy.log`。

## 安装

前提：客户端已安装原项目的 `external_lua` 启动引导，且能在游戏启动时执行 `external_lua/entry.lua`。本项目不包含客户端版本相关的 JMP 引导补丁。

1. 关闭游戏。
2. 在本项目目录运行 `python install.py "C:\\300\\JumpGame\\300Hero"`，按实际游戏目录修改路径。
3. 启动游戏，选择英雄并进入对局。首次进入角色的六格为空，将商城装备拖入槽位配置。

安装器会先备份已有 `external_lua/entry.lua`，然后部署本项目的独立入口。原项目其他自动化功能不会随这个独立入口启动；需要恢复时，把 `entry.before_custom_quickbuy.*.lua` 复制回 `entry.lua`。角色配置文件不会被安装器覆盖。

仓库中的 Lua 源码使用 UTF-8；安装器会将界面通知文本转换为游戏所用的 GBK 编码。

如果游戏更新后 `external_lua` 引导失效，先按原项目的安装说明恢复引导，再运行本项目安装器。请勿把旧版本清单 XML 直接覆盖到新客户端。

## 工作原理与边界

角色 ID 来自选人回调，加载画面通过本人头像路径补抓；有 `XGetHeroNameByID` 时会验证 ID。商城拖动来源由 `Market_pullPicbyUstID` 记录，在 `Market_pullPicXLUP` 松手时检测槽位坐标。购买使用 `XClickMarketGoods(id, 1)` 后再调用 `XClickMarketBuyAndSell(1)`，沿用商城确认逻辑。

金币差额来自商城下发的当前物品价格及 `FightBag_ReciveMoney`。若某商品尚未进入本局商城列表，则该格暂不显示差额；商品价格与服务端最终可购买价可能受合成材料影响，最终以游戏商城为准。预购差额使用预购回调下发的需求金币，和原槽计算一致。

保存文件采用 `槽位=装备ID`，六行，`0` 表示空槽。可以在游戏关闭时手动编辑。运行日志、配置文件不会提交到 Git。

## 开发与验证

本仓库独立管理 Git 历史；不会自动设置远端或推送。语法检查可用 Lua 5.1：

```powershell
lua.exe -e "assert(loadfile('external_lua/entry.lua')); assert(loadfile('external_lua/custom_quickbuy/quickbuy.lua'))"
python -m py_compile install.py
```

实际 UI 拖放、购买和通知需要在游戏客户端内验证，建议先用训练对局测试。
