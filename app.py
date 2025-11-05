import io
import os
import shutil
import subprocess
import tempfile
import threading

from flask import Flask, abort, request, send_file
from flask_caching import Cache

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


@app.route("/screenshot")
def capture_screenshot():
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
        # Call the memoized function to get the raw image data
        # The cache key will be based on the 'url' argument
        image_bytes = get_image_bytes(url)

        # Send the bytes from memory using io.BytesIO
        return send_file(io.BytesIO(image_bytes), mimetype="image/png")
    except Exception as e:
        # If get_image_bytes raised an abort (HTTPException), re-raise it
        if hasattr(e, "code"):
            app.logger.warning(f"Handled error for {url}: {e.code} {e.description}")
            return abort(e.code, description=e.description)

        # Handle other unexpected errors
        app.logger.error(f"Unexpected error in screenshot route: {e}")
        return abort(500, description="Internal server error handling request.")


@cache.memoize(timeout=3600)  # <-- CORRECT DECORATOR
def get_image_bytes(url):
    """
    Worker function.
    Generates the screenshot and returns the raw bytes.
    The result of this function is memoized based on the 'url' argument.
    """
    output_path = None
    default_screenshot_file = os.path.join(os.getcwd(), "screenshot.png")

    try:
        # 1. Create a unique destination path
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp:
            output_path = temp.name

        # 2. Acquire lock
        with firefox_lock:
            # 3. Clean up old file
            if os.path.exists(default_screenshot_file):
                os.remove(default_screenshot_file)

            # 4. Construct command
            command = ["firefox", "--headless", "--screenshot", url]  # No filename

            # 5. Execute command
            app.logger.info(f"CACHE MISS: Running Firefox for {url}")
            result = subprocess.run(
                command,
                timeout=FIREFOX_TIMEOUT,
                check=True,
                capture_output=True,
                text=True,
            )

            # 6. Check for file creation
            if (
                not os.path.exists(default_screenshot_file)
                or os.path.getsize(default_screenshot_file) == 0
            ):
                app.logger.error(
                    f"Firefox command ran but produced no file. Stderr: {result.stderr}"
                )
                # Raise an exception that the route can catch
                raise abort(
                    500, description="Firefox ran but failed to produce a screenshot."
                )

            # 7. Move file
            shutil.move(default_screenshot_file, output_path)

        # 8. Read the file bytes into memory
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
        # 9. Clean up all files
        if os.path.exists(default_screenshot_file):
            try:
                os.remove(default_screenshot_file)
            except Exception as e:
                app.logger.error(f"Failed to remove lingering default file: {e}")

        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                app.logger.error(f"Failed to remove temp file {output_path}: {e}")


if __name__ == "__main__":
    # Use 'threaded=True' for the lock to work properly with multiple requests
    # Port set to 11754
    app.run(debug=True, host="0.0.0.0", port=11754, threaded=True)
