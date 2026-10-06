-- 300Hero custom quick buy. Lua 5.1; all game callbacks are installed lazily.
local M = {}
local BASE = "external_lua/custom_quickbuy/"
local hero, map, bar, area, nextbuy
local slots, ids, names, owned = {}, {}, {}, {}
local money, queued, need, drag, portraitId
local lastReconcile = 0
local installed = {}
local drag_sources = setmetatable({}, { __mode = "k" })

local function valid_id(value)
    local n = tonumber(value)
    if n and n > 0 and n == math.floor(n) then return n end
end

function M.log(message)
    local f = io.open(BASE .. "quickbuy.log", "a")
    if f then f:write(os.date("%Y-%m-%d %H:%M:%S "), tostring(message), "\n") f:close() end
end

local function notify(message)
    M.log(message)
    local text = "[快捷购买] " .. message
    local mid = type(XGetMapId) == "function" and tonumber(XGetMapId()) or nil
    if mid == 1 and type(AddChatTextToLua) == "function" then
        pcall(AddChatTextToLua, 1, 0, 0, 0, 0, 0, text)
    else
        if type(AddChatInTextToLua) == "function" then pcall(AddChatInTextToLua, 1, 0, 0, 0, 0, 0, text) end
        if type(AddStartTextToLua) == "function" then pcall(AddStartTextToLua, text) end
        if type(AddUseMessageTextToLua) == "function" then pcall(AddUseMessageTextToLua, text) end
        if type(XShowSystemInfoFormLua) == "function" then pcall(XShowSystemInfoFormLua, text) end
    end
end

local function config_path(id)
    return BASE .. "heroes/" .. tostring(id) .. ".txt"
end

local function load_hero(id)
    ids = {}
    local f = io.open(config_path(id), "r")
    if f then
        for line in f:lines() do
            local slot, item = line:match("^(%d+)%s*=%s*(%d+)%s*$")
            slot, item = tonumber(slot), valid_id(item)
            if slot and slot >= 1 and slot <= 7 then ids[slot] = item end
        end
        f:close()
    end
    if not ids[7] then ids[7] = 27829 end
    hero = id
    M.refresh()
    notify("角色 " .. id .. " 的装备配置已读取")
end

local function save_hero()
    if not hero then return false end
    local path, tmp = config_path(hero), config_path(hero) .. ".tmp"
    local f = io.open(tmp, "w")
    if not f then M.log("cannot write " .. tmp) return false end
    for i = 1, 7 do f:write(i, "=", ids[i] or 0, "\n") end
    f:close()
    local backup = path .. ".bak"
    os.remove(backup)
    local previous = io.open(path, "r")
    if previous then previous:close() os.rename(path, backup) end
    local ok, err = os.rename(tmp, path)
    if not ok then
        os.rename(backup, path)
        M.log("save failed: " .. tostring(err))
    else
        os.remove(backup)
    end
    return ok
end

local function set_hero(raw)
    local id = valid_id(raw)
    if not id or id == hero then return end
    if type(XGetHeroNameByID) == "function" then
        local ok, name = pcall(XGetHeroNameByID, id)
        if not ok or not name or name == "" or name == "?" then return end
    end
    load_hero(id)
end

function M.set_slot(index, item)
    index = tonumber(index)
    item = valid_id(item)
    if not hero or not index or index ~= math.floor(index) or index < 1 or index > 7 or not item then
        return false
    end
    local previous = ids[index]
    ids[index] = item
    if not save_hero() then ids[index] = previous return false end
    M.refresh()
    notify((index == 7 and "单购槽" or "第 " .. index .. " 格") .. "已设置为" .. (names[item] or ("装备 " .. item)))
    return true
end

local function upvalue(fn, key)
    if type(fn) ~= "function" or not debug or not debug.getupvalue then return nil end
    local index = 1
    while true do
        local name, value = debug.getupvalue(fn, index)
        if not name then return nil end
        if name == key then return value end
        index = index + 1
    end
