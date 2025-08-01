# AngelOne-Stock-Data-Analyzer

This project fetches historical candlestick data for NIFTY50 and BANKNIFTY indices from the Angel One API, calculates technical indicators (EMA, RSI, VWAP), and stores the results in CSV files for further analysis.

## Features

- Fetches OHLCV (Open, High, Low, Close, Volume) data for NIFTY50 and BANKNIFTY
- Supports multiple time intervals: 1, 3, and 15 minutes
- Calculates technical indicators:
  - EMA (9, 20, 50 periods)
  - RSI (14 period)
  - VWAP
- Handles API authentication with TOTP (2FA)
- Automatically updates CSV files with new data

## Requirements

- Python 3.7+
- Angel One API credentials (USER_ID, PASSWORD, TOTP_KEY, APP_KEY)

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/AngelOne-Stock-Data-Analyzer.git
   cd AngelOne-Stock-Data-Analyzer
   ```

2. **Create and activate a virtual environment (optional but recommended):**
   ```sh
   python -m venv myvenv
   # On Windows:
   myvenv\Scripts\activate
   # On Mac/Linux:
   source myvenv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure your environment variables:**
   - Create a `.env` file in the project root with the following content:
     ```
     USER_ID=your_user_id
     PASSWORD=your_password
     TOTP_KEY=your_totp_key
     APP_KEY=your_app_key
     ```

## Usage

Run the main script to fetch and update data:
```sh
python angle_main.py
```

CSV files for each symbol and interval will be created/updated in the project directory.

## Notes

- The script includes rate-limiting and retry logic for API calls.
- Data is saved in CSV files like `NIFTY50_ONE_MINUTE.csv`, `BANKNIFTY_FIFTEEN_MINUTE.csv`, etc.
- Make sure your Angel One API credentials are valid and you have access to the API.

## License

[MIT](LICENSE) (add a license file if you want)
