//+------------------------------------------------------------------+
//|                                                    Mt5HubApi.mqh |
//|              Interface for sending data from MT5 to external hub |
//|                                                                  |
//| This file is part of the Mt5Hub project.                         |
//|                                                                  |
//| MIT License                                                      |
//|                                                                  |
//| Copyright (c) 2025 NewYaroslav                                   |
//|                                                                  |
//| Permission is hereby granted, free of charge, to any person      |
//| obtaining a copy of this software and associated documentation   |
//| files (the "Software"), to deal in the Software without          |
//| restriction, including without limitation the rights to use,     |
//| copy, modify, merge, publish, distribute, sublicense, and/or     |
//| sell copies of the Software, and to permit persons to whom the   |
//| Software is furnished to do so, subject to the following         |
//| conditions:                                                      |
//|                                                                  |
//| The above copyright notice and this permission notice shall be   |
//| included in all copies or substantial portions of the Software.  |
//|                                                                  |
//| THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,  |
//| EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES  |
//| OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND         |
//| NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT      |
//| HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,     |
//| WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     |
//| FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR    |
//| OTHER DEALINGS IN THE SOFTWARE.                                  |
//+------------------------------------------------------------------+
#ifndef __MT5HUB_API_MQH_INCLUDED__
#define __MT5HUB_API_MQH_INCLUDED__

#property copyright "Copyright © 2025"
#property version "1.0"
#property strict

#include <hmac-cpp\hmac.mqh>
#include <hmac-cpp\hmac_utils.mqh>
#include "libs\jason.mqh"

/// 
/// Класс Mt5HubApi отвечает за взаимодействие с сервером MT5 Hub и отправку JSON-запросов.
/// 
class Mt5HubApi {
public:
	
	/// Конструктор по умолчанию
	Mt5HubApi() {
		m_bot_id = 0;
		m_login = AccountInfoInteger(ACCOUNT_LOGIN);
		m_timeout = 5000;
		m_broker = AccountInfoString(ACCOUNT_COMPANY);
		m_max_leverage = get_max_leverage();
	}
	
	/// Параметризованный конструктор
	Mt5HubApi(
			const string& server_url,
			const string& secret_key, 
			int bot_id, 
			int timeout = 5000) {
		m_server_url = server_url;
		m_secret_key = secret_key;
		m_bot_id = bot_id;
		m_login = AccountInfoInteger(ACCOUNT_LOGIN);
	    m_timeout = timeout;
		m_broker = AccountInfoString(ACCOUNT_COMPANY);
		m_max_leverage = get_max_leverage();
	}
	
	~Mt5HubApi() {};
	
    void set_server_url(const string &server_url);
    void set_secret_key(const string &secret_key);
    void set_broker(const string &broker);
    void set_bot_id(long bot_id);
    void set_login(long login);
    void set_timeout(int timeout);

    /// Вычисляет общую прибыль по всем закрытым сделкам в сессии
    double calc_total_profit();

    /// Получает максимальное плечо для символа
    int get_max_leverage(const string &symbol);

    /// Находит наибольшее плечо среди всех доступных символов
    int get_max_leverage();

    /// Отправка сигнала heartbeat с указанным плечом
    bool send_heartbeat(bool &allowed, int leverage);

    /// Отправка сигнала heartbeat с плечом по умолчанию
    bool send_heartbeat(bool &allowed);

    /// Отправка остатков и прибыли в ручном режиме
    bool send_balance(double balance, double profit);

    /// Отправка остатков и прибыли по данным с счета
    bool send_balance();

    /// Отправка сигнала торговли
    bool send_signal(const string &symbol, int spread, double volume, int direction, long timestamp_ms);

    /// Отправка сигнала торговли с ENUM_ORDER_TYPE
    bool send_signal(const string &symbol, int spread, double volume, ENUM_ORDER_TYPE direction, long timestamp_ms);

private:
    string m_server_url;   ///< URL сервера
    string m_secret_key;   ///< Секретный ключ HMAC
    string m_broker;       ///< Имя брокера
    long m_bot_id;         ///< Идентификатор бота
    long m_login;          ///< Логин трейдера
    int m_timeout;         ///< Таймаут запроса
    int m_max_leverage;    ///< Плечо по умолчанию
    
