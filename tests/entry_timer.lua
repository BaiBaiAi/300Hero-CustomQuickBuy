-- Verify match polling and the O hotkey share one timer.
local real_loadfile = loadfile
local app = {ticks = 0, keys = 0}
function app.tick() app.ticks = app.ticks + 1 end
function app.poll_hotkey() app.keys = app.keys + 1 end
function app.log() end
loadfile = function(path)
    if path == "external_lua/custom_quickbuy/quickbuy.lua" then
        return function() return app end
    end
    return real_loadfile(path)
end
local timers = {}
g_setup_ui = {}
function g_setup_ui:SetTimer(id, interval)
    assert(id == 0 and interval == 100)
    local timer = {}
    timers[#timers + 1] = timer
    return timer
end
assert(real_loadfile("external_lua/entry.lua"))()
assert(#timers == 1 and app.ticks == 1)
for _ = 1, 20 do timers[1].Timer() end
assert(app.keys == 20 and app.ticks == 3)
print("entry timer test passed")
