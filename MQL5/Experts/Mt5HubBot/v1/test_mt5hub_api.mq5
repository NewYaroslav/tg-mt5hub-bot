//+------------------------------------------------------------------+
//|                                              test_mt5hub_api.mq5 |
//|                                   Пример использования Mt5HubApi |
//+------------------------------------------------------------------+
#include <Mt5HubBot\v1\Mt5HubApi.mqh>

input string HUB_URL     = "http://127.0.0.1:8080";
input string SECRET_KEY  = "12345";
input int    BOT_ID      = 1;
input int    INTERVAL_SEC = 30; // Интервал отправки (сек)

Mt5HubApi api;
datetime last_sent = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
    api = Mt5HubApi(HUB_URL, SECRET_KEY, BOT_ID, 5000);
    EventSetTimer(1); // Проверка каждую секунду
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    EventKillTimer();
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer() {
    datetime now = TimeGMT();
    if (now - last_sent < INTERVAL_SEC)
        return;

    last_sent = now;

    // --- send_heartbeat ---
    ulong start = GetTickCount();
    bool allowed = false;
    bool ok = api.send_heartbeat(allowed);
    ulong duration = GetTickCount() - start;
    Print("send_heartbeat result: ", ok, ", allowed: ", allowed, ", duration: ", duration, " ms");

    // --- send_balance ---
    start = GetTickCount();
    ok = api.send_balance();
    duration = GetTickCount() - start;
    Print("send_balance result: ", ok, ", duration: ", duration, " ms");

    // --- send_signal ---
    start = GetTickCount();
    string symbol = Symbol();
    double volume = 0.1;
    int spread = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);
    ENUM_ORDER_TYPE direction = ORDER_TYPE_BUY;
    long timestamp_ms = (long)TimeTradeServer() * 1000;
    ok = api.send_signal(symbol, spread, volume, direction, timestamp_ms);
    duration = GetTickCount() - start;
    Print("send_signal result: ", ok, ", duration: ", duration, " ms");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {
    // Пусто — обработка сигналов идёт через таймер
}