    /// Возвращает коэффициент пересчёта из валюты контракта в валюту депозита
    double get_leverage_factor(const string& symbol);
	
	/// Десериализация JSON и проверка ok=true
	bool parse_response_and_check_ok(const string &result_body, CJAVal &js);

	/// Генерация HMAC по текущим данным
	string generate_signature(long time_bucket, const string &body);
	
	/// Вспомогательная функция для проверки подписи
	bool verify_signature(const string &sig, const string &body);
	
	/// Отправка HTTP POST-запроса
	bool post_request(
        string &result_body,
        string &result_headers,
		const string &endpoint,
        const string &request_body);

};

void Mt5HubApi::set_server_url(const string& server_url) {
	m_server_url = server_url;
}

void Mt5HubApi::set_secret_key(const string& secret_key) {
	m_secret_key = secret_key;
}

void Mt5HubApi::set_broker(const string& broker) {
	m_broker = broker;
}

void Mt5HubApi::set_bot_id(long bot_id) {
	m_bot_id = bot_id;
}

void Mt5HubApi::set_login(long login) {
	m_login = login;
}

void Mt5HubApi::set_timeout(int timeout) {
	m_timeout = timeout;
}

bool Mt5HubApi::send_heartbeat(bool &allowed, int leverage) {
	CJAVal json;
	json["broker"] = m_broker;
	json["leverage"] = IntegerToString(leverage);
	
	string result_body;
    string result_headers;

	const string endpoint = "/api/v1/bot/heartbeat";
	string request_body;
	json.Serialize(request_body);

	if (post_request(result_body, result_headers, endpoint, request_body)) {
		CJAVal js(NULL, jtUNDEF);
		if (!parse_response_and_check_ok(result_body, js)) {
			return false;
		}
		
		if (!js.FindKey("allowed")) {
			Print("Failed response: missing 'allowed'");
			return false;
		}

		allowed = js["allowed"].ToBool();

		if (js.FindKey("signature")) {
			string sig = js["signature"].ToStr();
			if (verify_signature(sig, ""))
				return true;
		}
	}

	Print("Failed response: invalid signature");
	return false;
}

bool Mt5HubApi::send_heartbeat(bool &allowed) {
	return send_heartbeat(allowed, m_max_leverage);
}

bool Mt5HubApi::send_balance(
		double balance, 
		double profit) {
	CJAVal json;
	json["balance"] = DoubleToString(balance,2);
	json["profit"] = DoubleToString(profit,2);
	
	string result_body;
    string result_headers;

	const string endpoint = "/api/v1/bot/balance";
	string request_body;
	json.Serialize(request_body);

	if (post_request(result_body, result_headers, endpoint, request_body)) {
		CJAVal js(NULL, jtUNDEF);
        if (!parse_response_and_check_ok(result_body, js)) {
			return false;
		}

		if (js.FindKey("signature")) {
			string sig = js["signature"].ToStr();
			if (verify_signature(sig, ""))
				return true;
		}
	}

	Print("Failed response: invalid signature");
	return false;
}

bool Mt5HubApi::send_balance() {
	return send_balance(
		NormalizeDouble(AccountInfoDouble(ACCOUNT_BALANCE),2), 
		NormalizeDouble(calc_total_profit(),2));
}

bool Mt5HubApi::send_signal(
		const string &symbol, 
		int spread, 
		double volume, 
		int direction,
		long timestamp_ms) {
	CJAVal json;
	CJAVal obj(jtOBJ, "");
	obj["symbol"] = symbol;
	obj["spread"] = spread;
	obj["volume"] = NormalizeDouble(volume,2);
	obj["direction"] = direction;
	obj["timestamp"] = timestamp_ms;
	
	string result_body;
    string result_headers;

	const string endpoint = "/api/v1/bot/signal";
	string request_body;
	json.Clear(jtARRAY);
    json.Add(obj);
	json.Serialize(request_body);

	if (post_request(result_body, result_headers, endpoint, request_body)) {
		if (!parse_response_and_check_ok(result_body, json)) {
			return false;
		}

		if (json.FindKey("signature")) {
			string sig = json["signature"].ToStr();
			if (verify_signature(sig, ""))
				return true;
		}
	}

	Print("Failed response: invalid signature");
	return false;
}

