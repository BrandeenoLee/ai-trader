"""All tunable settings for the tournament live here."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRY_RUN = os.environ.get("DRY_RUN") == "1"  # simulated market + fake AI, separate folders
_sfx = "_dryrun" if DRY_RUN else ""
STATE_DIR = ROOT / f"state{_sfx}"
NOTES_DIR = ROOT / f"notes{_sfx}"
DOCS_DIR = ROOT / f"docs{_sfx}"  # GitHub Pages dashboard output
if DRY_RUN and not NOTES_DIR.exists():
    shutil.copytree(ROOT / "notes", NOTES_DIR)
KILL_SWITCH_FILE = ROOT / "KILL_SWITCH"  # create this file to halt all trading

# --- Tournament -------------------------------------------------------------
STARTING_CASH = 500.00
BENCHMARK = "SPY"

STRATEGIES = {
    "A": {"name": "Momentum", "universe": "liquid"},
    "B": {"name": "Mean reversion", "universe": "liquid"},
    "C": {"name": "Catalyst reader", "universe": "liquid"},
    "D": {"name": "Small-cap explorer", "universe": "smallcap"},
    "E": {"name": "Claude's pick", "universe": "any"},
}

EXCLUDED_SYMBOLS = {"GME", "AMC"}  # never traded by any strategy

# --- Position sizing: max share of a strategy's equity in ONE position ------
# (low, high, max_fraction) for the AI's stated confidence 1-10
CONFIDENCE_TIERS = [(1, 4, 0.15), (5, 7, 0.35), (8, 10, 0.75)]

# --- Liquidity rules ---------------------------------------------------------
ALLOWED_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "ARCA", "NYSEARCA", "BATS"}  # no OTC
LIQUID_MIN_PRICE = 5.00
LIQUID_MIN_DOLLAR_VOLUME = 20_000_000  # 20-day avg daily $ volume
SMALLCAP_MAX_ADV_FRACTION = 0.01  # an order may be at most 1% of avg daily $ volume
LIMIT_PRICE_BAND = 0.03  # limit price must be within 3% of the current price

# --- Simulated trading costs (paper fills are too clean) --------------------
BASE_SPREAD_PENALTY = 0.0005  # 0.05% minimum per fill
SMALLCAP_PENALTY_MULTIPLIER = 2.0  # small caps pay double the quoted half-spread

# --- Check-ins ---------------------------------------------------------------
# Eastern-time slots in priority order; a strategy at level N uses the first N.
CHECKIN_SLOTS_ET = ["09:45", "15:30", "12:30", "11:00", "14:00"]
CHECKIN_START_LEVEL = 2
CHECKIN_MIN_LEVEL = 1
CHECKIN_MAX_LEVEL = 5
LAST_CHECKIN_ET_MIN = 15 * 60 + 50  # no check-ins start after 3:50pm ET
MAX_ORDERS_PER_DAY = 6  # per strategy

# --- AI models and budget ----------------------------------------------------
TRADER_MODEL = "claude-sonnet-5-5"
REVIEW_MODEL = "claude-opus-5-5"
# USD per million tokens (input, output) - update if pricing changes
MODEL_PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
MONTHLY_TARGET_USD = 5.00  # soft target: throttle weakest strategies when ahead of pace
MONTHLY_HARD_CAP_USD = 20.00  # hard stop for all AI calls in a calendar month
MAX_OUTPUT_TOKENS_TRADER = 2000  # only tokens actually used are billed
MAX_OUTPUT_TOKENS_REVIEW = 6000

# --- Liquid universe for strategies A, B, C (E may also use it) -------------
LIQUID_UNIVERSE = [
    "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU",
    "XLB", "XLRE", "XLC", "SMH", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "TSLA", "AVGO", "AMD", "NFLX", "JPM", "BAC", "WFC", "GS", "V", "MA", "UNH",
    "LLY", "JNJ", "PFE", "MRK", "XOM", "CVX", "WMT", "COST", "HD", "KO", "PEP",
    "MCD", "DIS", "NKE", "BA", "CAT", "INTC", "CRM", "ORCL", "ADBE", "PLTR",
    "UBER", "SBUX", "T", "VZ",
]
