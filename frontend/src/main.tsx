import './index.css';

async function bootstrap() {
  await document.fonts.load("14px 'Noto Sans Tamil'");
  
  const { SKIP_AUTH } = await import('./utils/Constants.ts');
  const { default: App } = await import('./App.tsx');
  const { default: Auth0ProviderWithHistory } = await import('./components/Auth/Auth.tsx');
  const { BrowserRouter } = await import('react-router-dom');
  const { createRoot } = await import('react-dom/client');

  createRoot(document.getElementById('root')!).render(
    <BrowserRouter>
      {SKIP_AUTH ? (
        <App />
      ) : (
        <Auth0ProviderWithHistory>
          <App />
        </Auth0ProviderWithHistory>
      )}
    </BrowserRouter>
  );
}

bootstrap();
