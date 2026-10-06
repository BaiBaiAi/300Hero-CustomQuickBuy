-- Run from the project root with Lua 5.1.
XE_LBUP, XE_DRAG = 1, 2
UI_click_new = 1
local bought = {}
local cursor_x, cursor_y = 20, -30
local function widget(x, y, w, h)
    local self = { x = x, y = y, w = w, h = h, script = {}, children = {}, id = 1 }
    function self:AddImage(_, dx, dy, ww, hh)
        local child = widget(self.x + dx, self.y + dy, ww, hh)
        self.children[#self.children + 1] = child
        return child
    end
    function self:AddFont() return widget(self.x, self.y, 40, 15) end
    function self:GetPosition() return self.x, self.y end
    function self:GetWH() return self.w, self.h end
    function self:SetTouchEnabled() end
    function self:SetVisible(value) self.visible = value end
    function self:SetFontText(value) self.text = value end
    function self:SetImageTipWithItemId(value) self.tip = value end
    function self:EnableImageAnimate() end
    function self.changeimage() end
    return self
end
local EquipArea = widget(0, 0, 400, 130)
function InitMain_Fightbag() return EquipArea end
n_fightbag_ui = widget(0, 0, 868, 150)
local bag_open = false
function n_fightbag_ui:IsVisible() return bag_open end
local market_equip = {widget(0, 0, 167, 50)}
local market_icon = {widget(0, 0, 38, 38)}
local Market_goods = {Id = {21159}, strPictureName = {"icon.bmp"}}
function InitMain_MarketC() return market_equip, market_icon, Market_goods end
local latest_bar
CreateWindow = function(_, x, y, w, h)
    latest_bar = widget(x, y, w, h)
    return latest_bar
end
XGetMapId = function() return 2 end
XGetHeroNameByID = function(id) return id == 101 and "test" or nil end
XGetCursorPosX = function() return cursor_x end
XGetCursorPosY = function() return cursor_y end
XGetIconPathByItemID = function(id) return tostring(id) .. ".bmp" end
XGetPlayerCharItem = function() return nil end
XClickMarketGoods = function(id, count) bought[#bought + 1] = { id, count } end
XClickMarketBuyAndSell = function(flag) assert(flag == 1) end
Market_pullPicbyUstID = function() end
Market_pullPicXLUP = function() error("custom drop reached original handler") end
FightBag_ReciveMoney = function() end
local nextbuy = widget(273, 61, 36, 36)
FightBag_ReciveEquipCDInfoNextBuy = function() return nextbuy end
ClearData_EquipNextBuy = function() end
FarShop_ReciveEquip = function() end
SendData_MarketGoods = function() end
__EXTLUA_CUR_HERO = 101
os.remove("external_lua/custom_quickbuy/heroes/101.txt")

local app = assert(loadfile("external_lua/custom_quickbuy/quickbuy.lua"))()
app.tick()
assert(latest_bar == nil)
bag_open = true
app.tick()
assert(latest_bar and #latest_bar.children == 6)
assert(latest_bar.children[1].visible == 1)
assert(latest_bar.children[1].children[1].visible == 0)
market_equip[1].script[XE_DRAG]()
Market_pullPicXLUP(1)
local saved = assert(io.open("external_lua/custom_quickbuy/heroes/101.txt", "r"))
assert(saved:read("*l") == "1=21159")
saved:close()
local restored = assert(loadfile("external_lua/custom_quickbuy/quickbuy.lua"))()
restored.tick()
local copy = assert(io.open("external_lua/custom_quickbuy/heroes/101.txt", "r"))
assert(copy:read("*l") == "1=21159")
copy:close()
assert(restored.set_slot(2, 21057))
SendData_MarketGoods("item", "", "", "", "3000", 21159)
FightBag_ReciveMoney("1000")
assert(latest_bar ~= nil)
assert(restored.set_slot(1, 21159))
latest_bar.children[1].script[XE_LBUP]()
assert(#bought == 1 and bought[1][1] == 21159 and bought[1][2] == 1)
Market_pullPicbyUstID("icon", 21159, {}, 1, 1)
Market_pullPicXLUP(1)
assert(#bought == 1)
FightBag_ReciveEquipCDInfoNextBuy("", "", "", 21057, "3000", "1000")
assert(nextbuy.script[XE_LBUP] ~= nil)
nextbuy.script[XE_LBUP]()
assert(#bought == 1)
FightBag_ReciveMoney("3500")
nextbuy.script[XE_LBUP]()
assert(#bought == 2 and bought[2][1] == 21057 and bought[2][2] == 1)
print("smoke tests passed")