bool Mt5HubApi::send_signal(
		const string &symbol, 
		int spread, 
		double volume, 
		ENUM_ORDER_TYPE direction,
		long timestamp_ms) {
	return send_signal(symbol, spread, volume, direction == ORDER_TYPE_BUY ? 1 : -1, timestamp_ms);
}

double Mt5HubApi::calc_total_profit() {
    double total_profit = 0.0;
    if(!HistorySelect(0, TimeCurrent())) {
        Print("Ошибка при выборе истории сделок!");
        return 0.0;
    }
    int deals_total = HistoryDealsTotal(); // Получаем количество сделок
    for(int i = 0; i < deals_total; i++) {
        // Получаем номер сделки по индексу
        ulong deal_ticket = HistoryDealGetTicket(i);
        const int enty_type = (int)HistoryDealGetInteger(deal_ticket, DEAL_TYPE);
        if (enty_type == DEAL_TYPE_BALANCE) continue;
        if (enty_type == DEAL_TYPE_CREDIT) continue;
        if (enty_type == DEAL_TYPE_BONUS) continue;
        if (enty_type == DEAL_TYPE_CORRECTION) continue;

        // Получаем прибыль, комиссию и свопы по сделке в валюте депозита
        double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
        double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
        double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);

        // Суммируем прибыль, вычитая комиссию и свопы
        total_profit += (profit + commission + swap);
    }

    return total_profit;
}

int Mt5HubApi::get_max_leverage(const string& symbol) {
    double contract_size = 0.0;
    if (!SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE, contract_size) || contract_size <= 0.0) {
        Print("Failed to get contract size for symbol: ", symbol);
        return -1.0;
    }
    
    double margin_initial = 0.0;
    if (SymbolInfoDouble(symbol, SYMBOL_MARGIN_INITIAL, margin_initial) && margin_initial > 0.0) {
        double leverage = contract_size / margin_initial;
        return (int)leverage;
    }
    
    double price = 0.0;
    if (!SymbolInfoDouble(symbol, SYMBOL_ASK, price) || price <= 0.0) {
        Print("Failed to get price for symbol: ", symbol);
        return -1.0;
    }

    double lot = 1.0;
    double margin = 0.0;
    if (!OrderCalcMargin(ORDER_TYPE_BUY, symbol, lot, price, margin) || margin <= 0.0) {
        Print("OrderCalcMargin failed for symbol: ", symbol, " | Error: ", GetLastError());
        return -1.0;
    }

    double position_value = lot * contract_size * get_leverage_factor(symbol);
    double leverage = position_value / margin;

    return (int)(leverage + 0.5);
}

int Mt5HubApi::get_max_leverage() {
	int max_leverage = 0;
	for (int i = SymbolsTotal(true) - 1; i >= 0; --i) {
        string symbol = SymbolName(i, true);
		int leverage = get_max_leverage(symbol);
		if (leverage > max_leverage) {
			max_leverage = leverage;
		}
	}
	return max_leverage;
}

double Mt5HubApi::get_leverage_factor(const string& symbol) {
    string base_currency   = StringSubstr(symbol, 0, 3);
    string quote_currency  = StringSubstr(symbol, 3);
    string deposit_currency = AccountInfoString(ACCOUNT_CURRENCY);

    // Если валюта контракта совпадает с валютой депозита — ничего пересчитывать не нужно
    if (base_currency == deposit_currency)
        return 1.0;

    // Если котируемая валюта контракта совпадает с валютой депозита — используем текущую цену
    if (quote_currency == deposit_currency) {
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        if (ask > 0)
            return ask;
    }

    // Пробуем найти кросс-курс: например, если контракт AUDUSD, а депозит в JPY
    string cross1 = base_currency + deposit_currency; // AUDJPY
    string cross2 = deposit_currency + base_currency; // JPYAUD

    if (SymbolSelect(cross1, true)) {
        double ask = SymbolInfoDouble(cross1, SYMBOL_ASK);
        if (ask > 0)
            return ask;
    }

    if (SymbolSelect(cross2, true)) {
        double ask = SymbolInfoDouble(cross2, SYMBOL_ASK);
        if (ask > 0)
            return 1.0 / ask;
    }

    Print("get_leverage_factor: unable to resolve exchange rate for ", base_currency, " -> ", deposit_currency);
    return 1.0; // fallback (худший случай — ошибочное значение)
}

