# AngelOne Live Market Data & Technical Indicators

This project provides real-time market data streaming for NIFTY50 and BANKNIFTY indices using Angel One SmartAPI. It calculates and displays key technical indicators including EMAs, RSI, and VWAP in real-time.

## Features
- Secure login to Angel One with TOTP 
- Real-time WebSocket connection to Angel One SmartAPI
- Supports NIFTY50 and BANKNIFTY indices
- Calculates and displays multiple timeframes (1min, 3min, 15min)
- Implements technical indicators:
  - EMA (9, 20, 50 periods)
  - RSI (14 periods)
  - VWAP (Volume Weighted Average Price)
- Data persistence to CSV files for each symbol and timeframe
- Automatic handling of connection, reconnection, and errors

## Requirements
- Python 3.7+
- Angel One SmartAPI account and credentials
- `.env` file in the project directory with:
  ```env
  USER_ID=your_user_id
  PASSWORD=your_password
  TOTP_KEY=your_totp_key
  APP_KEY=your_app_key
  ```
- Required Python packages:
  ```sh
  pip install smartapi-python python-dotenv pyotp pandas websocket-client
  ```

## Usage
1. Ensure your `.env` file is present in the project directory.
2. Activate your Python virtual environment (if using one):
   ```sh
   venv\Scripts\activate
   ```
3. Run the script:
   ```sh
   python live_streaming.py
   ```

## Output
- Live tick data will be printed in the console.
- Each tick is also appended to a CSV file named `live_<symbol>.csv` (e.g., `live_NIFTY50.csv`).

## Market Hours
- The script will only receive live data during NSE/BSE market hours:
  - **Monday–Friday, 09:15 to 15:30 IST**
- If run outside market hours, you may see connection attempts and errors (this is expected)

## Troubleshooting
- **No data / connection closed errors:** 
  - Check if market is open
  - Verify internet connection
  - Ensure your Angel One account has API access enabled
- **Missing indicator values:**
  - EMA/RSI require minimum data points (9/20/50 for EMA, 14 for RSI)
  - VWAP requires non-zero volume data
- **Credentials errors:** 
  - Verify `.env` file contains correct credentials
  - Ensure TOTP key is valid
- **Data inconsistencies:**
  - Delete existing CSV files if you want to start fresh
  - Check for sufficient disk space

## References
- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs/)
- [SmartAPI Python SDK](https://github.com/angel-one/smartapi-python)

  ```sh
  pip install smartapi-python python-dotenv pyotp pandas websocket-client logzero
  ```

## Usage
1. Make sure your `.env` file is present in the project directory.
2. Activate your Python virtual environment (if using one):
   ```sh
   venv\Scripts\activate
   ```
3. Run the script:
   ```sh
   python live_streaming.py
   ```

## Output
- Live tick data will be printed in the console.
- Each tick is also appended to a CSV file named `live_<symbol>.csv` (e.g., `live_NIFTY50.csv`).

## Customization

### Adding More Tokens
To subscribe to additional symbols, update the `self.tokens` and `self.token_symbol_map` dictionaries in the script:

```python
self.tokens = {
    "NIFTY50": "99926000",
    "BANKNIFTY": "99926009",
    "RELIANCE": "2885",
    "TCS": "11536"
}
self.token_symbol_map = {
    "99926000": "NIFTY50",
    "99926009": "BANKNIFTY",
    "2885": "RELIANCE",
    "11536": "TCS"
}
```

### Adjusting Timeframes
Modify the `interval` loop in the `on_data` method to change or add timeframes:

```python
for interval, label in [("1T", "1min"), ("3T", "3min"), ("15T", "15min")]:
    # Processing code
```

## Notes
- The script maintains a buffer of the last 2000 ticks for calculations
- Data is appended to CSV files in real-time
- For production use, consider adding:
  - More robust error handling
  - Logging to file
  - Automatic reconnection logic
  - Rate limiting to prevent API throttling

## References
- [Angel One SmartAPI Docs](https://smartapi.angelbroking.com/docs/)
- [SmartAPI Python SDK](https://github.com/angel-one/smartapi-python)
