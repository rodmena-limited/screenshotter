import io  # <-- Import this
import os
import shutil
import subprocess
import tempfile
import threading

from flask import Flask, abort, request, send_file
from flask_caching import Cache
from werkzeug.exceptions import HTTPException

# App and Cache Configuration
config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",  # Uses a simple in-memory cache
    "CACHE_DEFAULT_TIMEOUT": 3600,  # Default cache timeout in seconds (1 hour)
}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

# Set a timeout for the Firefox command (in seconds)
FIREFOX_TIMEOUT = 15

# A lock to prevent race conditions with the default 'screenshot.png' filename
firefox_lock = threading.Lock()


from flask import Response


@app.route("/screenshot")
def capture_screenshot() -> Response:
    """
    Public-facing view.
    Fetches screenshot bytes (from cache or by generation)
    and serves them as an image.
    """
    url = request.args.get("url")

    if not url:
        return abort(400, description="Missing 'url' query parameter.")

    if not (url.startswith("http://") or url.startswith("https://")):
        return abort(
            400, description="Invalid URL. Must start with 'http://' or 'https://'."
        )

    try:
        # Call the cached function to get the raw image data
        image_bytes = get_image_bytes(url)

        # Send the bytes from memory using io.BytesIO
        return send_file(io.BytesIO(image_bytes), mimetype="image/png")
    except HTTPException as e:
        # If get_image_bytes raised an abort (HTTPException), re-raise it
        app.logger.warning(f"Handled error for {url}: {e.code} {e.description}")
        return abort(e.code if e.code is not None else 500, description=e.description)
    except Exception as e:
        # Handle other unexpected errors
        app.logger.error(f"Unexpected error in screenshot route for {url}: {e}")
        return abort(500, description="Internal server error handling request.")


@cache.cached(timeout=3600)  # Cache the result of *this* function
def get_image_bytes(url: str) -> bytes:
    """
    Worker function.
    Generates the screenshot and returns the raw bytes.
    The result of this function (the bytes) is cached.
    """
    output_path: str | None = None

    try:
        # 1. Create a unique destination path for Firefox to write to
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            output_path = temp_file.name

        # 2. Acquire lock
        with firefox_lock:
            # 3. Construct command with direct output path
            command = ["firefox", "--headless", "--screenshot", output_path, url]

            # 4. Execute command
            app.logger.info(f"CACHE MISS: Running Firefox for {url} to {output_path}")
            result = subprocess.run(
                command,
                timeout=FIREFOX_TIMEOUT,
                check=True,
                capture_output=True,
                text=True,
            )

            # 5. Check for file creation and size
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                app.logger.error(
                    f"Firefox command ran but produced no file at {output_path}. Stderr: {result.stderr}"
                )
                raise abort(
                    500, description="Firefox ran but failed to produce a screenshot."
                )

        # 6. Read the file bytes into memory
        with open(output_path, "rb") as f:
            image_bytes = f.read()

        return image_bytes  # This (the bytes) is what gets cached

    except subprocess.TimeoutExpired:
        app.logger.warning(f"Firefox command timed out for URL: {url}")
        raise abort(504, description="Screenshot command timed out.")

    except subprocess.CalledProcessError as e:
        app.logger.error(
            f"Firefox command failed with code {e.returncode}. Stderr: {e.stderr}"
        )
        raise abort(
            500, description=f"Firefox failed to take screenshot. Error: {e.stderr}"
        )

    except FileNotFoundError:
        app.logger.error(
            "Firefox executable not found. Make sure it's in your system's PATH."
        )
        raise abort(500, description="Firefox executable not found on server.")

    except Exception as e:
        # Re-raise if it's already an HTTP exception (abort)
        if hasattr(e, "code"):
            raise e
        app.logger.error(f"An unexpected error occurred in worker: {e}")
        raise abort(500, description="An unexpected server error occurred in worker.")

    finally:
        # Clean up the temporary file if it was created
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                app.logger.error(f"Failed to remove temp file {output_path}: {e}")


if __name__ == "__main__":
    # Use 'threaded=True' for the lock to work properly with multiple requests
    # Port set to 11754
    app.run(debug=True, host="0.0.0.0", port=11754, threaded=True)
