import os
import sys
import time
from datetime import datetime

import requests
import winsound
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


load_dotenv()

TARGET_URL = os.getenv("TARGET_URL", "").strip()
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()
CLOSED_MARKER = os.getenv("CLOSED_MARKER", "enrollment is not active").strip().lower()
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "90"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "45"))
PROFILE_DIR = os.getenv(
    "PROFILE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_profile"),
)

LOGIN_URL_MARKERS = (
    "login.microsoftonline.com",
    "/web/login",
)

LOGIN_TEXT_MARKERS = (
    "sign in to your account",
    "pick an account",
    "enter password",
    "sign in with microsoft",
)

ERROR_MARKERS = (
    "internal server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "too many requests",
    "temporarily unavailable",
)


def validate_config():
    missing = []
    if not TARGET_URL:
        missing.append("TARGET_URL")
    if not NTFY_TOPIC:
        missing.append("NTFY_TOPIC")
    if missing:
        raise RuntimeError(
            "Missing configuration: " + ", ".join(missing) +
            ". Copy .env.example to .env and fill in the values."
        )


def send_notification(title, message, priority="5"):
    try:
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": str(priority),
                "Tags": "rotating_light",
                "Click": TARGET_URL,
            },
            timeout=20,
        )
        response.raise_for_status()
        print(f"Phone notification sent (HTTP {response.status_code})")
    except Exception as exc:
        print(f"PHONE NOTIFICATION ERROR: {exc}")


def laptop_alarm(kind="open"):
    try:
        if kind == "open":
            for _ in range(10):
                winsound.Beep(1500, 650)
                winsound.Beep(1000, 350)
        else:
            for _ in range(4):
                winsound.Beep(900, 450)
                time.sleep(0.2)
    except Exception as exc:
        print(f"Laptop sound error: {exc}")


def get_body_text(page):
    try:
        return page.locator("body").inner_text(timeout=10000).lower()
    except Exception:
        return ""


def is_login_page(page, text=None):
    text = get_body_text(page) if text is None else text
    url = page.url.lower()

    return (
        any(marker in url for marker in LOGIN_URL_MARKERS)
        or any(marker in text for marker in LOGIN_TEXT_MARKERS)
    )


def classify_page(page, http_status=None):
    text = get_body_text(page)
    url = page.url.lower()

    if is_login_page(page, text):
        return "login"

    if http_status in (401, 403):
        return "login"

    if CLOSED_MARKER and CLOSED_MARKER in text:
        return "closed"

    if http_status is not None and http_status >= 500:
        return "error"

    if any(marker in text for marker in ERROR_MARKERS):
        return "error"

    if http_status == 404:
        return "unexpected"

    if len(text.strip()) < 50:
        return "unexpected"

    return "changed"


def load_enrollment_page(page):
    try:
        response = page.goto(
            TARGET_URL,
            wait_until="domcontentloaded",
            timeout=120000,
        )
        time.sleep(5)
        status = response.status if response else None
        return classify_page(page, status), status
    except PlaywrightTimeoutError:
        print("Portal load timed out.")
        return "error", None
    except Exception as exc:
        print(f"Portal load error: {exc}")
        return "error", None


def keep_session_alive(page):
    """Make a lightweight authenticated request using the browser context's cookies."""
    try:
        response = page.request.get(TARGET_URL, timeout=30000)
        status = response.status
        response.dispose()
        print(f"Session heartbeat sent (HTTP {status})")
        return status
    except Exception as exc:
        print(f"Session heartbeat failed: {exc}")
        return None


def wait_for_login(page, initial=False):
    if initial:
        print("LOGIN REQUIRED.")
        print("Complete authentication manually in the Chromium window.")
        print("The monitor will wait for you.")
    else:
        print("SESSION EXPIRED.")
        send_notification(
            "SESSION EXPIRED",
            "Your portal session expired. Sign in again so monitoring can continue.",
            "5",
        )
        laptop_alarm("session")

    while True:
        time.sleep(5)
        text = get_body_text(page)
        if not is_login_page(page, text):
            print("Login page has disappeared. Checking the portal again...")
            return


