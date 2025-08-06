import os
import time
import pandas as pd
from dotenv import load_dotenv
from SmartApi.smartConnect import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
from datetime import datetime


class AngelOneLiveStreamer:
    def __init__(self):
       
        load_dotenv()
        self.user_id = os.getenv("USER_ID")
        self.password = os.getenv("PASSWORD")
        self.totp_key = os.getenv("TOTP_KEY")
        self.app_key = os.getenv("APP_KEY")
        self.feed_token = None 
        self.client = None 
        self.ws = None          
        self.tokens = {
            "NIFTY50": "99926000",
            "BANKNIFTY": "99926009"
        }
        self.subscribe_tokens = [{"exchangeType": 1, "tokens": ["99926000", "99926009"]}]  # NIFTY50 and BANKNIFTY
        self.token_symbol_map = {"99926000": "NIFTY50", "99926009": "BANKNIFTY"}

    def generate_totp(self):
        return pyotp.TOTP(self.totp_key).now()

    def login(self):
        print("[INFO] Logging in to Angel One...")
        try:
            self.client = SmartConnect(api_key=self.app_key)  # Create API client
            otp = self.generate_totp()  # Generate OTP for 2FA
            session = self.client.generateSession(self.user_id, self.password, otp)  # Login
            self.session = session  # Save session for later use
            self.feed_token = session["data"]["feedToken"]  # Save feed token for websocket
            print(f"[INFO] Login successful. Feed Token: {self.feed_token}")
            return True
        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            return False

    def on_open(self, ws):
        print("[INFO] WebSocket connection opened.")
        try:
            # Reset the subscription state to avoid duplicate tokens on reconnect
            if hasattr(self.ws, "input_request_dict"):
                self.ws.input_request_dict = {}
           
            print("[DEBUG] Subscribing with request:", {
                "correlationID": "corrid1234",
                "action": self.ws.SUBSCRIBE_ACTION,
                "params": {
                    "mode": self.ws.QUOTE,
                    "tokenList": self.subscribe_tokens
                }
            })
           
            self.ws.subscribe("corrid1234", self.ws.QUOTE, self.subscribe_tokens)
            print(f"[INFO] Subscribed to tokens: {self.subscribe_tokens}")
        except Exception as e:
            print(f"[ERROR] Subscribe failed: {e}")

    def on_data(self, ws, ticks):
        

        if not hasattr(self, 'live_data_buffers'):
            self.live_data_buffers = {}
        if not hasattr(self, 'last_candle_time'):
            self.last_candle_time = {}
        if not hasattr(self, 'candle_buffers'):
            self.candle_buffers = {}

        # Angel One sometimes sends a string (e.g., "Connection closed") or dict/list
        if isinstance(ticks, str):
            print(f"[DEBUG] Received non-dict tick data: {ticks}")
            return
        if isinstance(ticks, dict):
            ticks = [ticks]
        for data in ticks:
            if not isinstance(data, dict):
                print(f"[DEBUG] Skipping non-dict tick: {data}")
                continue

            # Use token to determine symbol name for correct CSV naming
            token = str(data.get("token", ""))
            symbol = self.token_symbol_map.get(token, data.get("name", "UNKNOWN"))

            # Initialize buffer for each symbol
            if symbol not in self.live_data_buffers:
                self.live_data_buffers[symbol] = []
            # Extract price and volume info
            ltp = float(data.get("last_traded_price") or data.get("ltp") or 0)
            volume = float(data.get("volume") or 0)
            ts = data.get("exchange_timestamp") or data.get("time") or time.time()
            try:
                ts_val = float(ts)
                # Only convert if ts is a valid float and within a reasonable range
                if ts_val > 0 and ts_val < 1e11:
                    ts_dt = datetime.fromtimestamp(ts_val)
                else:
                    raise ValueError("Timestamp out of range")
            except Exception as e:
                print(f"[DEBUG] Invalid timestamp '{ts}' in tick: {data} ({e})")
                ts_dt = datetime.now()
            self.live_data_buffers[symbol].append({"ltp": ltp, "volume": volume, "ts": ts_dt})

            # Keep only the last 2000 ticks for memory efficiency
            self.live_data_buffers[symbol] = self.live_data_buffers[symbol][-2000:]

            # Create DataFrame from buffer
            buf_df = pd.DataFrame(self.live_data_buffers[symbol])
            buf_df = buf_df.sort_values("ts")
            buf_df.set_index("ts", inplace=True)

            for interval, label in [("1T", "1min"), ("3T", "3min"), ("15T", "15min")]:
                # Resample to OHLCV
                ohlcv = buf_df["ltp"].resample(interval).ohlc()
                ohlcv["volume"] = buf_df["volume"].resample(interval).sum()
                ohlcv = ohlcv.dropna()
                if ohlcv.empty:
                    continue
                # Track last candle time to avoid duplicate writes
                last_time = self.last_candle_time.get((symbol, label))
                # Only save new candles
                new_ohlcv = ohlcv if last_time is None else ohlcv[ohlcv.index > last_time]
                if new_ohlcv.empty:
                    continue
                for idx, row in new_ohlcv.iterrows():
                    # Calculate indicators on the window up to this candle
                    candle_window = ohlcv.loc[:idx]
                    # EMA
                    ema9 = candle_window["close"].ewm(span=9, adjust=False).mean().iloc[-1] if len(candle_window) >= 9 else None
                    ema20 = candle_window["close"].ewm(span=20, adjust=False).mean().iloc[-1] if len(candle_window) >= 20 else None
                    ema50 = candle_window["close"].ewm(span=50, adjust=False).mean().iloc[-1] if len(candle_window) >= 50 else None

                    # RSI
                    if len(candle_window) >= 15:
                        delta = candle_window["close"].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        rsi_val = rsi.iloc[-1]
                    else:
                        rsi_val = None
                        
                    # VWAP
                    vwap_val = None
                    if candle_window["volume"].sum() > 0:
                        vwap_val = (candle_window["close"] * candle_window["volume"]).sum() / candle_window["volume"].sum()
                    # Prepare output row
                    out_row = {
                        "Datetime": idx,
                        "Open": row["open"],
                        "High": row["high"],
                        "Low": row["low"],
                        "Close": row["close"],
                        "Volume": row["volume"],
                        "EMA9": ema9,
                        "EMA20": ema20,
                        "EMA50": ema50,
                        "RSI14": rsi_val,
                        "VWAP": vwap_val
                    }
                    out_df = pd.DataFrame([out_row])
                    filename = f"live_{symbol}_{label}.csv"
                    out_df.to_csv(filename, mode="a", header=not os.path.exists(filename), index=False)
                    print(f"[CANDLE {label}] {symbol} {idx} | O:{row['open']} H:{row['high']} L:{row['low']} C:{row['close']} V:{row['volume']} | EMA9:{ema9} EMA20:{ema20} EMA50:{ema50} RSI14:{rsi_val} VWAP:{vwap_val}")
                    self.last_candle_time[(symbol, label)] = idx


    def on_error(self, ws, error):
        # Step 4: Handle WebSocket errors
        print(f"[ERROR] WebSocket error: {error!r}")
        import traceback
        traceback.print_exc()

    def on_close(self, ws):
        # Handle WebSocket close event
        print("[INFO] WebSocket connection closed")

    def __del__(self):
        # Destructor to ensure WebSocket is properly closed
        if hasattr(self, 'ws') and self.ws:
            try:
                if hasattr(self.ws, 'sock') and self.ws.sock:
                    self.ws.sock.close()
                self.ws = None
            except Exception as e:
                print(f"[WARNING] Error during WebSocket cleanup: {e}")

    def start_streaming(self):
        # Step 6: Perform login and start the WebSocket streaming
        if not self.login():
            print("[ERROR] Exiting due to failed login.")
            return

    
        try:
            print(f"[DEBUG] Instantiating SmartWebSocketV2 with auth_token={self.session['data']['jwtToken']}, api_key={self.app_key}, client_code={self.user_id}, feed_token={self.feed_token}")
            self.ws = SmartWebSocketV2(
                f"Bearer {self.session['data']['jwtToken']}",
                self.app_key,                     
                self.user_id,                     
                self.feed_token                   
            )
            print("[DEBUG] SmartWebSocketV2 instantiated successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to instantiate SmartWebSocketV2: {e}")
            import inspect
            print("[DEBUG] SmartWebSocketV2 signature:", inspect.signature(SmartWebSocketV2))
            raise
        # Attach callback functions with proper binding
        self.ws.on_open = self.on_open
        self.ws.on_data = self.on_data
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close
        print("[INFO] Starting live data stream...")
        try:
            self.ws.connect()
        except Exception as e:
            print(f"[ERROR] WebSocket connection failed: {e}")
            raise

def main():
    # Entry point: create the streamer and start streaming
    streamer = AngelOneLiveStreamer()
    streamer.start_streaming()

if __name__ == "__main__":
    main()
