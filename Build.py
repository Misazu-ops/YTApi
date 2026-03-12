import os
import shutil
import subprocess

def clean_dist():
    for folder in ["dist", "build", "AbhiCalls.egg-info"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def build_package():
    subprocess.run(["python3", "-m", "build"], check=True)

def upload_package(token):
    subprocess.run([
        "twine",
        "upload",
        "dist/*",
        "-u",
        "__token__",
        "-p",
        token
    ], check=True)

if __name__ == "__main__":
    print("🔑 Enter PyPI Token:")
    token = input("Token: ").strip()

    print("📦 Cleaning old builds...")
    clean_dist()

    print("⚙️ Building package...")
    build_package()

    print("🚀 Uploading to PyPI...")
    upload_package(token)

    print("✅ Package uploaded successfully!")
