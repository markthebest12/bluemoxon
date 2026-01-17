"""Pre-download rembg models during Docker build."""
import sys

try:
    from rembg import new_session

    print("Downloading u2net model...")  # noqa: T201
    new_session("u2net")

    print("Downloading isnet-general-use model...")  # noqa: T201
    new_session("isnet-general-use")

    print("Models downloaded successfully")  # noqa: T201
except Exception as e:
    print(f"Error downloading models: {e}")  # noqa: T201
    sys.exit(1)
