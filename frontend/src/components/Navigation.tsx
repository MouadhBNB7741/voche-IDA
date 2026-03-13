import { NavLink, Link } from "react-router-dom";
import idaLogo from '../assets/ida.webp';
import { Button } from "./ui/button";
import { Home, FlaskConical, Users, BookOpen, Calendar, MessageCircle, Sun, Moon } from "lucide-react";
import { useTheme } from '../contexts/ThemeContext';

const navItems = [
  { path: "/", label: "Home", icon: Home },
  { path: "/trials", label: "Trials", icon: FlaskConical },
  { path: "/community", label: "Community", icon: Users },
  { path: "/resourcelibrary", label: "Resources", icon: BookOpen },
  { path: "/eventshub", label: "Events", icon: Calendar },
  { path: "/assistant", label: "Assistant", icon: MessageCircle }
];

export default function Navigation() {

  const { theme, toggleTheme } = useTheme();

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-2 rounded-full text-sm transition-all duration-200
    ${isActive
      ? "bg-primary/10 text-primary"
      : "text-muted-foreground hover:text-foreground hover:bg-muted"
    }`;

  return (

    <header className="flex items-center justify-between px-6 py-3 bg-background/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">

      {/* Logo */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">

          <div className="w-9 h-9 flex items-center justify-center">
            <img
              src={idaLogo}
              alt="VOCE Logo"
              className="w-9 h-9 object-contain rounded-xl shadow-sm"
            />
          </div>

          <div>
            <h1 className="font-bold text-lg text-foreground">
              VOCE
            </h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">
              Platform
            </p>
          </div>

        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex items-center gap-1">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={navLinkClass}
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Right Side Actions */}
      <div className="flex items-center gap-2">

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="rounded-full hover:bg-primary/10 hover:text-primary transition-all duration-300"
        >
          {theme === 'dark'
            ? <Sun size={20} />
            : <Moon size={20} />
          }
        </Button>

        {/* Login */}
        <Button
          variant="ghost"
          size="sm"
          asChild
          className="hidden lg:flex hover:bg-muted"
        >
          <Link to="/login">
            Log in
          </Link>
        </Button>

        {/* Sign Up CTA */}
        <Button
          asChild
          size="sm"
          className="gap-2 rounded-full px-5 font-semibold bg-[#08a103] text-white shadow-md hover:bg-[#079702] hover:shadow-lg transition-all duration-200"
        >
          <Link to="/signup">
            Sign up
          </Link>
        </Button>

      </div>

    </header>

  );
}