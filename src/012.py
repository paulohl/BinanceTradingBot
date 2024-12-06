import time
import logging
import json
import asyncio
import traceback
from decimal import Decimal
from datetime import datetime, timezone
from binance import ThreadedWebsocketManager
from binance import Client
from binance import BinanceSocketManager
import ccxt.async_support as ccxt
import aiohttp
import websockets
from binance.client import Client
import yfinance
from datetime import datetime, timezone


# Configure logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def get_readable_time(timestamp=None):
    if timestamp:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

# تنسيق الوقت القابل للقراءة مع الملي ثانية
readable_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
print(readable_time)


# إعدادات الحساب التجريبي أو الحقيقي
api_key = 'Ip34AErsSV4ipNO4djK7MZcLRUHabB0tWsqkVmXYc9PqqGDaTqTUPbvfXVkWkeZW'
api_secret = '0vukwNUxkNSwjJC0byzWYL2QwpNQ2Noztk23XPNjUd3nxnipL5Dr7hExVc89OWr0'
testnet = True  # تعيين True للحساب التجريبي أو False للحساب الحقيقي

# الاتصال بواجهة Binance Testnet Spot مع تمكين مزامنة الوقت
try:
    if testnet:
        binance = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'proxies': None,  # تعطيل استخدام البروكسي
            'options': {
                'adjustForTimeDifference': True  # تمكين مزامنة الوقت التلقائية
            },
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision',  # عنوان API للحساب التجريبي
                    'private': 'https://testnet.binance.vision'  # عنوان API الخاص بالحساب التجريبي
                }
            }
        })
    if testnet:
        binance.set_sandbox_mode(True)
        
except ccxt.BaseError as e:
    print(f"CCTX Error: {e}")


# إعداد python-binancea
binance_client = Client(
    'YOUR_API_KEY',
    'YOUR_API_SECRET',
   requests_params={"proxies": {"https": None}}
)
bsm = BinanceSocketManager(binance_client)   


symbol = input("Enter the trading pair symbol: ")
print("The entered trading symbol is:", symbol)


# تهيئة BinanceSocketManager مع تمرير الجلسة المخصصةc
client = Client(api_key, api_secret, testnet=True)


async def kline_milliseconds(symbol):
    url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@trade"
    try:
        async with websockets.connect(url) as ws:
            logging.info(f"Connected to WebSocket for {symbol} @trade.")

            current_millisecond = None
            open_price = None
            printed_candle_color = None

            while True:
                candle_color = None
                try:
                    # Receive data
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(msg)

                    # Extract relevant data
                    current_price = Decimal(data['p'])
                    trade_time = int(data['T'])  # Trade time in milliseconds

                    # Detect candle start
                    if current_millisecond is None or trade_time != current_millisecond:
                        current_millisecond = trade_time
                        open_price = current_price

                    # Determine candle color
                    if open_price is not None:
                        if current_price > open_price:
                            candle_color = "Green"
                            if not trade_manager.has_open_trade:
                                await execute_buy_order(symbol, current_price)
                                trade_manager.last_trade_time = datetime.now()  # Update last trade time
                        elif current_price < open_price:
                            candle_color = "Red"
                            if trade_manager.has_open_trade:
                                await execute_sell_order(symbol, current_price)
                                trade_manager.last_trade_time = datetime.now()  # Update last trade time
                        else:
                            candle_color = None  # No color when price remains unchanged

                    # Skip logging if the price hasn't changed
                    if current_price == open_price:
                        candle_color = None

                    if candle_color is not None and candle_color != printed_candle_color:
                        printed_candle_color = candle_color
                        logging.info(
                            f"{candle_color} Candle Detected: Open Price: {open_price}, Current Price: {current_price}"
                        )

                except asyncio.TimeoutError:
                    logging.warning("Timeout while waiting for WebSocket data. Retrying...")
                    continue
                except json.JSONDecodeError:
                    logging.error(f"Received invalid JSON data: {msg}")
                    continue
                except Exception as e:
                    logging.error(f"Error while processing data: {e}")
                    traceback.print_exc()
                    continue

    except Exception as e:
        logging.error(f"WebSocket connection failed for {symbol}: {e}")





