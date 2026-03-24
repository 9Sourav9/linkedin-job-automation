"""
Setup script — run once to install dependencies and configure the app.
Usage: python setup.py
"""
import subprocess
import sys
import os
import shutil


def run(cmd, check=True):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print(result.stderr.strip())
    return result.returncode == 0


def main():
    print("=" * 60)
    print("LinkedIn Job Automation — Setup")
    print("=" * 60)

    # 1. Install Python packages
    print("\n[1] Installing Python dependencies...")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 2. Install Playwright browsers
    print("\n[2] Installing Playwright browser (Chromium)...")
    run([sys.executable, "-m", "playwright", "install", "chromium"])

    # 3. Create directories
    print("\n[3] Creating directories...")
    for d in ["outputs", "resumes/tailored", "credentials", "resumes"]:
        os.makedirs(d, exist_ok=True)
        print(f"  Created: {d}/")

    # 4. Create .env from example if not exists
    print("\n[4] Setting up .env file...")
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        shutil.copy(".env.example", ".env")
        print("  Created .env from .env.example")
        print("  ⚠️  Edit .env with your credentials before running!")
    elif os.path.exists(".env"):
        print("  .env already exists — skipping")
    else:
        print("  .env.example not found — please create .env manually")

    print("\n" + "=" * 60)
    print("Setup complete! Next steps:")
    print("=" * 60)
    print("""
1. Edit .env with your credentials:
   - LINKEDIN_EMAIL and LINKEDIN_PASSWORD
   - ANTHROPIC_API_KEY (get from console.anthropic.com)
   - GOOGLE_CREDENTIALS_PATH (see step 2)

2. Set up Google API credentials:
   a. Go to console.cloud.google.com
   b. Create a project → Enable Google Docs API + Google Drive API
   c. Create OAuth 2.0 credentials (Desktop app)
   d. Download JSON → save as credentials/google_credentials.json

3. Place your resume:
   - Save your base resume as: resumes/base_resume.docx
   - Or update BASE_RESUME_PATH in .env

4. Configure job search filters in .env:
   - JOB_KEYWORDS, JOB_LOCATION, JOB_DATE_FILTER, etc.

5. Run the app:
   python main.py                  # Full auto mode
   python main.py --dry-run        # Test without submitting
   python main.py --scrape-only    # Just scrape jobs
""")


if __name__ == "__main__":
    main()
