# Enrollment Monitor

A lightweight Python + Playwright browser monitor that watches an authorized enrollment page and sends an instant phone alert when the page changes from an inactive state to a possible active state.

> Built to solve a very specific problem: enrollment windows can open at unpredictable times, authenticated sessions can expire, and desired sections can fill quickly. Instead of manually refreshing a page, the monitor handles the waiting and alerts the user when attention is needed.

## Features

- Checks the target enrollment page every 90 seconds by default
- Uses a persistent Chromium profile for an existing authenticated browser session
- Sends lightweight authenticated heartbeats every 45 seconds by default
- Detects login/session expiration
- Detects a configurable "closed" page marker
- Performs a second confirmation check before triggering an opening alert
- Sends urgent push notifications through [ntfy](https://ntfy.sh/)
- Plays a local Windows alarm
- Saves a screenshot when an opening is confirmed
- Treats server errors and unexpected pages as errors, not as an enrollment opening
- Does not automatically submit enrollment requests or bypass authentication

## How it works

```text
                    ┌────────────────────────┐
                    │ Persistent Chromium    │
                    │ authenticated session  │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Playwright Monitor     │
                    └────────────┬───────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              every 45 sec              every 90 sec
              heartbeat                   page check
                    │                         │
                    ▼                         ▼
              keep session alive       classify page
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                      CLOSED               LOGIN                CHANGED
                         │                    │                    │
                         ▼                    ▼                    ▼
                     wait/check          notify + login       confirm again
                                                                   │
                                                           ┌───────┴───────┐
                                                           ▼               ▼
                                                        CLOSED           CHANGED
                                                                           │
                                                                           ▼
                                                               phone + laptop alarm
                                                               + trigger screenshot
```

## Tech stack

- **Python** - application logic
- **Playwright** - browser automation and persistent session handling
- **Chromium** - visible browser session
- **ntfy** - push notifications
- **python-dotenv** - local configuration through `.env`
- **Windows `winsound`** - local alarm

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/imnxr/enrollment-monitor.git
cd enrollment-monitor
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Configure the monitor

Copy the example environment file:

```bash
copy .env.example .env
```

On macOS/Linux, use:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
TARGET_URL=https://example.com/enrollment
NTFY_TOPIC=your-ntfy-topic-here
CLOSED_MARKER=enrollment is not active
CHECK_INTERVAL=90
HEARTBEAT_INTERVAL=45
```

The `TARGET_URL` and `CLOSED_MARKER` are intentionally configurable so the monitor can be adapted to different portals without changing the Python source.

### 4. Subscribe to ntfy

Install the ntfy app on the phone and subscribe to the same topic configured in `.env`.

Enable notifications, sound/vibration, background operation, and any Android settings required for reliable delivery on the device.

### 5. Start the monitor

```bash
python monitor.py
```

A visible Chromium window will open. If authentication is required, complete it manually. The persistent browser profile will then be reused by later runs unless the profile is removed or the session expires.

### 6. Test notifications and the local alarm

```bash
python monitor.py test
```

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `TARGET_URL` | required | Page to monitor |
| `NTFY_TOPIC` | required | ntfy topic for phone alerts |
| `CLOSED_MARKER` | `enrollment is not active` | Text indicating that enrollment remains closed |
| `CHECK_INTERVAL` | `90` | Seconds between full page checks |
| `HEARTBEAT_INTERVAL` | `45` | Seconds between authenticated session heartbeats |
| `PROFILE_DIR` | `./browser_profile` | Persistent Playwright browser profile |

## Why two intervals?

The monitor separates **session maintenance** from **enrollment detection**.

A lightweight authenticated heartbeat runs every 45 seconds so an inactivity-based session timeout is less likely to occur. The actual enrollment page is checked every 90 seconds, reducing unnecessary page loads while still providing frequent detection.

These values are configurable because different portals can have different session policies and traffic constraints.

## False-positive protection

A server error, unexpected page, or temporary failure is **not** treated as an enrollment opening.

When the configured closed marker disappears, the monitor waits and performs another full check. Only two consecutive `changed` states trigger the urgent alarm.

## Security and privacy

Do not commit:

- `.env`
- browser profiles or cookies
- authentication tokens
- personal student information
- private dashboard screenshots
- private notification topics

The `.gitignore` file excludes the local environment and browser profile by default.

## Responsible use

This project is intended for pages that the user is authorized to access. It does not bypass authentication, defeat access controls, or automatically submit enrollment requests. Users should follow the terms and policies of the service being monitored and avoid excessive request rates.

## Limitations

- A server-side maximum session lifetime cannot be prevented by a client-side heartbeat.
- Microsoft or another identity provider may require reauthentication independently of portal activity.
- Notification delivery ultimately depends on the phone, operating system, network, and notification-service configuration.
- The current local alarm implementation uses Windows `winsound`.

## Project story

This started as a small personal automation problem: repeatedly refreshing an enrollment portal while waiting for registration to open. The final workflow combines browser automation, session awareness, page-state detection, confirmation checks, push notifications, and a local alarm into one focused utility.

## License

MIT License

Copyright (c) 2026 Muhammad Mansoor Ur Rehman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
