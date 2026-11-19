export const languages = [
  { code: 'en', name: 'English' },
  { code: 'pt', name: 'Português' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'ar', name: 'العربية' },
];

/**
 * Saved languages may be a code ("en") or, on older profiles, a name ("English").
 */
export function toLanguageCode(value?: string | null): string {
  return languages.find((lang) => lang.code === value || lang.name === value)?.code ?? 'en';
}
