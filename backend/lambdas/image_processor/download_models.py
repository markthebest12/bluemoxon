"""Pre-download rembg models during Docker build."""
import sys

try:
    from rembg import new_session

    print("Downloading u2net model...")
    new_session("u2net")

    print("Downloading isnet-general-use model...")
    new_session("isnet-general-use")

    print("Models downloaded successfully")
except Exception as e:
    print(f"Error downloading models: {e}")
    sys.exit(1)
