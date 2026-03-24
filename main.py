"""
LinkedIn Job Automation — Main Orchestrator
==========================================
1. Scrapes LinkedIn jobs with your configured filters
2. Creates a Google Doc with all job listings
3. For each Easy Apply job:
   a. Fetches the full job description
   b. Uses Claude to tailor your resume
   c. Uploads tailored resume to Google Drive
   d. Auto-applies via LinkedIn Easy Apply
4. Updates the Google Doc with application statuses

Usage:
    python main.py                    # Full auto mode
    python main.py --scrape-only      # Just scrape, no applying
    python main.py --no-apply         # Scrape + create doc, skip applying
    python main.py --dry-run          # Scrape + tailor resumes, no applying
"""
import argparse
import json
import os
import sys
from datetime import datetime
from dataclasses import asdict

# Validate environment before importing modules
def check_env():
    missing = []
    required = ["LINKEDIN_EMAIL", "LINKEDIN_PASSWORD", "ANTHROPIC_API_KEY"]
    for var in required:
        if not os.environ.get(var):
            # Try loading .env
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            if not os.environ.get(var):
                missing.append(var)
    if missing:
        print(f"[Error] Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

check_env()

import config
from modules.linkedin_scraper import LinkedInScraper, JobPosting
from modules.resume_tailor import tailor_resume
from modules.auto_apply import AutoApply
from modules.google_docs import (
    create_jobs_doc,
    upload_resume_to_drive,
    save_jobs_to_json,
)


def parse_args():
    parser = argparse.ArgumentParser(description="LinkedIn Job Automation")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape jobs, no resume/apply")
    parser.add_argument("--no-apply", action="store_true", help="Scrape + doc + resumes, skip applying")
    parser.add_argument("--dry-run", action="store_true", help="No actual form submissions")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--max-jobs", type=int, default=config.MAX_JOBS_TO_APPLY, help="Max jobs to process")
    parser.add_argument("--easy-apply-only", action="store_true", default=True, help="Only apply to Easy Apply jobs")
    return parser.parse_args()


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║         LinkedIn Job Automation — Powered by Claude      ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    args = parse_args()
    print_banner()

    os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
    os.makedirs(config.RESUMES_DIR, exist_ok=True)

    # Validate base resume
    if not args.scrape_only and not os.path.exists(config.BASE_RESUME_PATH):
        print(f"[Error] Base resume not found: {config.BASE_RESUME_PATH}")
        print("Please place your resume DOCX at the path specified in .env (BASE_RESUME_PATH).")
        if not args.scrape_only:
            sys.exit(1)

    print(f"[Config] Keywords   : {', '.join(config.JOB_KEYWORDS)}")
    print(f"[Config] Location   : {config.JOB_LOCATION or 'Any'}")
    print(f"[Config] Date filter: {config.DATE_FILTER_LABELS.get(config.JOB_DATE_FILTER, 'Custom')}")
    print(f"[Config] Max jobs   : {args.max_jobs}")
    print(f"[Config] Mode       : {'Dry run' if args.dry_run else 'Live'}")
    print()

    # ── Step 1: Scrape Jobs ────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Scraping LinkedIn jobs...")
    print("=" * 60)

    jobs: list[JobPosting] = []
    with LinkedInScraper(headless=args.headless) as scraper:
        jobs = scraper.scrape_jobs(max_jobs=args.max_jobs)

        if not jobs:
            print("[Warning] No jobs found. Try adjusting your filters.")
            return

        # ── Step 2: Create Google Doc ──────────────────────────────
        print("\n" + "=" * 60)
        print("STEP 2: Creating Google Doc with job listings...")
        print("=" * 60)

        jobs_as_dicts = [asdict(j) for j in jobs]
        save_jobs_to_json(jobs_as_dicts)

        doc_url = ""
        try:
            doc_url = create_jobs_doc(jobs_as_dicts)
            print(f"[Doc] {doc_url}")
        except Exception as e:
            print(f"[Warning] Google Docs failed: {e}")
            print("[Info] Check that GOOGLE_CREDENTIALS_PATH is set correctly.")

        if args.scrape_only:
            print("\n[Done] Scrape-only mode. Exiting.")
            _print_summary(jobs, doc_url)
            return

        # ── Step 3: Tailor Resumes & Apply ────────────────────────
        print("\n" + "=" * 60)
        print("STEP 3: Tailoring resumes and applying...")
        print("=" * 60)

        auto_applier = AutoApply(scraper.page)
        applied_count = 0
        failed_count = 0

        easy_apply_jobs = [j for j in jobs if j.is_easy_apply] if args.easy_apply_only else jobs

        if not easy_apply_jobs:
            print("[Info] No Easy Apply jobs found in results.")
        else:
            print(f"[Info] {len(easy_apply_jobs)} Easy Apply jobs to process")

        for i, job in enumerate(easy_apply_jobs, 1):
            print(f"\n[{i}/{len(easy_apply_jobs)}] {job.title} @ {job.company}")
            print(f"  URL: {job.job_url}")

            # Tailor resume
            resume_path = ""
            resume_url = ""
            try:
                if job.description:
                    jd = job.description
                else:
                    print("  [JD] Fetching full job description...")
                    jd = scraper.fetch_job_description(job.job_url)
                    job.description = jd

                if jd:
                    resume_path = tailor_resume(
                        job_title=job.title,
                        company=job.company,
                        job_description=jd,
                        job_id=job.job_id,
                    )
                    job.tailored_resume_path = resume_path

                    # Upload to Google Drive
                    if doc_url:
                        try:
                            resume_url = upload_resume_to_drive(
                                resume_path, job.title, job.company
                            )
                        except Exception as e:
                            print(f"  [Drive] Upload warning: {e}")
                else:
                    print("  [Warning] No job description found, using base resume")
                    resume_path = config.BASE_RESUME_PATH

            except Exception as e:
                print(f"  [Resume] Error: {e}")
                resume_path = config.BASE_RESUME_PATH

            if args.no_apply or args.dry_run:
                job.application_status = "dry_run"
                print(f"  [Skip] {'Dry run' if args.dry_run else 'No-apply'} mode — not submitting")
                continue

            # Auto-apply
            if not job.is_easy_apply:
                job.application_status = "skipped"
                print(f"  [Skip] Not Easy Apply — visit manually: {job.job_url}")
                continue

            print(f"  [Apply] Submitting application...")
            success, msg = auto_applier.apply(job, resume_path or config.BASE_RESUME_PATH)

            if success:
                job.application_status = "applied"
                applied_count += 1
                print(f"  [✅] Applied successfully!")
            else:
                job.application_status = "failed"
                job.error_msg = msg
                failed_count += 1
                print(f"  [❌] Failed: {msg}")

        # Save final state to JSON
        save_jobs_to_json([asdict(j) for j in jobs], "outputs/jobs_final.json")

    # ── Summary ────────────────────────────────────────────────────
    _print_summary(jobs, doc_url, applied_count, failed_count)


def _print_summary(jobs, doc_url="", applied=0, failed=0):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total jobs found     : {len(jobs)}")
    easy = sum(1 for j in jobs if j.is_easy_apply)
    print(f"  Easy Apply jobs      : {easy}")
    print(f"  Applications sent    : {applied}")
    print(f"  Failed attempts      : {failed}")
    skipped = sum(1 for j in jobs if j.application_status == "skipped")
    print(f"  Skipped (manual req) : {skipped}")
    if doc_url:
        print(f"\n  Google Doc: {doc_url}")
    print(f"  Local backup: outputs/jobs_final.json")
    print()

    if applied > 0:
        print(f"[🎉] {applied} application(s) submitted successfully!")
    print("Good luck with your job search!")


if __name__ == "__main__":
    main()