# نموذج حالة التداول
class TradeManager:
    def __init__(self, initial_balance):
        self.has_open_trade = False
        self.recently_sold = False
        self.profit_or_loss = Decimal('0.0')
        self.total_balance = Decimal(initial_balance)  # الرصيد الإجمالي بعد البيع
        self.initial_balance = Decimal(initial_balance)
        self.open_price = None
        self.current_price = None
        self.candle_time = None
        self.last_trade_time = None  # Track last trade timestamp
        self.coin = None

    def update_after_buy(self, coin, open_price, current_price, candle_time):
        self.has_open_trade = True
        self.coin = coin
        self.open_price = open_price
        self.current_price = current_price
        self.candle_time = candle_time
        # الرصيد الإجمالي بعد الصفقة يظل كما هو لأننا في حالة شراء
        self.total_balance = self.total_balance


    def update_after_sell(self, balance_before_sell, balance_after_sell, coin, open_price, current_price, candle_time):
        self.has_open_trade = False  # يتم إغلاق الصفقة بعد البيع
        self.recently_sold = True  # تحديث الحالة
        self.coin = None  # إزالة العملة
        self.open_price = None  # إعادة تعيين سعر الفتح
        self.current_price = current_price  # تحديث السعر الحالي
        self.candle_time = candle_time  # تحديث وقت الشمعة
        self.total_balance = balance_after_sell  # تحديث الرصيد الإجمالي
        self.profit_or_loss = balance_after_sell - balance_before_sell  # حساب المكسب أو الخسارة


    def reset_trade_status(self):
        self.has_open_trade = False
        self.recently_sold = False


# طباعة ملخص الصفقة
def display_trade_status(action, candle_color, symbol, open_price, close_price=None, current_price=None, profit_or_loss=None, initial_balance=None, total_balance=None, timestamp=None):
    print("\n--- Trade Summary ---")    
    print(f"Timestamp: {timestamp}")  # توقيت الصفقة
    print(f"Symbol: {symbol}")  # نوع العملة
    print(f"Candle Color: {candle_color}")  # لون الشمعة
    print(f"Action: {action}")  # حالة الصفقة (شراء/بيع)
   

    if open_price is not None:
       print(f"Open Price: {open_price:.2f} USDT")

    if close_price is not None:
        print(f"Close Price: {close_price:.2f} USDT")  # Close price if available
    
    if current_price is not None:
        print(f"Current Price: {current_price:.2f} USDT")  # السعر المغلق إذا وجد

    if profit_or_loss is not None:
       print(f"Profit/Loss: {profit_or_loss:.2f} USDT")  # الربح أو الخسارة إذا حسبت

    if initial_balance is not None:
        print(f"Initial Balance: {initial_balance:.2f} USDT")  # الرصيد الابتدائي

    if total_balance is not None:
        print(f"Total Balance: {total_balance:.2f} USDT")  # إجمالي الرصيد
        print("----------------------------------------")


# إدخال الرصيد الابتدائي كـ Decimal
initial_balance = Decimal(input("Enter the initial balance: "))

# تهيئة كائن TradeManager
trade_manager = TradeManager(initial_balance)





