import { NavLink, Link, useLocation, useNavigate } from "react-router-dom";

import idaLogo from "../assets/ida.webp";

import { Button } from "./ui/button";
import {
  Home,
  FlaskConical,
  Users,
  BookOpen,
  Calendar,
  MessageCircle,
  Sun,
  Moon,
  LogOut,
  User,
  Bell
} from "lucide-react";

import { useTheme } from "../contexts/ThemeContext";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../hooks/use-toast";
import { useData } from "../contexts/DataContext";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator
} from "../components/ui/dropdownmenu";

import { Avatar, AvatarFallback, AvatarImage } from "../components/ui/avatar";

const navItems = [
  { path: "/", label: "Home", icon: Home },
  { path: "/trials", label: "Trials", icon: FlaskConical },
  { path: "/community", label: "Community", icon: Users },
  { path: "/resourcelibrary", label: "Resources", icon: BookOpen },
  { path: "/eventshub", label: "Events", icon: Calendar },
  { path: "/assistant", label: "Assistant", icon: MessageCircle }
];

export default function Navigation() {

  const location = useLocation();
  const navigate = useNavigate();

  const { isAuthenticated, user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { toast } = useToast();
  const { state } = useData();

  const handleLogout = () => {
    logout();

    toast({
      title: "Logged out",
      description: "You have been successfully logged out."
    });

    navigate("/");
  };

  const getInitials = (name?: string) => {
    return name
      ? name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
      : "U";
  };

  const unreadCount = state.notifications.filter((n) => !n.read).length;

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-2 rounded-full text-sm
     transition-all duration-200
     ${isActive
      ? "bg-primary text-primary-foreground shadow-sm"
      : "text-muted-foreground hover:text-primary hover:bg-primary/10"
    }`;

  return (
    <header className="flex-shrink-0 flex items-center justify-between px-6 py-3 bg-background/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">

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
            <h1 className="font-bold text-xl text-foreground tracking-tight">
              VOCE
            </h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">
              Platform
            </p>
          </div>

        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex items-center gap-1 justify-center">
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
          {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
        </Button>

        {/* User Profile / Login */}
        {isAuthenticated && user ? (
          <DropdownMenu>

            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="relative h-10 w-10 rounded-full ring-2 ring-transparent hover:ring-primary/20 transition-all p-0"
              >
                <Avatar className="h-9 w-9 border border-border">
                  <AvatarImage src={user.avatar} alt={user.name} />
                  <AvatarFallback className="bg-gradient-to-br from-primary to-accent text-primary-foreground font-bold">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-56" align="end" forceMount>

              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user.name}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user.email}
                  </p>
                </div>
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={() => navigate("/profile")}>
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => navigate("/notifications")}>
                <Bell className="mr-2 h-4 w-4" />
                <span>Notifications</span>

                {unreadCount > 0 && (
                  <span className="ml-auto bg-destructive text-destructive-foreground text-[10px] px-1.5 py-0.5 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem
                onClick={handleLogout}
                className="text-red-500 focus:text-red-500 focus:bg-red-50 dark:focus:bg-red-950/20"
              >
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>

            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <>
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="hidden lg:flex hover:bg-primary/10 hover:text-primary transition-all cursor-pointer"
            >
              <Link to="/login">
                Log in
              </Link>
            </Button>

            <Button
              asChild
              size="sm"
              className="gap-2 rounded-full px-5 font-semibold bg-[#08a103] text-white shadow-md hover:bg-[#079702] hover:shadow-lg transition-all duration-200 cursor-pointer"
            >
              <Link to="/signup">
                Sign up
              </Link>
            </Button>
          </>
        )}

      </div>
    </header>
  );
}