end

local function buy(item)
    item = valid_id(item)
    if not item or type(XClickMarketGoods) ~= "function" or type(XClickMarketBuyAndSell) ~= "function" then
        notify("购买接口尚未就绪")
        return false
    end
    local ok, err = pcall(function()
        XClickMarketGoods(item, 1)
        XClickMarketBuyAndSell(1)
    end)
    if not ok then notify("购买失败: " .. tostring(err)) return false end
    if type(XClickPlaySound) == "function" then pcall(XClickPlaySound, UI_click_new) end
    notify("已尝试购买" .. (names[item] or ("编号 " .. item .. " 的")) .. "装备")
    return true
end

local function contains(control, x, y)
    if not control then return false end
    local ok, left, top = pcall(function() return control:GetPosition() end)
    if not ok or not left then return false end
    local good, w, h = pcall(function() return control:GetWH() end)
    return good and w and x >= left and x < left + w and y >= top and y < top + h
end

local function dropped_slot()
    if type(XGetCursorPosX) ~= "function" or type(XGetCursorPosY) ~= "function" then return nil end
    local x, y = XGetCursorPosX(), XGetCursorPosY()
    for i = 1, 7 do if contains(slots[i], x, y) then return i end end
end

local function wrap(name, key, callback)
    local current = _G[name]
    if type(current) ~= "function" or current == installed[key] then return end
    local wrapper = function(...)
        return callback(current, ...)
    end
    installed[key] = wrapper
    _G[name] = wrapper
end

local function install_hero_hooks()
    wrap("SetGameStart_CurrentHeroId", "hero", function(original, id, ...)
        set_hero(id)
        return original(id, ...)
    end)
    wrap("XGameHeroChoseId", "chosen", function(original, id, ...)
        set_hero(id)
        return original(id, ...)
    end)
    wrap("SetLoading_PlayerName", "loading", function(original, index, team, name, portrait, ...)
        if type(XGetSelfName) == "function" and name == XGetSelfName() and type(portrait) == "string" then
            for number in portrait:gmatch("%d+") do portraitId = tonumber(number) end
            set_hero(portraitId)
        end
        return original(index, team, name, portrait, ...)
    end)
end

local function install_drag_hooks()
    wrap("Market_pullPicbyUstID", "dragstart", function(original, picture, id, control, index, kind, ...)
        drag = (kind == 1 or kind == 2) and valid_id(id) or nil
        return original(picture, id, control, index, kind, ...)
    end)
    wrap("Market_pullPicXLUP", "dragend", function(original, kind, ...)
        local slot = drag and dropped_slot()
        local item = drag
        drag = nil
        if slot and M.set_slot(slot, item) then return end
        return original(kind, ...)
    end)
end

-- The game's shop disables XE_DRAG in some recommendation/CEF modes.
-- Attach a handler to its existing item controls so the normal drag ghost
-- can still be used for the custom bar.
local function install_market_sources()
    local controls = upvalue(InitMain_MarketC, "market_equip")
    local icons = upvalue(InitMain_MarketC, "market_icon")
    local goods = upvalue(InitMain_MarketC, "Market_goods")
    if not controls or not icons or not goods or not goods.Id then return end
    local attached = 0
    for index, control in pairs(controls) do
        if control and (not drag_sources[control] or drag_sources[control] ~= control.script[XE_DRAG]) then
            local original = control.script[XE_DRAG]
            local row = index
            local handler = function()
                local active = upvalue(InitMain_MarketC, "Market_goods") or goods
                local item = active.Id and valid_id(active.Id[row])
                if item and type(Market_pullPicbyUstID) == "function" then
                    if active.strName and active.strName[row] then names[item] = tostring(active.strName[row]) end
                    local picture = active.strPictureName and active.strPictureName[row]
                    local ok, err = pcall(Market_pullPicbyUstID, picture or "", item, icons[row], row, 1)
                    if ok then M.log("商城开始拖动装备 " .. item) return end
                    M.log("商城拖动失败: " .. tostring(err))
                end
                if type(original) == "function" then return original() end
            end
            control.script[XE_DRAG] = handler
            drag_sources[control] = handler
            attached = attached + 1
        end
    end
    if attached > 0 then M.log("商城拖动入口已接管 " .. attached .. " 个控件") end