async def execute_buy_order(symbol, current_price):
    candle_color = "Green"

    if not trade_manager.has_open_trade:  # Check if no open trade exists
        coin = symbol
        open_price = current_price  # Set open_price to current_price
        candle_time = await get_readable_time()  # Get current timestamp

        # الرصيد قبل الصفقة هو الرصيد الابتدائي
        balance_before_sell= trade_manager.initial_balance

        # لا يتم تغيير الرصيد الإجمالي أثناء الشراء
        balance_after_sell = trade_manager.total_balance  # يبقى كما هو



        # تحديث بيانات الصفقة بعد الشراء
        trade_manager.update_after_buy(coin, open_price, current_price, candle_time)

        # عرض ملخص الصفقة
        display_trade_status(
            action="BUY",
            candle_color=candle_color,
            symbol=symbol,
            open_price=open_price,
            current_price=current_price,
            profit_or_loss=None,  # No profit/loss for a buy action
            initial_balance=trade_manager.initial_balance,
            total_balance=trade_manager.total_balance,
            timestamp=candle_time
        )
        return True  # Return a success status
    else:
        print("Buy order ignored: An open trade already exists.")
        return False  # Return a failure status




total_balance =Decimal('0.0')# دالة غير متزامنة لتنفيذ عملية البيع

async def execute_sell_order(symbol, current_price):
    candle_color = "Red"

    if trade_manager.has_open_trade:
        coin = symbol
        candle_time = await get_readable_time()

        # الرصيد قبل البيع
        balance_before_sell = trade_manager.total_balance

        # افتراض قيمة المكسب أو الخسارة (يمكن تعديل ذلك حسب منطقك)
        profit_or_loss = Decimal('0.0')

        # تحديث الرصيد بعد البيع بناءً على المكسب أو الخسارة
        balance_after_sell = balance_before_sell + profit_or_loss

        # حساب المكسب أو الخسارة بناءً على الفرق بين الرصيد بعد البيع والرصيد قبل البيع
        profit_or_loss = balance_after_sell - balance_before_sell

        # تحديث الرصيد الإجمالي بعد البيع
        trade_manager.total_balance = balance_after_sell

        # تحديث بيانات التداول
        trade_manager.update_after_sell(
            balance_before_sell=balance_before_sell,
            balance_after_sell=balance_after_sell,
            coin=coin,
            open_price=trade_manager.open_price,
            current_price=current_price,
            candle_time=candle_time
        )

        # عرض ملخص الصفقة
        display_trade_status(
            action="SELL",
            candle_color=candle_color,
            symbol=symbol,
            open_price=trade_manager.open_price,
            current_price=current_price,
            profit_or_loss=profit_or_loss,
            initial_balance=balance_before_sell,
            total_balance=balance_after_sell,
            timestamp=candle_time
        )

        # تعيين حالة "تم البيع مؤخرًا" لمنع الحساب حتى تحدث عملية شراء جديدة
        trade_manager.recently_sold = True
        return True  # Return a success status
    else:
        print("Sell order ignored: No open trade exists.")
        return False  # Return a failure status



      


# تعريف الدالة fetch_ticker_data
async def fetch_ticker_data(symbol):
    try:
        # افتراض أن binance هو كائن تم تهيئته من ccxt.async_support
        response = await binance.fetch_ticker(symbol)
        print("Ticker Data:", response)
        
        # تحويل القيم الأساسية إلى Decimal
        last_price = Decimal(response['last'])
        high_price = Decimal(response['high'])
        low_price = Decimal(response['low'])
        open_price = Decimal(response['open'])
        volume = Decimal(response['quoteVolume'])
        
        print("The entered trading symbol is:", symbol)
        
        print("Ticker Data:")
        print(f"Last Price: {last_price}")
        print(f"High Price: {high_price}")
        print(f"Low Price: {low_price}")
        print(f"Open Price: {open_price}")
        print(f"Volume: {volume}")
        
        return {
            "last_price": last_price,
            "high_price": high_price,
            "low_price": low_price,
            "open_price": open_price,
            "volume": volume
        }
        
    except Exception as e:
        logging.error(f"Error fetching ticker data for {symbol}: {e}")
        return None

