<<<<<<< HEAD

export default function Footer() {
  return (
    <footer className="border-t border-border bg-background py-8">
      <div className="container px-4 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md gradient-primary flex items-center justify-center">
            </div>
            <span className="font-semibold text-sm text-foreground">VOCE Platform</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} Platform. All rights reserved.
=======
import { Globe, Github, Twitter, Linkedin, MapPin, Phone } from "lucide-react";
import { NavLink } from "react-router-dom";
import idaLogo from "../assets/ida.webp";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  const footerLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.1em] transition-all duration-500 cursor-pointer w-fit
   ${isActive
      ? "bg-primary-color text-primary-foreground shadow-2xl scale-105"
      : "text-muted-foreground hover:text-primary-color hover:bg-primary-color/5 hover:scale-105 active:scale-95"
    }`;

  const navItems = [
    { name: 'Research Hub', path: '/trials' },
    { name: 'Connect Space', path: '/community' },
    { name: 'Resources', path: '/resources' },
    { name: 'Events Calendar', path: '/events' }
  ];

  return (
    <footer className="border-0 bg-background/60 backdrop-blur-3xl pt-20 pb-20 transition-all duration-500 mt-auto selection:bg-primary-color selection:text-primary-foreground">
      <div className="container mx-auto px-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-16 mb-20 items-start">
          
          {/* Section 1: Voche Identity */}
          <div className="space-y-8">
            <div className="flex items-center gap-4 group cursor-pointer" onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}>
               <img src={idaLogo} alt="Logo" className="w-14 h-14 rounded-3xl shadow-2xl transition-all group-hover:rotate-6 group-hover:shadow-primary-color/10" />
               <span className="font-black text-2xl tracking-tighter uppercase italic text-foreground">voche</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed font-black opacity-60 max-w-[320px]">
              Transforming inclusive research across Denmark and beyond. Bridging gaps in health equity through data advocacy.
            </p>
          </div>

          {/* Section 2: Explore Hub (Pill Design) */}
          <div className="space-y-8 lg:pl-16">
            <h4 className="font-black uppercase text-[10px] tracking-[0.4em] text-primary-color opacity-70">Core Hub</h4>
            <ul className="space-y-3.5">
              {navItems.map((link, i) => (
                <li key={`footer-pill-serv-${i}`}>
                   <NavLink to={link.path} className={footerLinkClass}>
                     {link.name}
                   </NavLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Section 4: Contact & Denmark Support (Now Section 3) */}
          <div className="space-y-8 lg:pl-16">
            <h4 className="font-black uppercase text-[10px] tracking-[0.4em] text-primary-color opacity-70">Support Access</h4>
            <div className="space-y-6 font-black uppercase text-[11px] tracking-widest text-muted-foreground">
               <div className="flex items-center gap-5 group cursor-pointer hover:text-primary-color transition-colors">
                  <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center group-hover:bg-primary-color/10 transition-colors">
                    <MapPin size={18} className="text-primary-color" />
                  </div>
                  <span className="opacity-70 group-hover:opacity-100">Denmark Hub</span>
               </div>
               <div className="flex items-center gap-5 group cursor-pointer hover:text-primary-color transition-colors">
                  <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center group-hover:bg-primary-color/10 transition-colors">
                    <Phone size={18} className="text-primary-color" />
                  </div>
                  <span className="opacity-70 group-hover:opacity-100">0000000000</span>
               </div>
               <div className="flex items-center gap-5 pt-6">
                  {[Twitter, Linkedin, Github].map((Icon, i) => (
                    <a key={`footer-sos-cl-${i}`} href="#" className="w-12 h-12 rounded-2xl bg-muted/20 flex items-center justify-center text-muted-foreground hover:bg-primary-color/10 hover:text-primary-color transition-all hover:-translate-y-2 border-0 shadow-none cursor-pointer">
                      <Icon size={22} />
                    </a>
                  ))}
               </div>
            </div>
          </div>
        </div>

        <div className="border-t border-border/10 pt-14 flex flex-col md:flex-row items-center justify-between gap-8 opacity-60">
          <div className="flex items-center gap-3 text-[10px] font-black text-muted-foreground uppercase tracking-[0.5em] cursor-default">
            <Globe size={18} className="text-primary-color" />
            Inclusive Research Network
          </div>
          
          <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.5em] text-center md:text-right cursor-default">
            © {currentYear} Voche IDA. HEALTH EQUITY FOR ALL.
>>>>>>> origin/main
          </p>
        </div>
      </div>
    </footer>
  );
<<<<<<< HEAD
}
=======
}
>>>>>>> origin/main