end

local function install_gold_hooks()
    wrap("FightBag_ReciveMoney", "money", function(original, value, ...)
        money = tonumber(value)
        M.refresh_gold()
        return original(value, ...)
    end)
    wrap("FightBag_ReciveEquipCDInfoNextBuy", "queue", function(original, p1, p2, p3, item, left, current, ...)
        local result = original(p1, p2, p3, item, left, current, ...)
        queued, need, money = valid_id(item), tonumber(left), tonumber(current)
        nextbuy = upvalue(original, "nextbuy") or nextbuy
        if nextbuy then
            pcall(function() nextbuy:SetTouchEnabled(1) end)
            nextbuy.script[XE_LBUP] = function()
                if queued and money and need and money >= need and buy(queued) then
                    pcall(function() nextbuy:EnableImageAnimate(0, 6) end)
                end
            end
        end
        M.refresh_gold()
        return result
    end)
    wrap("ClearData_EquipNextBuy", "clearqueue", function(original, ...)
        queued, need = nil, nil
        M.refresh_gold()
        return original(...)
    end)
end

local function install_name_hook()
    wrap("SendData_MarketGoods", "names", function(original, name, p1, p2, p3, price, id, ...)
        local key = valid_id(id)
        if key and name and name ~= "" then names[key] = tostring(name) end
        return original(name, p1, p2, p3, price, id, ...)
    end)
end

local gold_label
function M.refresh_gold()
    if nextbuy and not gold_label then
        pcall(function()
            gold_label = nextbuy:AddFont("", 13, 8, 0, -37, 36, 15, 0xe3e38d)
            gold_label:SetTouchEnabled(0)
        end)
    end
    if gold_label then
        local difference = queued and need and money and math.max(0, need - money) or 0
        pcall(function()
            gold_label:SetVisible(difference > 0 and 1 or 0)
            gold_label:SetFontText(difference > 0 and tostring(difference) or "", 0xe3e38d)
            if nextbuy then nextbuy:EnableImageAnimate(queued and difference == 0 and 1 or 0, 6) end
        end)
    end
end

local function reconcile()
    owned = {}
    if type(XGetPlayerCharItem) ~= "function" then return end
    for index = 0, 5 do
        local ok, item = pcall(XGetPlayerCharItem, 0, index)
        if ok and type(item) == "table" then
            local id = valid_id(item.itemId)
            if id then owned[id] = true end
        end
    end
    M.refresh()
end

local function install_reconcile_hooks()
    wrap("FarShop_ReciveEquip", "farshop", function(original, ...)
        local result = original(...)
        reconcile()
        return result
    end)
end

function M.refresh()
    for i = 1, 7 do
        local slot, id = slots[i], ids[i]
        if slot then
            pcall(function()
                slot:SetVisible(1)
                if slot.icon then slot.icon:SetVisible(id and 1 or 0) end
                if id then
                    slot:SetImageTipWithItemId(id)
                    if type(XGetIconPathByItemID) == "function" then
                        local path = XGetIconPathByItemID(id)
                        if path and path ~= "" and slot.icon then slot.icon.changeimage(path) end
                    end
                    if slot.dark then slot.dark:SetVisible(i <= 6 and owned[id] and 1 or 0) end
                elseif slot.dark then
                    slot.dark:SetVisible(0)
                end
            end)
        end
    end
    M.refresh_gold()
end