# التحقق من توفر السيولة قبل التداول
async def check_balance(symbol, retries=3):
    for attempt in range(retries):
        try:
            # استخدام await للحصول على البيانات بشكل غير متزامن
            balance = await binance.fetch_balance()
            asset = symbol.split('/')[0]  # الرمز الأساسي مثل STORJ
            usdt_balance = Decimal(balance['total'].get('USDT', 0))
            asset_balance = Decimal(balance['total'].get(asset, 0))
            storj_balance = Decimal(balance['total'].get('STORJ', 0))

            # إرجاع النتائج
            logging.info(f"USDT Balance: {usdt_balance}, Asset Balance ({asset}): {asset_balance}")
            if usdt_balance < 0 or asset_balance < 0:
                raise ValueError("Invalid balance value.")
            return usdt_balance, storj_balance

        except Exception as e:
            logging.error(f"Error fetching balance (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # استخدام asyncio.sleep بدلاً من time.sleep
            else:
                return 0, 0
            



async def handle_tick_data(symbol, data):
    """
    معالجة بيانات التداول اللحظية
    """
    try:
        trade_id = data['a']
        price = Decimal(data['p'])
        quantity = Decimal(data['q'])
        event_time = data['T']

        print(f"Trade ID: {trade_id}, Price: {price}, Quantity: {quantity}, Time: {event_time}")

        # يمكنك إضافة استراتيجيتك هنا بناءً على البيانات اللحظية
    except Exception as e:
        logging.error(f"Error handling tick data: {e}")


async def sync_time(fetch_server_time, retries=5, acceptable_difference=500):
    for attempt in range(retries):
        try:
            server_time = await fetch_server_time()
            server_timestamp = int(server_time)
            local_timestamp = int(time.time() * 1000)

            time_difference = server_timestamp - local_timestamp
            logging.info(f"Time difference: {time_difference} milliseconds")

            if abs(time_difference) <= acceptable_difference:
                logging.info(f"Time synchronized successfully with acceptable difference: {time_difference} milliseconds.")
                return time_difference
            else:
                logging.warning(f"Time difference ({time_difference} milliseconds) exceeds acceptable limit. Retrying...")

        except Exception as e:
            logging.error(f"Error syncing time (attempt {attempt + 1}/{retries}): {e}")

        # Retry immediately with minimal delay
        await asyncio.sleep(0.1)

    logging.error("Failed to sync time after multiple attempts.")
    return None



async def fetch_server_time():
    # جلب الوقت من خادم Binance API
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.binance.com/api/v3/time") as response:
            data = await response.json()
            return data['serverTime']  # الاحتفاظ بالوقت بوحدة الملي ثانية



# دالة رئيسية
async def main():
    retry_count = 3
    for attempt in range(retry_count):
        try:
            # مزامنة الوقت مع خادم Binance
            time_diff = await sync_time(fetch_server_time)
            if time_diff is None:
                logging.error("Time synchronization failed. Exiting.")
                return  # الخروج إذا لم تنجح مزامنة الوقت

            logging.info(f"Time synchronized successfully: {time_diff * 1000} milliseconds difference.")

            # بدء WebSocket لمعالجة البيانات اللحظية (بالمللي ثانية)
            await kline_milliseconds(symbol)  # تمرير الرمز للعملة
            break  # الخروج عند النجاح
        except asyncio.TimeoutError:
            logging.warning(f"Attempt {attempt + 1}: WebSocket connection timeout. Retrying...")
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}: WebSocket connection failed: {e}")
        finally:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # الفاصل الزمني المتزايد (2, 4, 8 ثوانٍ)
                logging.info(f"Retrying connection after {wait_time * 1000} milliseconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error("WebSocket connection failed after multiple attempts. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())


