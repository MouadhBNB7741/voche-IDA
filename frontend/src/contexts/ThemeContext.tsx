import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

type Theme = 'light' | 'dark';

export interface ThemeColors {
  primary: string;
  secondary: string;
  accent: string;
}

export interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  colors: ThemeColors;
  font: string;
  updateColor: (key: keyof ThemeColors, value: string) => void;
  updateFont: (font: string) => void;
  resetTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'voce_theme';
const COLORS_STORAGE_KEY = 'voce_theme_colors';
const FONT_STORAGE_KEY = 'voce_theme_font';

const DEFAULT_COLORS: ThemeColors = {
  primary: '142 70% 35%',
  secondary: '170 50% 30%',
  accent: '80 60% 45%',
};

const DEFAULT_FONT = 'poppins';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return (stored as Theme) || 'light';
  });

  const [colors, setColors] = useState<ThemeColors>(() => {
    const stored = localStorage.getItem(COLORS_STORAGE_KEY);
    return stored ? JSON.parse(stored) : DEFAULT_COLORS;
  });

  const [font, setFont] = useState<string>(() => {
    return localStorage.getItem(FONT_STORAGE_KEY) || DEFAULT_FONT;
  });

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(COLORS_STORAGE_KEY, JSON.stringify(colors));
    const root = document.documentElement;
    root.style.setProperty('--primary', colors.primary);
    root.style.setProperty('--secondary', colors.secondary);
    root.style.setProperty('--accent', colors.accent);

    // Also update rings and borders that use primary
    root.style.setProperty('--ring', colors.primary);
  }, [colors]);

  useEffect(() => {
    localStorage.setItem(FONT_STORAGE_KEY, font);
    document.documentElement.style.setProperty('--font-sans', font);

    // Inject dynamic style to override Tailwind's font-sans
    // This ensures it applies everywhere
    const styleId = 'dynamic-font-style';
    let styleTag = document.getElementById(styleId) as HTMLStyleElement;
    if (!styleTag) {
      styleTag = document.createElement('style');
      styleTag.id = styleId;
      document.head.appendChild(styleTag);
    }
    styleTag.innerHTML = `
      body, .font-sans { font-family: '${font}', sans-serif !important; }
    `;
  }, [font]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  const updateColor = (key: keyof ThemeColors, value: string) => {
    setColors(prev => ({ ...prev, [key]: value }));
  };

  const updateFont = (newFont: string) => {
    setFont(newFont);
  };

  const resetTheme = () => {
    setColors(DEFAULT_COLORS);
    setFont(DEFAULT_FONT);
  };

  return (
    <ThemeContext.Provider value={{
      theme,
      toggleTheme,
      colors,
      font,
      updateColor,
      updateFont,
      resetTheme
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}