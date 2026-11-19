import { Navigate } from 'react-router-dom';
import Cookies from 'universal-cookie';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { dashboardPathFor } from '../utils/dashboard';

/**
 * /profile opens the dashboard that holds the user's settings.
 */
export default function ProfileRedirect() {
  const { user, isLoading } = useAuth();

  if (user) {
    return <Navigate to={dashboardPathFor(user.user_type)} replace />;
  }
  if (!isLoading && !new Cookies().get('voche_token')) {
    return <Navigate to="/login" replace />;
  }
  return (
    <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Loading">
      <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
    </div>
  );
}
