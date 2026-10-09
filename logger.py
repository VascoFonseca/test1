import time

import state
from config import logger


def log(message, level="info"):
    message = str(message)

    if level == "debug":
        logger.debug(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.info(message)

    print(f"[{time.strftime('%H:%M:%S')}] {message}")

    try:
        app = state.ui

        if app is not None and app.root is not None:
            app.root.after(
                0,
                lambda m=message, a=app: a.append_log(m)
            )
        else:
            print("GUI LOG WARNING: state.ui is not initialized")

    except Exception as e:
        print(f"GUI LOG ERROR: {e!r}")

def update_status(message):
    try:
        if state.ui is not None and state.ui.root is not None:
            state.ui.root.after(
                0,
                lambda m=message: state.ui.status_label.config(
                    text=f"Status: {m}"
                )
            )
    except Exception as e:
        log(f"Status update error: {e!r}", "error")


def set_state(new_state, reason=""):
    old_state = state.state
    state.state = new_state

    message = f"STATE: {old_state} -> {new_state}"
    if reason:
        message += f" | {reason}"

    log(message)