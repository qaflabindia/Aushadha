import './index.css';

async function bootstrap() {
  await document.fonts.load("14px 'Noto Sans Tamil'");

  const { SKIP_AUTH } = await import('./utils/Constants.ts');
  const { default: App } = await import('./App.tsx');
  const { GoogleAuthProvider } = await import('./context/GoogleAuthContext.tsx');
  const { GoogleOAuthProvider } = await import('@react-oauth/google');
  const { BrowserRouter } = await import('react-router-dom');
  const { createRoot } = await import('react-dom/client');

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

  createRoot(document.getElementById('root')!).render(
    <BrowserRouter>
      {SKIP_AUTH ? (
        <App />
      ) : (
        <GoogleOAuthProvider clientId={googleClientId}>
          <GoogleAuthProvider>
            <App />
          </GoogleAuthProvider>
        </GoogleOAuthProvider>
      )}
    </BrowserRouter>
  );
}

bootstrap();
