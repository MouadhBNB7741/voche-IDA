import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'sonner'
import { queryClient } from './lib/reactQuery'
import { AuthProvider } from './contexts/AuthContext'
import { DataProvider } from './contexts/DataContext'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import { SettingsProvider } from './contexts/SettingsContext'
import './index.css'
import App from './App.tsx'

function VocheToaster() {
  const { theme } = useTheme();
  return (
    <Toaster 
      position="bottom-right" 
      richColors 
      expand={true}
      duration={3000}
      visibleToasts={4}
      gap={12}
      theme={theme as 'light' | 'dark' | 'system'}
      toastOptions={{
        className: 'voche-toast-premium',
      }}
    />
  );
}

createRoot(document.getElementById('root')!).render(
<<<<<<< HEAD
    <App />
=======
  <QueryClientProvider client={queryClient}>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ThemeProvider>
        <SettingsProvider>
          <DataProvider>
            <AuthProvider>
              <App />
              <VocheToaster />
            </AuthProvider>
          </DataProvider>
        </SettingsProvider>
      </ThemeProvider>
    </BrowserRouter>
  </QueryClientProvider>
>>>>>>> origin/main
)
