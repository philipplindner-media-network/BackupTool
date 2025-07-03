import os
import json
import logging

# Konfigurieren Sie das Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TranslationManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        # Der Ordner 'translations' sollte sich im selben Verzeichnis wie die Skripte befinden
        self.translation_dir = os.path.join(os.path.dirname(__file__), "lang")
        self.translations = {}
        self.current_language_code = self.config_manager.get_setting('language', 'en')
        self.set_language(self.current_language_code)
        logging.info(f"TranslationManager initialized. Current language: {self.current_language_code}")

    def set_language(self, lang_code):
        lang_file = os.path.join(self.translation_dir, f"{lang_code}.json")
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_language_code = lang_code
            logging.info(f"Loaded translations for language: {lang_code}")
        except FileNotFoundError:
            logging.warning(f"Translation file not found for {lang_code} at {lang_file}. Falling back to default (en).")
            # Wenn die angeforderte Sprache nicht gefunden wird, versuchen Sie, Englisch zu laden
            if lang_code != 'en':
                self.set_language('en')
            else:
                self.translations = {} # Leere Übersetzungen, wenn selbst 'en' nicht gefunden wird
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from translation file {lang_file}: {e}")
            self.translations = {} # Leere Übersetzungen bei Fehler
        except Exception as e:
            logging.error(f"An unexpected error occurred loading translations for {lang_code}: {e}")
            self.translations = {} # Leere Übersetzungen bei Fehler

    def get_translation(self, key):
        """Gibt die Übersetzung für einen gegebenen Schlüssel zurück. Wenn nicht gefunden, gibt es den Schlüssel selbst zurück."""
        return self.translations.get(key, key)

    def get_available_languages(self):
        """Scannt das Übersetzungsverzeichnis und gibt eine Zuordnung von Sprachcode zu Anzeigename zurück."""
        available_languages = {}
        if os.path.exists(self.translation_dir):
            for filename in os.listdir(self.translation_dir):
                if filename.endswith(".json"):
                    lang_code = filename.replace(".json", "")
                    # Versuchen Sie, den Anzeigenamen aus der JSON-Datei selbst zu lesen,
                    # oder verwenden Sie einen Standardnamen
                    display_name = lang_code # Standardwert
                    try:
                        with open(os.path.join(self.translation_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "language_display_name" in data:
                                display_name = data["language_display_name"]
                    except (IOError, json.JSONDecodeError):
                        logging.warning(f"Could not read display name from {filename}. Using '{lang_code}'.")
                        # Fallback zu bekannten Namen, wenn die Datei nicht gelesen werden kann
                        display_name = {
                            'en': 'English',
                            'de': 'Deutsch'
                        }.get(lang_code, lang_code)
                    available_languages[lang_code] = display_name
        else:
            logging.warning(f"Translation directory not found: {self.translation_dir}")
        return available_languages

    def get_language_display_name(self, lang_code):
        """Helper to get a readable name for a language code, for UI display."""
        return self.get_available_languages().get(lang_code, lang_code)
