import re

from app.utils.response import success_response, error_response


class SettingsService:
    BRANDING_KEY = "branding"
    DEFAULT_BRANDING = {
        "brand_name": "Q-Home",
        "logo_url": "images/logo.png",
        "accent_color": "#4caf57",
    }

    def __init__(self, settings_repository, log_repository):
        self.settings_repository = settings_repository
        self.log_repository = log_repository

    def get_branding(self):
        try:
            return success_response(self._get_branding_value(), "Branding settings retrieved")
        except Exception as exc:
            self.log_repository.error(f"Error retrieving branding settings: {exc}")
            return error_response("Failed to retrieve branding settings", 500)

    def update_branding(self, data):
        try:
            current = self._get_branding_value()
            next_value = {
                "brand_name": str(data.get("brand_name", current["brand_name"])).strip(),
                "logo_url": str(data.get("logo_url", current["logo_url"])).strip(),
                "accent_color": str(data.get("accent_color", current["accent_color"])).strip(),
            }

            validation_error = self._validate_branding(next_value)
            if validation_error:
                return validation_error

            self.settings_repository.upsert_setting(self.BRANDING_KEY, next_value)
            self.log_repository.info("Branding settings updated")
            return success_response(next_value, "Branding settings updated")
        except Exception as exc:
            self.log_repository.error(f"Error updating branding settings: {exc}")
            return error_response("Failed to update branding settings", 500)

    def _get_branding_value(self):
        stored = self.settings_repository.get_setting(self.BRANDING_KEY)
        value = stored.get("value", {}) if stored else {}
        return {
            **self.DEFAULT_BRANDING,
            **{key: value for key, value in value.items() if value not in (None, "")},
        }

    def _validate_branding(self, value):
        if not value["brand_name"]:
            return error_response("Brand name is required", 400)

        if len(value["brand_name"]) > 80:
            return error_response("Brand name must be 80 characters or less", 400)

        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value["accent_color"]):
            return error_response("Accent color must be a hex color like #4caf57", 400)

        logo_url = value["logo_url"]
        if logo_url and not (
            logo_url.startswith("images/")
            or logo_url.startswith("data:image/")
            or logo_url.startswith("http://")
            or logo_url.startswith("https://")
        ):
            return error_response("Logo must be an image path, image URL, or uploaded image data", 400)

        if len(logo_url) > 750000:
            return error_response("Logo image is too large", 400)

        return None