bool Mt5HubApi::parse_response_and_check_ok(const string &result_body, CJAVal &js) {
    if (!js.Deserialize(result_body)) {
        Print("Failed to deserialize JSON response.");
        return false;
    }
    if (!js.FindKey("ok") || !js["ok"].ToBool()) {
        if (js.FindKey("error"))
            Print("Failed response: ", js["error"].ToStr());
        else
            Print("Failed response: unknown reason");
        return false;
    }
    return true;
}

string Mt5HubApi::generate_signature(long time_bucket, const string &body) {
	string payload = IntegerToString(m_bot_id) + ":" + IntegerToString(m_login) + ":" + IntegerToString(time_bucket) + ":" + body;
	return hmac::get_hmac(
        m_secret_key,
        payload,
        hmac::TypeHash::HASH_SHA256);
}

bool Mt5HubApi::verify_signature(const string &sig, const string &body) {
    const datetime timestamp = TimeGMT();
    const long bucket = timestamp / 60;
	for (long offset = -1; offset <= 1; ++offset) {
        string calc_sig = generate_signature(bucket + offset, body);
        if (sig == calc_sig) return true;
    }
    return false;
}

bool Mt5HubApi::post_request(
        string &result_body,
        string &result_headers,
		const string &endpoint,
        const string &request_body) {
    //--- Временная метка
	const datetime timestamp = TimeGMT();
    const long time_bucket = timestamp / 60;
    
    //--- Формируем HMAC-подпись
    string sig = generate_signature(time_bucket, request_body);
	
	string payload = IntegerToString(m_bot_id) + ":" + IntegerToString(m_login) + ":" + IntegerToString(time_bucket) + ":" + request_body;
	hmac::get_hmac(
        m_secret_key,
        payload,
        hmac::TypeHash::HASH_SHA256);

    //--- Формируем заголовки
    string headers = 
        "Content-Type: application/json\r\n" +
        "x-bot-id: " + IntegerToString(m_bot_id) + "\r\n" +
        "x-mt5-login: " + IntegerToString(m_login) + "\r\n" +
        "x-mt5-time: " + IntegerToString(timestamp) + "\r\n" +
        "x-mt5-signature: " + sig + "\r\n";

    //--- Подготовка тела запроса
    char request_data[];
	int request_data_size = StringLen(request_body);
    StringToCharArray(request_body, request_data, 0, request_data_size);

    //--- Буфер результата
    char result[];

    //--- Отправка запроса
	string full_url = m_server_url + endpoint;
    int res = WebRequest(
        "POST",
        full_url,
        headers,
        m_timeout,
        request_data,
        result,
        result_headers);

    ArrayFree(request_data);
	
	//--- delete BOM
	int start_index=0;
	int size = ArraySize(result);
	for(int i = 0; i < fmin(size, 8); ++i) {
		uchar byte = (uchar)result[i];
		if(byte == 0xef || byte == 0xbb || byte == 0xbf) {
			start_index = i + 1;
		} else {
			break;
		}
	}

    if (res != 200) {
        if (res == -1) {
            ArrayFree(result);
			Print("WebRequest failed. Error: ", _LastError);
            return false;
        }
        result_body = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
		ArrayFree(result);
        Print("HTTP error: ", res);
        return false;
    }

    result_body = CharArrayToString(result, start_index, WHOLE_ARRAY, CP_UTF8);
    ArrayFree(result);
    return true;
}

#endif // __MT5HUB_API_MQH_INCLUDED__