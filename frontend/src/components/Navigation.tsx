import { NavLink, Link } from "react-router-dom";
import idaLogo from '../assets/ida.webp';
import { Button } from "./ui/button";
import { Home,FlaskConical, Users, BookOpen, Calendar, Bot } from "lucide-react";

const navItems = [
    { path: "/", label: "Home", icon: Home},
    { path: "/trialsearch", label: "Trials", icon: FlaskConical},
    { path: "/community", label: "Community", icon: Users },
    { path: "/resourcelibrary", label: "Resources", icon: BookOpen },
    { path: "/eventshub", label: "Events", icon: Calendar},
    { path: "/assistant", label: "Assistant", icon: Bot}
];


export default function Navigation() {
    const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `voce-nav-item ${isActive ? "active" : ""}`;

      return (

        <header className="hidden md:flex items-center justify-between px-6 py-4 bg-card border-b border-border">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 voce-gradient-primary rounded-lg flex items-center justify-center">
              <img src={idaLogo} alt="VOCE Logo" className="w-9 h-9 object-contain rounded-xl shadow-lg" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-foreground">
                VOCE
              </h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">Platform</p>
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === "/"}
            className={navLinkClass}
          >
            <span className="flex items-center gap-2 text-sm font-medium">
              <Icon className="w-4 h-4" />
              {label}
            </span>
          </NavLink>
        ))}
        </nav>

       <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" asChild className="hidden lg:flex hover:bg-primary/5 hover:text-primary">
                <Link to="/login">
                  Log in
                </Link>
              </Button>
              <Button asChild size="sm" className="gap-2 shadow-md rounded-full px-5 font-semibold bg-[#08a103] hover:bg-primary/90 text-primary-foreground">
                <Link to="/signup">
                  Sign up
                </Link>
              </Button>
        </div>

        </header>
      );
}