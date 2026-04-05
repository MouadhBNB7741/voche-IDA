import Navigation from './Navigation';
import Footer from './Footer.tsx'
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background selection:bg-primary-color selection:text-primary-foreground">
      <Navigation />
      <main className="flex-grow w-full max-w-[1440px] mx-auto px-4 md:px-8 py-10">
        <Outlet/>
      </main>
      <Footer />
    </div>
  );
}
