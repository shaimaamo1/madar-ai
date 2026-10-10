import { Globe2 } from "lucide-react";
import { Language, tr, useLanguage } from "./i18n";

export function LanguageSelector() {
  const { lang, setLanguage } = useLanguage();
  return (
    <label className="language-selector">
      <Globe2 size={16} aria-hidden="true" />
      <select
        aria-label={tr("Language")}
        value={lang}
        onChange={(event) => setLanguage(event.target.value as Language)}
      >
        <option value="ar" lang="ar">
          العربية (AR)
        </option>
        <option value="en" lang="en">
          English (EN)
        </option>
      </select>
    </label>
  );
}
