from huggingface_hub import HfApi

print("Starting upload...")
api = HfApi()

api.upload_folder(
    folder_path=".",
    repo_id="S8world7/cloud-optimizer-env",
    repo_type="space",
    ignore_patterns=["venv/*", "venv/**/*", "__pycache__/*", "*.pyc", ".git/*", "upload.py"]
)

print("✅ Upload completely successful!")