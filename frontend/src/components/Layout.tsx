import Navigation from './Navigation';
import Footer from './Footer.tsx'
import { Navigate, Outlet } from "react-router-dom";
import FeedbackModal from './FeedbackModal';
import { useAuth } from '../contexts/AuthContext';

export default function Layout() {
  const { user } = useAuth();

  if (user && !user.user_type) {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
        <main className="app-container">
        <Outlet/>
      </main>
      <Footer />
      <FeedbackModal />
    </div>
  );
}
