import './index.css';

async function bootstrap() {
  await document.fonts.load("14px 'Noto Sans Tamil'");

  const { SKIP_AUTH } = await import('./utils/Constants.ts');
  const { default: App } = await import('./App.tsx');
  const { GoogleAuthProvider } = await import('./context/GoogleAuthContext.tsx');
  const { GoogleOAuthProvider } = await import('@react-oauth/google');
  const { BrowserRouter } = await import('react-router-dom');
  const { createRoot } = await import('react-dom/client');
  const { PatientProvider } = await import('./context/PatientContext.tsx');
  const { LanguageProvider } = await import('./context/LanguageContext.tsx');
  const { default: TranslationProvider } = await import('./context/TranslationContext.tsx');
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

  const inner = SKIP_AUTH ? (
    <PatientProvider><App /></PatientProvider>
  ) : (
    <GoogleOAuthProvider clientId={googleClientId}>
      <GoogleAuthProvider>
        <PatientProvider><App /></PatientProvider>
      </GoogleAuthProvider>
    </GoogleOAuthProvider>
  );

  createRoot(document.getElementById('root')!).render(
    <BrowserRouter>
      <LanguageProvider>
        <TranslationProvider>
          {inner}
        </TranslationProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

bootstrap();