def enrollment_open_alarm(page):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(
        screenshot_dir,
        f"enrollment-trigger-{timestamp}.png",
    )

    try:
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Trigger screenshot saved: {screenshot_path}")
    except Exception as exc:
        print(f"Could not save screenshot: {exc}")

    print("\n" + "!" * 70)
    print("ENROLLMENT PAGE HAS CHANGED")
    print("ENROLLMENT IS VERY LIKELY ACTIVE")
    print("GET TO THE PORTAL NOW")
    print("!" * 70 + "\n")

    send_notification(
        "ENROLLMENT OPEN",
        "Enrollment appears to be active. Get to the portal now!",
        "5",
    )
    time.sleep(4)
    send_notification(
        "ENROLLMENT OPEN",
        "Wake up. Self-enrollment appears to be active.",
        "5",
    )
    time.sleep(4)
    send_notification(
        "ENROLLMENT OPEN",
        "Open the enrollment portal now.",
        "5",
    )

    laptop_alarm("open")

    print("Browser will remain open. Press CTRL+C after you are awake.")

    minutes = 0
    while True:
        time.sleep(60)
        minutes += 1
        laptop_alarm("open")
        if minutes % 5 == 0:
            send_notification(
                "ENROLLMENT OPEN",
                "Enrollment alert is still active. Check the portal now.",
                "5",
            )


def test_alarm():
    validate_config()
    send_notification(
        "ENROLLMENT MONITOR TEST",
        "Test alert. Your phone notification setup is working.",
        "5",
    )
    laptop_alarm("open")
    print("Test notification sent.")


def run_monitor():
    validate_config()
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("=" * 70)
    print("ENROLLMENT MONITOR")
    print("=" * 70)
    print(f"Target: {TARGET_URL}")
    print(f"Enrollment check: every {CHECK_INTERVAL} seconds")
    print(f"Session heartbeat: every {HEARTBEAT_INTERVAL} seconds")
    print()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
        )

        page = context.pages[0] if context.pages else context.new_page()
        state, status = load_enrollment_page(page)

        if state == "login":
            wait_for_login(page, initial=True)
            state, status = load_enrollment_page(page)

        next_check = time.monotonic() + CHECK_INTERVAL
        next_heartbeat = time.monotonic() + HEARTBEAT_INTERVAL
        consecutive_errors = 0
        warned_about_errors = False

        while True:
            try:
                now = time.monotonic()

                if now >= next_heartbeat:
                    heartbeat_status = keep_session_alive(page)
                    next_heartbeat = now + HEARTBEAT_INTERVAL

                    if heartbeat_status in (401, 403):
                        state = "login"

                if now < next_check:
                    time.sleep(min(1, next_check - now))
                    continue

                current_time = datetime.now().strftime("%I:%M:%S %p")
                print(f"\n[{current_time}] Checking enrollment...")

                state, status = load_enrollment_page(page)
                next_check = time.monotonic() + CHECK_INTERVAL

                if state == "closed":
                    consecutive_errors = 0
                    warned_about_errors = False
                    print("STATUS: Enrollment CLOSED")
                    continue

                if state == "login":
                    wait_for_login(page)
                    state, status = load_enrollment_page(page)
                    next_check = time.monotonic() + CHECK_INTERVAL
                    continue

                if state == "changed":
                    print("Possible enrollment opening detected. Confirming...")
                    time.sleep(8)
                    confirm_state, confirm_status = load_enrollment_page(page)

                    if confirm_state == "changed":
                        enrollment_open_alarm(page)
                        return

                    print("False trigger or temporary page issue. Continuing monitor.")
                    state, status = confirm_state, confirm_status
                    continue

                if state in ("error", "unexpected"):
                    consecutive_errors += 1
                    print(f"STATUS: {state.upper()} - not treating as OPEN")

                    if consecutive_errors >= 3 and not warned_about_errors:
                        send_notification(
                            "MONITOR WARNING",
                            "The portal has failed several checks. The server may be overloaded.",
                            "4",
                        )
                        warned_about_errors = True
                    continue

            except KeyboardInterrupt:
                print("\nMonitor stopped by user.")
                break

            except Exception as exc:
                print(f"Unexpected monitor error: {exc}")
                time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
        test_alarm()
    else:
        run_monitor()
