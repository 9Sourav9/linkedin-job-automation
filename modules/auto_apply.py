"""
LinkedIn Easy Apply automation.
Handles multi-step application forms and resume upload.
"""
import os
import time
import random
from typing import Optional
from playwright.sync_api import Page
import config
from modules.linkedin_scraper import JobPosting


class AutoApply:
    def __init__(self, page: Page):
        self.page = page

    def _human_delay(self, min_ms: int = 400, max_ms: int = 1200):
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    def _type_human(self, locator, text: str):
        locator.click()
        self._human_delay(100, 300)
        locator.fill("")  # Clear first
        for char in text:
            locator.type(char, delay=random.randint(40, 120))

    def apply(self, job: JobPosting, resume_path: str) -> tuple[bool, str]:
        """
        Attempt Easy Apply for a job.
        Returns (success, error_message).
        """
        if not job.is_easy_apply:
            return False, "Not an Easy Apply job"

        try:
            # Navigate to job
            self.page.goto(job.job_url, wait_until="networkidle")
            self._human_delay(2000, 3000)

            # Click Easy Apply button
            apply_btn = self.page.locator(".jobs-apply-button").first
            if apply_btn.count() == 0:
                return False, "Easy Apply button not found"

            apply_btn.click()
            self._human_delay(2000, 3000)

            # Handle the application modal
            success, msg = self._handle_application_modal(resume_path)
            return success, msg

        except Exception as e:
            return False, str(e)

    def _handle_application_modal(self, resume_path: str) -> tuple[bool, str]:
        """Handle multi-step Easy Apply modal."""
        max_steps = 10
        step = 0

        while step < max_steps:
            self._human_delay(1000, 2000)

            # Check if modal is still open
            modal = self.page.locator(".jobs-easy-apply-modal").first
            if modal.count() == 0:
                # Check if application was submitted
                success_banner = self.page.locator(".artdeco-inline-feedback--success").first
                if success_banner.count() > 0:
                    return True, "Application submitted successfully"
                return False, "Modal closed unexpectedly"

            # Fill current step
            self._fill_current_step(resume_path)
            self._human_delay(500, 1000)

            # Check for Submit button
            submit_btn = self.page.locator('button[aria-label*="Submit application"]').first
            if submit_btn.count() > 0 and submit_btn.is_enabled():
                submit_btn.click()
                self._human_delay(3000, 5000)

                # Verify submission
                success = self.page.locator(".jobs-easy-apply-modal__post-apply-modal").count() > 0
                if success:
                    # Close modal
                    close_btn = self.page.locator('button[aria-label="Dismiss"]').first
                    if close_btn.count() > 0:
                        close_btn.click()
                    return True, "Application submitted"
                return False, "Submit clicked but confirmation not found"

            # Look for Next button
            next_btn = self.page.locator('button[aria-label="Continue to next step"]').first
            if next_btn.count() == 0:
                next_btn = self.page.locator('button[aria-label="Review your application"]').first
            if next_btn.count() == 0:
                next_btn = self.page.locator(".jobs-easy-apply-modal__next-button").first

            if next_btn.count() > 0 and next_btn.is_enabled():
                next_btn.click()
                step += 1
                continue

            # Check for error messages
            error = self.page.locator(".artdeco-inline-feedback--error").first
            if error.count() > 0:
                error_text = error.inner_text().strip()
                return False, f"Form error: {error_text}"

            break

        return False, f"Max steps ({max_steps}) reached without completion"

    def _fill_current_step(self, resume_path: str):
        """Fill in form fields for the current step."""
        # Phone number
        self._fill_field_if_empty('input[id*="phoneNumber"]', config.YOUR_PHONE)
        self._fill_field_if_empty('input[name*="phone"]', config.YOUR_PHONE)

        # Email (usually pre-filled but ensure it's there)
        self._fill_field_if_empty('input[id*="email"]', config.YOUR_EMAIL)

        # City/location
        self._fill_field_if_empty('input[id*="city"]', config.YOUR_LOCATION.split(",")[0].strip())

        # Upload resume if file input present
        self._upload_resume(resume_path)

        # Handle "Yes/No" questions (default to "Yes" for standard questions)
        self._handle_radio_buttons()

        # Handle dropdowns
        self._handle_dropdowns()

        # Handle text area questions
        self._handle_text_areas()

    def _fill_field_if_empty(self, selector: str, value: str):
        """Fill a text field only if it's empty."""
        if not value:
            return
        try:
            inputs = self.page.locator(selector).all()
            for inp in inputs:
                if inp.is_visible() and not inp.input_value():
                    self._type_human(inp, value)
        except Exception:
            pass

    def _upload_resume(self, resume_path: str):
        """Upload the tailored resume."""
        try:
            # Find file upload input
            file_inputs = self.page.locator('input[type="file"]').all()
            for file_input in file_inputs:
                if file_input.is_visible() or True:  # May be hidden
                    try:
                        file_input.set_input_files(resume_path)
                        self._human_delay(2000, 3000)
                        print(f"    [Apply] Resume uploaded: {os.path.basename(resume_path)}")
                        break
                    except Exception:
                        pass
        except Exception as e:
            print(f"    [Apply] Resume upload warning: {e}")

    def _handle_radio_buttons(self):
        """Handle Yes/No radio questions — default to first option (usually Yes)."""
        try:
            # Find all radio groups
            radio_groups = self.page.locator('.jobs-easy-apply-form-element').all()
            for group in radio_groups:
                radios = group.locator('input[type="radio"]').all()
                if radios and not any(r.is_checked() for r in radios):
                    # Click first option
                    if radios[0].is_visible():
                        radios[0].click()
                        self._human_delay(200, 400)
        except Exception:
            pass

    def _handle_dropdowns(self):
        """Handle select dropdowns — pick first non-empty option."""
        try:
            selects = self.page.locator('select.fb-dropdown__select').all()
            for sel in selects:
                if sel.is_visible():
                    current = sel.evaluate("el => el.value")
                    if not current or current == "":
                        options = sel.evaluate("el => [...el.options].map(o => o.value)")
                        non_empty = [o for o in options if o]
                        if non_empty:
                            sel.select_option(non_empty[0])
                            self._human_delay(200, 400)
        except Exception:
            pass

    def _handle_text_areas(self):
        """Handle open text fields — fill with reasonable defaults."""
        try:
            textareas = self.page.locator('textarea.artdeco-text-input--input').all()
            for ta in textareas:
                if ta.is_visible() and not ta.input_value():
                    # Get label for context
                    label = ""
                    try:
                        label_id = ta.get_attribute("id") or ""
                        label_el = self.page.locator(f'label[for="{label_id}"]').first
                        if label_el.count() > 0:
                            label = label_el.inner_text().lower()
                    except Exception:
                        pass

                    if "cover letter" in label:
                        # Skip cover letter — usually better to leave blank than auto-fill
                        pass
                    elif "years" in label or "experience" in label:
                        ta.fill("3")
                    elif "salary" in label or "compensation" in label:
                        ta.fill("Negotiable")
                    elif "linkedin" in label or "profile" in label:
                        ta.fill(config.YOUR_LINKEDIN)
                    elif "website" in label or "portfolio" in label:
                        ta.fill(config.YOUR_LINKEDIN)
        except Exception:
            pass
