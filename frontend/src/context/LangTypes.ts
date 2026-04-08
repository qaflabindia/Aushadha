export interface AppLanguage {
  code: string; // ISO 639-1 (e.g., 'en', 'hi', 'ta')
  speechCode: string; // BCP 47 for Web Speech API (e.g., 'en-US', 'hi-IN')
  name: string; // Display name in that language
  nameEn: string; // Display name in English
}

export const SUPPORTED_LANGUAGES: AppLanguage[] = [
  { code: 'en', speechCode: 'en-US', name: 'English', nameEn: 'English' },
  { code: 'hi', speechCode: 'hi-IN', name: 'हिन्दी', nameEn: 'Hindi' },
  { code: 'ta', speechCode: 'ta-IN', name: 'தமிழ்', nameEn: 'Tamil' },
  { code: 'te', speechCode: 'te-IN', name: 'తెలుగు', nameEn: 'Telugu' },
  { code: 'bn', speechCode: 'bn-IN', name: 'বাংলা', nameEn: 'Bengali' },
  { code: 'mr', speechCode: 'mr-IN', name: 'मराठी', nameEn: 'Marathi' },
  { code: 'kn', speechCode: 'kn-IN', name: 'ಕನ್ನಡ', nameEn: 'Kannada' },
  { code: 'ml', speechCode: 'ml-IN', name: 'മലയാളം', nameEn: 'Malayalam' },
  { code: 'gu', speechCode: 'gu-IN', name: 'ગુજરાતી', nameEn: 'Gujarati' },
  { code: 'pa', speechCode: 'pa-IN', name: 'ਪੰਜਾਬੀ', nameEn: 'Punjabi' },
  { code: 'or', speechCode: 'or-IN', name: 'ଓଡ଼ିଆ', nameEn: 'Odia' },
];