RECEIVE_TIMEOUT = None 
# دالة لجلب بيانات السعر اللحظي باستخدام WebSocket
async def get_realtime_price(symbol):
    global previous_price, has_open_trade

    # تهيئة Binance Client و BinanceSocketManager
    client = Client(api_key, api_secret, testnet=True)
    bsm = BinanceSocketManager(client)

    # فتح قناة التداول
    socket = bsm.trade_socket(symbol=symbol.upper())

    try:
        async with socket as stream:
            while True:
                try:
                    # استقبال البيانات اللحظية
                    data = await stream.recv()

                    # جلب السعر اللحظي (سعر التداول الحالي)
                    current_price = Decimal(data['p'])

                    # إذا كان لدينا سعر سابق
                    if previous_price is not None:
                        # نقارن السعر الحالي بالسعر السابق
                        if current_price < previous_price and has_open_trade:
                            print(f"Price dropped from {previous_price} to {current_price}, executing sell order...")
                            amount = Decimal('10')  # مثال على الكمية المطلوبة للبيع
                            await execute_sell_order(symbol, sell_price=current_price, amount=amount)
                            has_open_trade = False  # تحديث حالة الصفقة لتكون مغلقة
                            previous_price = current_price  # تحديث السعر السابق بعد التنفيذ
                            return  # إنهاء الدالة بعد تنفيذ الصفقة

                    # تحديث `previous_price` إلى `current_price`
                    previous_price = current_price

                    # طباعة السعر اللحظي
                    print(f"Current Price: {current_price}")

                except asyncio.TimeoutError:
                    logging.warning("Timeout error: Retrying connection...")
                    break  # الخروج من الحلقة في حالة المهلة
                except Exception as e:
                    logging.error(f"Error in get_realtime_price: {e}")
                    break

    finally:
        # إغلاق الاتصال عند الانتهاء
        await client.close_connection()



# وظيفة لحساب الكمية المطلوبة بالدولار
async def calculate_trade_amount(symbol, usd_amount, retries=3):
    global initial_balance
    for attempt in range(retries):
        try:
            # Fetch ticker data بشكل غير متزامن
            ticker = await binance.fetch_ticker(symbol)
            current_price = Decimal(ticker['last'])

            # Fetch balance بشكل غير متزامن
            usdt_balance, _ = await check_balance("Initial Balance Check")
            initial_balance = usdt_balance
            logging.info(f"Trade amount set to: {initial_balance} USDT")

            if current_price <= 0:
                raise ValueError("Invalid price value.")
            logging.info(f"Current price for {symbol}: {current_price}")
            return usd_amount / current_price

        except Exception as e:
            logging.error(f"Error calculating trade amount (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # استخدام asyncio.sleep بدلاً من time.sleep
            else:
                return 0
       

async def check_market_liquidity(symbol, retries=3):
    attempt_counter = 0  # Initialize attempt counter

    for attempt in range(retries):
        try:
            # Fetch the order book for the given symbol asynchronously
            depth = await binance.fetch_order_book(symbol, limit=5)
            if not depth or 'bids' not in depth or 'asks' not in depth:
                raise ValueError("Invalid order book data.")

            # Calculate the total highest bid and lowest ask
            highest_bid = sum([Decimal(bid[1]) for bid in depth['bids']])
            lowest_ask = sum([Decimal(ask[1]) for ask in depth['asks']])  # Fixed the missing closing parenthesis
            logging.info(f"Market liquidity - Bid: {highest_bid}, Ask: {lowest_ask}")

            # Check available liquidity against the current balance
            usdt_balance, asset_balance = await check_balance(symbol)
            if usdt_balance < initial_balance:
                logging.warning(f"Insufficient USDT balance: {usdt_balance}. Cannot execute trade.")
                await asyncio.sleep(5)  # Wait before the next attempt asynchronously
                attempt_counter += 1  # Increase attempt counter
                continue  # Retry fetching market liquidity

            return highest_bid, lowest_ask  # Return liquidity if sufficient balance

        except Exception as e:
            logging.error(f"Error fetching market liquidity (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2)  # Wait before retrying asynchronously
            else:
                return 0, 0  # Return default values on failure

    return 0, 0  # Final fallback return in case of failure after retries


