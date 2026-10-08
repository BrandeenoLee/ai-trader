"""Surface errors as GitHub Actions annotations so they show on the run page and via the API."""
import os
import sys
import traceback


def run_reported(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            last = [ln.strip() for ln in tb.strip().splitlines()][-6:]
            msg = f"{type(e).__name__}: {e}"[:900].replace("\n", " ")
            where = " | ".join(last[:-1])[:900]
            print(f"::error title=Bot error::{msg}")
            print(f"::error title=Where::{where}")
        sys.exit(1)
