-- Independent entry point for the existing external_lua bootstrap.
if __CQB_STARTED then return end
local chunk, err = loadfile("external_lua/custom_quickbuy/quickbuy.lua")
if not chunk then
    local f = io.open("external_lua/custom_quickbuy/error.log", "a")
    if f then f:write(tostring(err), "\n") f:close() end
    return
end
local ok, app = pcall(chunk)
if not ok then return end
__CQB_STARTED = true
__CQB_APP = app
local function run()
    local good, failure = pcall(app.tick)
    if not good then app.log("tick: " .. tostring(failure)) end
end
if g_setup_ui then
    local timer = g_setup_ui:SetTimer(0, 100)
    local ticks = 0
    timer.Timer = function()
        local good, failure = pcall(app.poll_hotkey)
        if not good then app.log("hotkey: " .. tostring(failure)) end
        ticks = ticks + 1
        if ticks >= 10 then ticks = 0 run() end
    end
    app.log("主定时器已启动")
else
    app.log("未找到 g_setup_ui，等待入口再次加载")
end
run()
