import { NavLink } from "react-router-dom";
import idaLogo from '../assets/ida.webp';

const navItems = [
    { path: "/", label: "Home"},
    { path: "/trialsearch", label: "Trials"},
    { path: "/community", label: "Community"},
    { path: "/resourcelibrary", label: "Resources"},
    { path: "/eventshub", label: "Events"},
    { path: "/assistant", label: "Assistant"},
    { path: "/userprofile", label: "Profile"},
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
              <p className="text-xs text-muted-foreground">
                P L A T F O R M
              </p>
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {navItems.map(({ path, label }) => (
            <NavLink key={path} to={path} end={path === "/"} className={navLinkClass}>
              <span className="text-sm font-medium">{label}</span>
            </NavLink>
          ))}
        </nav>

        </header>
      );
}