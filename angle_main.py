import pyotp
import os
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv
from SmartApi.smartConnect import SmartConnect

load_dotenv()

class AngelOneClient:
    def __init__(self):
        self.user_id = os.getenv("USER_ID")
        self.password = os.getenv("PASSWORD")
        self.totp_key = os.getenv("TOTP_KEY")
        self.app_key = os.getenv("APP_KEY")
        self.client = SmartConnect(api_key=self.app_key)
        self.session = None
        self.refresh_token = None

    def generate_totp(self):
        return pyotp.TOTP(self.totp_key).now()
    
    def test_ltp(self):
        """Test if API is working by getting LTP data"""
        try:
            ltp_params = {
                "exchange": "NSE",
                "tradingsymbol": "NIFTY 50",
                "symboltoken": "99926000"
            }
            print("[INFO] Testing API with LTP request...")
            ltp_data = self.client.ltpData("NSE", "NIFTY 50", "99926000")
            print(f"[INFO] LTP Test Result: {ltp_data}")
            return ltp_data.get('status', False)
        except Exception as e:
            print(f"[WARN] LTP test failed: {e}")
            return False

    def login(self):
        try:
            print(f"[INFO] Attempting login for user: {self.user_id}")
            otp = self.generate_totp()
            print(f"[INFO] Generated OTP: {otp}")
            self.session = self.client.generateSession(self.user_id, self.password, otp)
            print(f"[INFO] Session response: {self.session}")
            self.refresh_token = self.session["data"]["refreshToken"]
            print("[✓] Login successful.")
        except Exception as e:
            print(f"[✗] Login failed: {e}")
            import traceback
            traceback.print_exc()

    def get_candle_data(self, token, interval, start_time, end_time, symbol_name, max_retries=3):
        for attempt in range(max_retries):
            try:
                # Add delay to avoid rate limiting
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    print(f"[INFO] Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                
                candle_params = {
                    "exchange": "NSE",  # Try NSE instead of NFO
                    "symboltoken": token,
                    "interval": interval,
                    "fromdate": start_time.strftime("%Y-%m-%d %H:%M"),
                    "todate": end_time.strftime("%Y-%m-%d %H:%M")
                }
                
                print(f"[INFO] Fetching {symbol_name} {interval} data...")
                data = self.client.getCandleData(candle_params)
                
                # Check if API returned error
                if not data.get('status', False):
                    error_msg = data.get('message', 'Unknown API error')
                    error_code = data.get('errorcode', 'Unknown')
                    
                    if error_code == 'AB1004' and attempt < max_retries - 1:
                        print(f"[WARN] Server error {error_code}: {error_msg}. Retrying...")
                        continue
                    else:
                        print(f"[✗] API Error {error_code}: {error_msg}")
                        return
                
                # Check if we have data
                if not data.get('data'):
                    print(f"[WARN] No data returned for {symbol_name} {interval}")
                    return
                
                new_df = pd.DataFrame(data["data"], columns=[
                    "Datetime", "Open", "High", "Low", "Close", "Volume"
                ])
                new_df["Datetime"] = pd.to_datetime(new_df["Datetime"])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    new_df[col] = pd.to_numeric(new_df[col], errors='coerce')

                # Calculate EMA9, EMA20, EMA50
                new_df['EMA9'] = new_df['Close'].ewm(span=9, adjust=False).mean()
                new_df['EMA20'] = new_df['Close'].ewm(span=20, adjust=False).mean()
                new_df['EMA50'] = new_df['Close'].ewm(span=50, adjust=False).mean()

                # Calculate RSI (14-period)
                delta = new_df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                new_df['RSI'] = 100 - (100 / (1 + rs))

                # Calculate VWAP
                vwap_num = (new_df['Close'] * new_df['Volume']).cumsum()
                vwap_den = new_df['Volume'].cumsum()
                new_df['VWAP'] = vwap_num / vwap_den

                filename = f"{symbol_name}_{interval}.csv"

                if os.path.exists(filename):
                    old_df = pd.read_csv(filename)
                    old_df["Datetime"] = pd.to_datetime(old_df["Datetime"])
                    combined_df = pd.concat([old_df, new_df]).drop_duplicates(subset="Datetime").sort_values("Datetime")
                else:
                    combined_df = new_df

                combined_df.to_csv(filename, index=False)
                print(f"[✓] Updated: {filename} ({len(new_df)} new records)")
                
                # Add delay between successful requests to avoid rate limiting
                time.sleep(1)
                return
                
            except Exception as e:
                if "rate" in str(e).lower() and attempt < max_retries - 1:
                    print(f"[WARN] Rate limit hit: {e}. Retrying...")
                    continue
                else:
                    print(f"[✗] Error fetching candles for {symbol_name} {interval}: {e}")
                    return


def main():
    print("[INFO] Starting Angel One client...")
    client = AngelOneClient()
    print("[INFO] Client initialized, attempting login...")
    client.login()

    if not client.session:
        print("[ERROR] No session established, exiting...")
        return
    
    print("[INFO] Session established, proceeding with data fetch...")

    # Test API first
    if not client.test_ltp():
        print("[ERROR] API test failed, but continuing anyway...")
    
    # Use correct NSE symbol tokens
    symbols = {
        "NIFTY50": "99926000",  # NIFTY 50 Index  
        "BANKNIFTY": "99926009"  # BANK NIFTY Index
    }

    intervals = ["ONE_MINUTE", "THREE_MINUTE", "FIFTEEN_MINUTE"]
    
    end_time = datetime.now()
    start_time = end_time.replace(hour=max(10, end_time.hour-2), minute=0, second=0, microsecond=0)
    
    print(f"[INFO] Fetching data from {start_time} to {end_time}")

    for symbol_name, token in symbols.items():
        print(f"\n[INFO] Processing {symbol_name}...")
        for interval in intervals:
            client.get_candle_data(
                token=token,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                symbol_name=symbol_name
            )
            # Add delay between intervals to avoid rate limiting
            time.sleep(2)
        
        # Add longer delay between symbols
        print(f"[INFO] Completed {symbol_name}. Waiting before next symbol...")
        time.sleep(5)

if __name__ == "__main__":
    main()