local function create_single_slot(parent)
    if slots[7] then return end
    local ok, slot = pcall(function()
        return parent:AddImageMultiple("", "", "", 273, 22, 36, 36)
    end)
    if not ok or not slot then M.log("单购槽创建失败") return end
    slot:SetTouchEnabled(1)
    if type(DisableRButtonClick) == "function" then pcall(DisableRButtonClick, slot.id) end
    local icon = slot:AddImage("", 1, 1, 34, 34)
    if icon then
        icon:SetTouchEnabled(0)
        local frame = icon:AddImage((path_lolfight or "../Data/UINEW/FIGHT/") .. "farshop_side.BMP", -1, -1, 36, 36)
        if frame then frame:SetTouchEnabled(0) end
    end
    slot.icon = icon
    local caption = slot:AddFont("P", 11, 8, -3, -22, 12, 12, 0xe3e38d)
    if caption then caption:SetTouchEnabled(0) end
    slot.script[XE_LBUP] = function()
        local id = ids[7]
        if not id then return end
        if id == 27829 and money and money < 145 then
            notify("金币不足，传送卷轴需要 145 金币")
            return
        end
        buy(id)
    end
    slots[7] = slot
    M.refresh()
    M.log("单购槽已加载，装备=" .. tostring(ids[7]))
end

local function create_bar()
    local parent = upvalue(InitMain_Fightbag, "EquipArea")
    if not parent or not hero or type(CreateWindow) ~= "function" or not n_fightbag_ui then return end
    local visible, is_open = pcall(function() return n_fightbag_ui:IsVisible() end)
    if not visible or (is_open ~= true and is_open ~= 1) then return end
    if area == parent and bar then create_single_slot(parent) return end
    area, nextbuy, gold_label, bar = parent, nil, nil, nil
    local ok, result = pcall(CreateWindow, parent.id, 10, -55, 326, 59)
    if not ok or not result then return end
    bar = result
    bar:SetVisible(1)
    slots = {}
    for i = 1, 6 do
        local index = i
        local slot = bar:AddImage((path_fight or "../Data/UINEW/FIGHT/") .. "Me_equip.BMP", (i - 1) * 44, 10, 40, 40)
        if slot then
            slot:SetTouchEnabled(1)
            if type(DisableRButtonClick) == "function" then pcall(DisableRButtonClick, slot.id) end
            local icon = slot:AddImage("", 0, 0, 40, 40)
            if icon then icon:SetTouchEnabled(0) icon:SetVisible(0) end
            slot.icon = icon
            local frame = slot:AddImage((path_lolfight or "../Data/UINEW/FIGHT/") .. "farshop_side.BMP", -1, -1, 42, 42)
            if frame then frame:SetTouchEnabled(0) end
            local dark = slot:AddImage(BASE .. "dark.bmp", 0, 0, 40, 40)
            if dark then dark:SetTouchEnabled(0) dark:SetVisible(0) end
            slot.dark = dark
            slot.script[XE_LBUP] = function()
                local id = ids[index]
                if not id then return end
                if owned[id] then notify("装备 " .. id .. " 已购买") return end
                buy(id)
            end
            slots[i] = slot
        end
    end
    create_single_slot(parent)
    M.refresh()
    reconcile()
    if slots[1] then
        local good, x, y = pcall(function() return slots[1]:GetPosition() end)
        if good then M.log("首槽坐标: " .. tostring(x) .. "," .. tostring(y) .. " map=" .. tostring(map)) end
    end
    notify("六格快捷购买栏已加载")
end

function M.tick()
    install_hero_hooks()
    if not hero then set_hero(__EXTLUA_CUR_HERO) end
    local current = type(XGetMapId) == "function" and tonumber(XGetMapId()) or nil
    if current ~= map then
        map = current
        area, bar, nextbuy, gold_label, drag = nil, nil, nil, nil, nil
        money, queued, need, names, owned = nil, nil, nil, {}, {}
        slots = {}
    end
    if not current or current == 0 or current == 1 then return end
    install_drag_hooks()
    install_market_sources()
    install_gold_hooks()
    install_name_hook()
    install_reconcile_hooks()
    create_bar()
    if os.time() - lastReconcile >= 10 then lastReconcile = os.time() reconcile() end
end

return M
