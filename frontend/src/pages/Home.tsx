import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import {
  FlaskConical,
  Users,
  BookOpen,
  Calendar,
  MapPin,
  Clock,
  TrendingUp,
  Bell,
  ChevronRight,
  ShieldCheck,
  Edit,
  Activity,
  CheckCircle2,
  Lock
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from 'sonner';
import { useData } from '../contexts/DataContext';
import { useAuth } from '../contexts/AuthContext';

export default function Dashboard() {
  const navigate = useNavigate();
  const { state, actions } = useData();
  const { user } = useAuth(); // Use AuthContext for user state

  // If not logged in, user is null.
  // const { currentUser } = state; // We typically use AuthContext for the active session, but DataContext holds the full user profile if fetched separately.
  // For now, let's assume useAuth() returns the primary user object.
  // DataContext might need to sync with AuthContext or we just use AuthContext here.

  const { trials, events, notifications } = state;

  // Get featured trials and events for dashboard
  const featuredTrials = trials.slice(0, 2);
  const upcomingEvents = events.slice(0, 3);
  const recentNotifications = notifications.slice(0, 3);

  const handleRegister = (e: React.MouseEvent, eventId: string, eventName: string) => {
    e.stopPropagation();
    if (state.registeredEvents.includes(eventId)) {
      actions.unregisterEvent(eventId);
      toast.info("Registration Cancelled", {
        description: `You are no longer registered for ${eventName}.`
      });
    } else {
      actions.registerEvent(eventId, eventName);
      toast.success("Registered Successfully", {
        description: `You have been registered for ${eventName}. Check your email for details.`
      });
    }
  };

  const quickActions = [
    {
      icon: FlaskConical,
      title: 'Find Trials',
      description: 'Search clinical trials in your area',
      path: '/trials',
      color: 'bg-[hsl(var(--primary))]'
    },
    {
      icon: Users,
      title: 'Forums',
      description: 'Connect with the community',
      path: '/community',
      color: 'bg-[hsl(var(--teal))]'
    },
    {
      icon: BookOpen,
      title: 'Resources',
      description: 'Educational materials & toolkits',
      path: '/resources',
      color: 'bg-[hsl(var(--lime))]'
    },
    {
      icon: Calendar,
      title: 'Events',
      description: 'Webinars & conferences',
      path: '/events',
      color: 'bg-[hsl(var(--blue))]'
    },
  ];

  if (!user) {
    // Guest View
    return (
      <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
        <PageHeader 
          title="Welcome to VOCE"
          description="Advancing health equity through accessible clinical research for everyone."
          variant="orange"
          action={
            <div className="flex gap-4">
              <Button onClick={() => navigate('/login')} className="shadow-lg">Login</Button>
              <Button variant="outline" onClick={() => navigate('/register')} className="bg-white/10 border-white/20 text-foreground hover:bg-white/20">Register</Button>
            </div>
          }
        />

        {/* Quick Actions (Public) */}
        <div className="pt-4">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><ShieldCheck size={18} className="text-accent" /> Explore the Platform</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Link key={index} to={action.path}>
                  <Card className="p-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer group border-transparent hover:border-border text-center flex flex-col items-center h-full justify-center bg-card">
                    <div className={`w-14 h-14 ${action.color} rounded-2xl flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                      <Icon size={28} className="text-white" />
                    </div>
                    <h3 className="font-bold text-base mb-1 group-hover:text-primary transition-colors">{action.title}</h3>
                    <p className="text-xs text-muted-foreground leading-snug max-w-[120px]">{action.description}</p>
                  </Card>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Upcoming Events (Public) */}
        <Card className="p-6 md:p-8 overflow-hidden relative bg-card shadow-sm border-none rounded-2xl">
          <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl -z-10"></div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Calendar size={20} className="text-accent" />
              Upcoming Events
            </h2>
            <Link to="/events">
              <Button variant="ghost" size="sm" className="text-accent hover:text-accent-foreground hover:bg-accent/10">
                View All <ChevronRight size={16} />
              </Button>
            </Link>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {upcomingEvents.map((event) => (
              <div key={event.id} className="bg-white/70 backdrop-blur-sm rounded-xl p-5 shadow-sm hover:shadow-md transition-all">
                <Badge variant="outline" className="mb-3 border-accent/30 text-accent font-bold uppercase tracking-wider text-[10px]">
                  {event.type}
                </Badge>
                <h3 className="font-bold text-sm mb-3 min-h-[40px] line-clamp-2">{event.title}</h3>
                <div className="text-xs text-muted-foreground mb-4 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Clock size={12} className="text-accent" />
                    <span className="font-medium text-foreground">{new Date(event.date).toLocaleDateString()}</span> at {event.time}
                  </div>
                  <div className="pl-5">By <span className="text-foreground">{event.organizer}</span></div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" className="w-full" onClick={() => navigate(`/events/${event.id}`)}>
                    Details
                  </Button>
                  <Button size="sm" variant="ghost" className="px-2" title="Login to register">
                    <Lock size={14} className="text-muted-foreground" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  // Authenticated View
  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title={`Welcome back, ${user.name}!`}
        description="Stay connected with the global community working towards health equity."
        badgeText="Member Since 2024"
        variant="orange"
        action={
          <div className="hidden md:block">
            <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
              <Users size={32} className="text-white" />
            </div>
          </div>
        }
      />

      <div className="grid md:grid-cols-2 gap-6">
        {/* User Status Card */}
        <Card className="p-6 md:col-span-2 bg-gradient-to-r from-card to-muted/20 border-border/50 shadow-sm relative overflow-hidden group">
          <div className="absolute right-0 top-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
            <Activity size={100} />
          </div>
          <div className="flex flex-col sm:flex-row gap-6 items-center relative z-10">
            <Avatar className="w-16 h-16 border-2 border-primary/20 shadow-md">
              <AvatarImage src={localStorage.getItem('voce_profile_image') || user.avatar} />
              <AvatarFallback className="bg-primary text-primary-foreground text-xl font-bold">
                {user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1 text-center sm:text-left space-y-1">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <h3 className="text-lg font-bold">{user.name}</h3>
                <Badge variant="outline" className="px-2 py-0.5 text-xs border-primary/20 bg-primary/5 text-primary">
                  {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                </Badge>
              </div>
              <div className="flex flex-wrap justify-center sm:justify-start gap-x-4 gap-y-1 text-sm text-muted-foreground">
                <div className="flex items-center gap-1">
                  <MapPin size={14} />
                  {user.location || 'Location not set'}
                </div>
                <div className="hidden sm:block text-border">•</div>
                <div className="font-medium text-foreground/80">
                  {state.savedTrials.length} Saved Trials
                </div>
              </div>
            </div>

            <Button variant="outline" size="sm" className="gap-2 shadow-sm" onClick={() => navigate('/profile')}>
              <Edit size={14} />
              Edit Profile
            </Button>
          </div>
        </Card>

        {/* Notifications Panel */}
        <Card className="p-6 border-l-4 border-l-secondary shadow-md hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Bell size={20} className="text-secondary" />
              Notifications
            </h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/notifications')} className="text-muted-foreground hover:text-secondary">
              View All
            </Button>
          </div>
          <div className="space-y-4">
            {notifications.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">No notifications</p>
            ) : (
              recentNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 rounded-xl border transition-all cursor-pointer hover:bg-muted/50 group ${!notification.read ? 'border-primary/30 bg-primary/5' : 'border-dashed'
                    }`}
                  onClick={() => navigate('/notifications')}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h4 className={`font-semibold text-sm group-hover:text-primary transition-colors ${!notification.read ? 'text-primary' : 'text-foreground'}`}>
                      {notification.title}
                    </h4>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{notification.time}</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-snug line-clamp-2">{notification.message}</p>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Personalized Trial Alerts */}
        <Card className="p-6 border-l-4 border-l-primary shadow-md hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp size={20} className="text-primary" />
              Recommended for You
            </h2>
            <Link to="/trials">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                View All <ChevronRight size={16} />
              </Button>
            </Link>
          </div>
          <div className="space-y-4">
            {featuredTrials.map((trial) => (
              <div key={trial.id} className="border border-border rounded-xl p-5 hover:border-primary/50 transition-colors bg-card hover:bg-muted/10">
                <div className="flex justify-between items-start mb-3">
                  <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20">
                    {trial.disease}
                  </Badge>
                  <Badge variant="secondary" className="font-normal text-xs">
                    {trial.phase}
                  </Badge>
                </div>
                <h3 className="font-bold text-base mb-2 line-clamp-1">{trial.title}</h3>
                <div className="flex items-center text-xs text-muted-foreground mb-4 gap-4">
                  <span className="flex items-center gap-1">
                    <MapPin size={12} />
                    {trial.location}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users size={12} />
                    {trial.enrollment} enrolled
                  </span>
                </div>
                <Button size="sm" className="w-full shadow-sm" asChild>
                  <Link to={`/trials/${trial.id}`}>Learn More</Link>
                </Button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Quick Actions (Authenticated) */}
      <div className="pt-4">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><ShieldCheck size={18} className="text-accent" /> Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <Link key={index} to={action.path}>
                <Card className="p-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer group border-transparent hover:border-border text-center flex flex-col items-center h-full justify-center bg-card">
                  <div className={`w-14 h-14 ${action.color} rounded-2xl flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                    <Icon size={28} className="text-white" />
                  </div>
                  <h3 className="font-bold text-base mb-1 group-hover:text-primary transition-colors">{action.title}</h3>
                  <p className="text-xs text-muted-foreground leading-snug max-w-[120px]">{action.description}</p>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Upcoming Events */}
      <Card className="p-6 md:p-8 overflow-hidden relative /60">
        <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl -z-10"></div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Calendar size={20} className="text-accent" />
            Upcoming Events
          </h2>
          <Link to="/events">
            <Button variant="ghost" size="sm" className="text-accent hover:text-accent-foreground hover:bg-accent/10">
              View All <ChevronRight size={16} />
            </Button>
          </Link>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {upcomingEvents.map((event) => {
            const isRegistered = state.registeredEvents.includes(event.id);
            return (
              <div key={event.id} className="border border-border/60 bg-background/50 backdrop-blur-sm rounded-xl p-5 hover:shadow-md transition-all">
                <Badge variant="outline" className="mb-3 border-accent/30 text-accent font-bold uppercase tracking-wider text-[10px]">
                  {event.type}
                </Badge>
                <h3 className="font-bold text-sm mb-3 min-h-[40px] line-clamp-2">{event.title}</h3>
                <div className="text-xs text-muted-foreground mb-4 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Clock size={12} className="text-accent" />
                    <span className="font-medium text-foreground">{new Date(event.date).toLocaleDateString()}</span> at {event.time}
                  </div>
                  <div className="pl-5">By <span className="text-foreground">{event.organizer}</span></div>
                </div>
                <Button
                  size="sm"
                  variant={isRegistered ? "default" : "outline"}
                  className={`w-full border-accent/20 ${isRegistered ? "bg-green-600 hover:bg-green-700 text-white" : "hover:bg-accent hover:text-white"}`}
                  onClick={(e) => handleRegister(e, event.id, event.title)}
                >
                  {isRegistered ? <><CheckCircle2 size={16} className="mr-2" /> Registered</> : "Register Now"}
                </Button>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}