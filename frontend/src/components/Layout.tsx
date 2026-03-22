import Navigation from './Navigation';
import Footer from './Footer.tsx'
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <Navigation />
        <main className="app-container">
        <Outlet/>
      </main>
      <Footer />
    </div>
  );
}