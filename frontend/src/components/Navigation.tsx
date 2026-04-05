import { NavLink, Link, useNavigate } from "react-router-dom";
import idaLogo from "../assets/ida.webp";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
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
  User as UserIcon,
  BellRing,
  ChevronDown,
  ShieldCheck,
  BellDot
} from "lucide-react";

import { useTheme } from "../contexts/ThemeContext";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
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
  { path: "/resources", label: "Resources", icon: BookOpen },
  { path: "/events", label: "Events", icon: Calendar },
  { path: "/assistant", label: "Ida", icon: MessageCircle }
];

export default function Navigation() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { state } = useData();

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
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
    `flex items-center gap-2.5 px-6 py-2.5 rounded-full text-[11px] font-black uppercase tracking-[0.1em] transition-all duration-500 cursor-pointer
   ${isActive
      ? "bg-primary-color text-primary-foreground shadow-2xl shadow-primary-color/30 scale-105"
      : "text-foreground/70 hover:text-primary-color hover:bg-primary-color/10 hover:scale-105 active:scale-95"
    }`;

  return (
    <header className="flex-shrink-0 flex items-center justify-between px-10 py-3 bg-background/80 backdrop-blur-3xl sticky top-0 z-50 transition-all duration-500 border-0">

      {/* Logo */}
      <Link to="/" className="flex items-center gap-4 active:scale-95 transition-transform group cursor-pointer">
        <div className="relative">
          <div className="absolute inset-0 bg-primary-color/30 rounded-2xl blur-xl group-hover:blur-3xl transition-all opacity-0 group-hover:opacity-100"></div>
          <img
            src={idaLogo}
            alt="Voche Logo"
            className="w-12 h-12 relative z-10 object-contain rounded-2xl shadow-2xl transition-all duration-500 border-0 group-hover:rotate-12"
          />
        </div>

        <div className="hidden lg:block relative">
          <div className="flex items-center gap-2">
            <h1 className="font-black text-xl text-foreground tracking-tighter uppercase italic leading-none">
              voche
            </h1>
            <ShieldCheck size={14} className="text-primary-color opacity-30 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </Link>

      {/* Navigation Links */}
      <nav className="hidden lg:flex items-center gap-2 bg-muted/20 p-1.5 rounded-full border-0 shadow-inner">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={`top-nav-v3-${path}`}
            to={path}
            end={path === "/"}
            className={navLinkClass}
          >
            <Icon className="w-4 h-4 opacity-80" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Right Side Actions */}
      <div className="flex items-center gap-4">

        <div className="hidden md:flex items-center bg-muted/20 p-2 rounded-full border-0 gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="rounded-full w-11 h-11 transition-all duration-700 hover:bg-background shadow-none border-0 cursor-pointer group/theme"
          >
            {theme === "dark" 
              ? <Sun size={20} className="text-yellow-400 group-hover:rotate-180 transition-transform duration-700" /> 
              : <Moon size={20} className="text-primary-color group-hover:-rotate-12 transition-transform duration-700" />
            }
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className={`relative rounded-full w-12 h-12 transition-all duration-700 border-0 cursor-pointer active:scale-90
              ${unreadCount > 0 ? "bg-primary-color text-white shadow-primary-color/40 hover:bg-primary-color/90 shadow-2xl" : "bg-background/40 hover:bg-background shadow-sm"}`}
            onClick={() => navigate('/notifications')}
          >
            {unreadCount > 0 
              ? <BellDot size={22} className="animate-[swing_0.8s_ease-out_infinite]" /> 
              : <BellDot size={20} className="text-foreground/70" />
            }
            {unreadCount > 1 && (
              <span className="absolute -top-1 -right-1 flex h-6 w-6 items-center justify-center">
                 <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-color opacity-75"></span>
                 <div className="relative inline-flex rounded-full h-4 w-4 bg-white text-primary-color text-[9px] font-black items-center justify-center shadow-lg">
                    {unreadCount}
                 </div>
              </span>
            )}
          </Button>
        </div>

        {/* User Profile / Login */}
        {isAuthenticated && user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="flex items-center gap-4 h-12 pl-1 pr-5 rounded-full bg-muted/20 border-0 hover:bg-primary-color/10 transition-all shadow-md group cursor-pointer"
              >
                <Avatar className="h-10 w-10 border-2 border-primary-color/20 shadow-2xl group-hover:scale-105 transition-transform">
                  <AvatarImage src={user.avatar} />
                  <AvatarFallback className="bg-primary text-primary-foreground font-black text-[12px]">
                    {getInitials(user.display_name)}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden xl:block text-left">
                  <p className="text-[11px] font-black truncate max-w-[120px] leading-none opacity-80">{user.display_name?.split(' ')[0]}</p>
                </div>
                <ChevronDown size={14} className="opacity-40 group-hover:opacity-100 group-hover:translate-y-0.5 transition-all" />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-64 rounded-3xl mt-4 shadow-2xl border border-border/10 p-2 bg-background/95 backdrop-blur-3xl animate-in zoom-in-95 duration-200" align="end">
              <DropdownMenuLabel className="p-4 bg-muted/20 rounded-2xl mx-1 mb-2">
                <div className="flex items-center gap-4">
                  <Avatar className="h-12 w-12 border border-primary-color/20">
                     <AvatarImage src={user.avatar} />
                     <AvatarFallback className="bg-primary text-primary-foreground font-black text-xs">
                        {getInitials(user.display_name)}
                     </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col space-y-0.5">
                    <p className="font-bold text-sm tracking-tight">{user.display_name}</p>
                    <Badge variant="secondary" className="w-fit px-2 py-0 h-4 text-[8px] font-black uppercase tracking-wider bg-secondary-color/10 text-secondary-color border-0">
                       {user.user_type}
                    </Badge>
                  </div>
                </div>
              </DropdownMenuLabel>

              <DropdownMenuSeparator className="opacity-10 h-1" />

              <div className="space-y-0.5">
                <DropdownMenuItem
                  onClick={() => navigate(user.user_type === 'hcp' ? "/hcpdashboard" : "/patientdashboard")}
                  className="px-4 py-2.5 rounded-xl focus:bg-primary-color/10 focus:text-primary-color cursor-pointer transition-colors gap-3"
                >
                  <UserIcon className="h-4 w-4 opacity-70" />
                  <span className="font-bold text-xs">Profile</span>
                </DropdownMenuItem>

                <DropdownMenuItem onClick={() => navigate("/notifications")}
                  className="px-4 py-2.5 rounded-xl focus:bg-primary-color/10 focus:text-primary-color cursor-pointer transition-colors gap-3">
                  <div className="relative">
                     <BellRing className="h-4 w-4 opacity-70" />
                  </div>
                  <span className="font-bold text-xs">Notifications</span>
                  {unreadCount > 0 && <Badge variant="destructive" className="ml-auto h-5 px-1.5 min-w-[20px] justify-center text-[10px]">{unreadCount}</Badge>}
                </DropdownMenuItem>
              </div>

                <DropdownMenuSeparator className="opacity-10 h-3" />

                <DropdownMenuItem
                  onClick={handleLogout}
                  className="px-4 py-2.5 rounded-xl text-destructive focus:bg-destructive/10 focus:text-destructive cursor-pointer transition-colors gap-3 mt-1"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="font-bold text-xs">Logout</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              asChild
              className="font-black text-[11px] uppercase tracking-[0.2em] rounded-full h-11 px-8 hover:bg-muted/40 transition-all border-0 shadow-none cursor-pointer"
            >
              <Link to="/login">Sign In</Link>
            </Button>

            <Button
              variant="default"
              asChild
              className="bg-primary-color text-primary-foreground font-black text-[11px] uppercase tracking-[0.2em] rounded-full h-11 px-10 shadow-2xl shadow-primary-color/20 hover:shadow-primary-color/50 hover:-translate-y-1 transition-all border-0 cursor-pointer active:scale-95"
            >
              <Link to="/signup">Join voche</Link>
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
