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
    local timer = g_setup_ui:SetTimer(0, 1000)
    timer.Timer = function() run() end
end
run()
