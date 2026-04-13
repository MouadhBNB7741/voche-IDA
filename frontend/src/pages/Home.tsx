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
  Lock,
  Heart
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from 'sonner';
import { useData } from '../contexts/DataContext';
import { useAuth } from '../contexts/AuthContext';
import type { Event, Notification, ClinicalTrial } from '../types/db';

export default function Dashboard() {
  const navigate = useNavigate();
  const { state, actions } = useData();
  const { user } = useAuth(); 

  const trials = state.trials as ClinicalTrial[] || [];
  const events = state.events as Event[] || [];
  const notifications = state.notifications as Notification[] || [];

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
      color: 'bg-primary-color'
    },
    {
      icon: Users,
      title: 'Forums',
      description: 'Connect with the community',
      path: '/community',
      color: 'bg-teal-color'
    },
    {
      icon: BookOpen,
      title: 'Resources',
      description: 'Educational materials & toolkits',
      path: '/resources',
      color: 'bg-lime-color'
    },
    {
      icon: Calendar,
      title: 'Events',
      description: 'Webinars & conferences',
      path: '/events',
      color: 'bg-blue-color'
    },
  ];

  if (!user) {
    // Guest View
    return (
      <div className="container mx-auto p-4 md:p-8 space-y-12 animate-in fade-in duration-1000">
        <PageHeader
          title="Welcome to VOCHE"
          description="Advancing health equity through accessible clinical research for everyone. Join our mission to make healthcare research inclusive."
          variant="green"
        />

        {/* Quick Actions (Public) */}
        <div className="pt-4">
          <h2 className="text-xl font-bold mb-10 flex items-center gap-3"><ShieldCheck size={28} className="text-primary-color" /> Explore the Platform</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {quickActions.map((action, index) => {
              const Icon = action.icon;
              return (
                <Link key={`guest-action-pill-${index}`} to={action.path} className="group h-full cursor-pointer">
                  <Card className="p-10 bg-card/30 backdrop-blur-xl border-border/10 hover:bg-card/50 hover:shadow-[0_45px_90px_-25px_rgba(16,185,129,0.4)] hover:-translate-y-4 transition-all duration-1000 text-center flex flex-col items-center h-full justify-center cursor-pointer shadow-sm">
                    <div className={`w-20 h-20 ${action.color} rounded-[2.2rem] flex items-center justify-center mb-10 shadow-2xl group-hover:scale-110 group-hover:rotate-6 transition-all duration-1000`}>
                      <Icon size={38} className="text-white" />
                    </div>
                    <h3 className="font-extrabold text-xl mb-3 group-hover:text-primary-color tracking-tight transition-colors duration-500">{action.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed font-bold opacity-60 transition-colors duration-500">{action.description}</p>
                  </Card>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Upcoming Events (Public) */}
        <Card className="p-10 md:p-14 rounded-[3.5rem] border-0 bg-card/20 backdrop-blur-2xl shadow-2xl relative overflow-hidden group">
          <div className="absolute -top-32 -right-32 w-96 h-96 bg-primary-color/5 rounded-full blur-[120px] transition-all duration-1000 group-hover:scale-125 -z-10"></div>
          
          <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-12 gap-8">
            <div>
              <h2 className="text-4xl font-black tracking-tighter flex items-center gap-5">
                <Calendar size={36} className="text-primary-color" />
                Live Sessions
              </h2>
              <p className="text-muted-foreground mt-3 text-lg font-medium opacity-80">Join expert-led sessions and community meetups.</p>
            </div>
            <Link to="/events">
              <Button variant="outline" className="rounded-2xl border-primary-color/20 hover:bg-primary-color/10 text-primary-color font-black h-14 px-10 group shadow-xl hover:shadow-primary-color/20 cursor-pointer transition-all">
                Explore Calendar <ChevronRight size={22} className="ml-2 group-hover:translate-x-2 transition-transform duration-500" />
              </Button>
            </Link>
          </div>
          
          <div className="grid md:grid-cols-3 gap-10">
            {upcomingEvents.map((event, index) => (
              <Card key={`guest-event-card-item-${event.event_id || index}`} className="bg-background/40 border-border/5 rounded-[3rem] p-10 shadow-2xl hover:shadow-[0_45px_90px_-25px_rgba(16,185,129,0.3)] hover:bg-card hover:border-primary-color/20 hover:-translate-y-4 transition-all duration-1000 group/item cursor-pointer h-full flex flex-col">
                <Badge variant="outline" className="mb-8 border-primary-color/10 bg-primary-color/5 text-primary-color font-black uppercase tracking-[0.3em] text-[10px] px-5 py-2.5 rounded-full shadow-inner w-fit">
                  {event.type}
                </Badge>
                <h3 className="font-black text-xl mb-6 line-clamp-2 md:line-clamp-3 min-h-[56px] group-hover/item:text-primary-color transition-colors duration-700 leading-tight tracking-tight uppercase ">{event.title}</h3>
                <div className="text-[12px] text-muted-foreground mb-12 space-y-6 font-black uppercase tracking-widest opacity-80 flex-grow">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center group-hover/item:bg-primary-color group-hover/item:text-white transition-all duration-700">
                       <Clock size={20} />
                    </div>
                    <span className="text-foreground">{event.event_date ? new Date(event.event_date).toLocaleDateString() : 'Now'}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center group-hover/item:bg-primary-color group-hover/item:text-white transition-all duration-700">
                       <MapPin size={20} />
                    </div>
                    <span className="text-foreground truncate max-w-[150px]">Denmark Hub</span>
                  </div>
                </div>
                <div className="flex gap-4 pt-4">
                  <Button size="lg" className="w-full bg-primary-color text-primary-foreground font-black rounded-2xl h-16 shadow-2xl shadow-primary-color/20 hover:shadow-primary-color/50 hover:scale-105 transition-all cursor-pointer" onClick={() => navigate(`/events/${event.event_id}`)}>
                    Details
                  </Button>
                  <Button size="lg" variant="ghost" className="px-6 rounded-2xl border-0 bg-muted/40 hover:bg-muted/60 cursor-pointer" title="Login to register">
                    <Lock size={24} className="text-primary-color/70 hover:text-primary-color transition-colors" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  // Authenticated View
  const firstName = user.first_name || user.display_name?.split(' ')[0] || 'Member';
  
  return (
    <div className="container mx-auto p-4 md:p-8 space-y-14 animate-in fade-in duration-1000">
      <PageHeader
        title={`Hi, ${firstName}!`}
        description="Your gateway to inclusive clinical research and community support. Ready to contribute today?"
        badgeText={`Active ${user.user_type || 'member'}`}
        variant="green"
        action={
          <div className="hidden md:block">
            <div className="w-24 h-24 bg-primary-color/10 rounded-[2rem] flex items-center justify-center backdrop-blur-xl shadow-2xl rotate-6 group hover:rotate-0 transition-transform duration-700">
              <Activity size={40} className=" animate-pulse" />
            </div>
          </div>
        }
      />

      <div className="grid md:grid-cols-2 gap-10 lg:gap-14">
        {/* User Status Card */}
        <Card className="p-10 md:col-span-2 bg-gradient-to-br from-card/40 to-muted/20 border border-border/5 shadow-[0_45px_100px_-25px_rgba(0,0,0,0.2)] rounded-[3.5rem] relative overflow-hidden group hover:shadow-[0_60px_120px_-30px_rgba(0,0,0,0.4)] transition-all duration-700 cursor-pointer">
          <div className="absolute right-0 top-0 p-12 opacity-5 group-hover:opacity-10 transition-opacity duration-1000 scale-150">
            <TrendingUp size={140} />
          </div>
          <div className="flex flex-col lg:flex-row gap-10 items-center relative z-10">
            <div className="relative">
              <Avatar className="w-32 h-32 border-4 border-primary-color/20 shadow-2xl ring-8 ring-primary-color/5 group-hover:ring-primary-color/10 transition-all duration-700">
                <AvatarImage src={user.avatar} />
                <AvatarFallback className="bg-primary text-primary-foreground text-4xl font-black">
                  {user.display_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'V'}
                </AvatarFallback>
              </Avatar>
              <div className="absolute -bottom-2 -right-2 w-10 h-10 bg-success-color rounded-[1.2rem] border-4 border-card flex items-center justify-center shadow-2xl">
                <CheckCircle2 size={20} className="text-white" />
              </div>
            </div>

            <div className="flex-1 text-center lg:text-left space-y-4">
              <div className="flex flex-col lg:flex-row items-center gap-4">
                <h3 className="text-2xl font-black tracking-tight">{user.display_name}</h3>
                <Badge className="px-4 py-1.5 text-[10px] font-black bg-primary-color text-primary-foreground border-none rounded-full uppercase tracking-[0.15em] shadow-lg shadow-primary-color/20">
                  {user.user_type || 'Member'}
                </Badge>
              </div>
              <p className="text-sm font-medium text-muted-foreground/90 line-clamp-2 max-w-xl">
                 {user.bio || 'Your journey to inclusive health research starts here. Join our mission as a key contributor.'}
              </p>
              
              <div className="flex flex-wrap justify-center lg:justify-start gap-x-8 gap-y-4 text-[11px] text-muted-foreground font-black uppercase tracking-[0.2em] pt-2">
                <div className="flex items-center gap-3 group/info hover:text-primary-color transition-colors">
                  <div className="p-2 bg-secondary-color/10 rounded-xl group-hover/info:bg-primary-color/10 transition-colors">
                    <MapPin size={16} className="text-secondary-color group-hover/info:text-primary-color" />
                  </div>
                  {user.location || 'Hub Access'}
                </div>
                <div className="flex items-center gap-3 group/info hover:text-destructive transition-colors">
                  <div className="p-2 bg-destructive/5 rounded-xl group-hover/info:bg-destructive/10 transition-colors">
                    <Heart size={16} className="text-destructive opacity-70" fill="currentColor" />
                  </div>
                  {state.savedTrials.length} Matches Found
                </div>
                <div className="flex items-center gap-3 group/info hover:text-blue-500 transition-colors">
                  <div className="p-2 bg-blue-500/5 rounded-xl group-hover/info:bg-blue-500/10 transition-colors">
                    <Activity size={16} className="text-blue-500 opacity-70" />
                  </div>
                  {user.is_verified ? 'Identity Verified' : 'Standard Access'}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3">
               <Button
                variant="default"
                size="lg"
                className="gap-3 rounded-2xl bg-primary-color text-primary-foreground shadow-2xl shadow-primary-color/30 font-black h-14 px-8 transition-all active:scale-95 cursor-pointer hover:shadow-primary-color/50"
                onClick={() => navigate(user.user_type === 'hcp' ? '/hcpdashboard' : '/patientdashboard')}
              >
                <Edit size={18} className="text-white" />
                Profile Settings
              </Button>
              <p className="text-[10px] font-black uppercase tracking-widest text-center opacity-30 italic">Edit Profile</p>
            </div>
          </div>
        </Card>

        {/* Pulse Panel */}
        <Card className="p-10 border-0 bg-card/40 backdrop-blur-2xl shadow-2xl rounded-[3rem] hover:shadow-[0_45px_100px_-25px_rgba(16,185,129,0.2)] transition-all duration-700 group cursor-pointer">
          <div className="flex items-center justify-between mb-10">
            <h2 className="text-2xl font-black tracking-tighter flex items-center gap-4">
              <Bell size={28} className="text-secondary-color" />
              Pulse
            </h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/notifications')} className="text-muted-foreground hover:text-secondary-color font-black uppercase tracking-widest text-[10px] hover:bg-secondary-color/5 rounded-xl px-4 h-10 transition-all cursor-pointer">
              View History
            </Button>
          </div>
          <div className="space-y-5">
            {notifications.length === 0 ? (
              <div className="text-center py-16 space-y-4">
                <div className="w-20 h-20 bg-muted/20 rounded-full flex items-center justify-center mx-auto scale-110">
                  <Bell size={40} className="text-muted/30" />
                </div>
                <p className="text-sm font-black text-muted-foreground uppercase tracking-widest opacity-40">Healthy Silence</p>
              </div>
            ) : (
              recentNotifications.map((notification, index) => (
                <div
                  key={`auth-notif-pulse-v3-${notification.notification_id || index}`}
                  className={`p-6 rounded-[2rem] border border-border/5 transition-all duration-500 cursor-pointer hover:translate-x-2 hover:bg-card hover:shadow-xl active:scale-98 group/notif ${!notification.read ? 'bg-primary-color/5 shadow-lg shadow-primary-color/5 border-primary-color/10' : 'bg-background/20 opacity-80'
                    }`}
                  onClick={() => navigate('/notifications')}
                >
                  <div className="flex justify-between items-start mb-3">
                    <h4 className={`font-black text-lg group-hover/notif:text-primary-color transition-colors duration-500 leading-tight ${!notification.read ? 'text-primary-color' : 'text-foreground'}`}>
                      {notification.title}
                    </h4>
                    <span className="text-[10px] font-black uppercase tracking-tighter bg-muted/30 px-2 py-0.5 rounded-md opacity-60">
                      {notification.created_at ? new Date(notification.created_at).toLocaleDateString() : 'Now'}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2 font-medium">{notification.message}</p>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Matches Panel */}
        <Card className="p-10 border-0 bg-card/40 backdrop-blur-2xl shadow-2xl rounded-[3rem] hover:shadow-[0_45px_100px_-25px_rgba(16,185,129,0.3)] transition-all duration-700 cursor-pointer">
          <div className="flex items-center justify-between mb-10">
            <h2 className="text-2xl font-black tracking-tighter flex items-center gap-4">
              <FlaskConical size={28} className="text-primary-color" />
              Matches
            </h2>
            <Link to="/trials">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary-color font-black uppercase tracking-widest text-[10px] hover:bg-primary-color/5 rounded-xl px-4 h-10 transition-all cursor-pointer">
                Full Registry <ChevronRight size={14} className="ml-1" />
              </Button>
            </Link>
          </div>
          <div className="space-y-6">
            {featuredTrials.map((trial, index) => (
              <div key={`auth-trial-match-item-v3-${trial.trial_id || index}`} className="border border-border/5 rounded-[2.5rem] p-7 hover:shadow-2xl hover:bg-card hover:border-primary-color/20 transition-all duration-700 bg-background/30 group cursor-pointer" onClick={() => navigate(`/trials/${trial.trial_id}`)}>
                <div className="flex justify-between items-start mb-5">
                  <Badge variant="outline" className="bg-primary-color/5 text-primary-color border-primary-color/10 font-black uppercase text-[9px] tracking-widest px-4 py-1.5 rounded-full shadow-sm">
                    {trial.disease_area || 'Oncology'}
                  </Badge>
                  <Badge variant="secondary" className="px-4 py-1.5 font-black text-[9px] rounded-lg bg-secondary-color/10 text-secondary-color border-0 uppercase tracking-widest">
                    {trial.phase}
                  </Badge>
                </div>
                <h3 className="font-extrabold text-xl mb-4 line-clamp-1 group-hover:text-primary-color transition-colors leading-tight duration-500">{trial.title}</h3>
                <div className="flex items-center text-xs text-muted-foreground mb-8 gap-6 font-bold uppercase tracking-widest opacity-80">
                  <span className="flex items-center gap-2">
                    <MapPin size={16} className="text-primary-color" />
                    Denmark Hub
                  </span>
                  <span className="flex items-center gap-2 text-primary-color">
                    <Activity size={16} className="opacity-60" />
                    {trial.enrollment} Enrolled
                  </span>
                </div>
                <Button className="w-full shadow-2xl shadow-primary-color/10 rounded-2xl font-black h-14 bg-primary-color text-primary-foreground text-xs uppercase tracking-widest border-0 hover:shadow-primary-color/50 transition-all duration-500 cursor-pointer">
                  Consultation
                </Button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Instant Access */}
      <div className="pt-10">
        <h2 className="text-2xl font-black mb-12 flex items-center gap-3 underline decoration-primary-color/30 decoration-8 underline-offset-[12px]"><ShieldCheck size={32} className="text-primary-color" /> Priority Access</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <Link key={`auth-act-priority-pills-${index}`} to={action.path} className="group h-full cursor-pointer">
                <Card className="p-10 backdrop-blur-2xl hover:shadow-[0_45px_100px_-20px_rgba(16,185,129,0.5)] hover:-translate-y-4 transition-all duration-1000 cursor-pointer border-border/10 hover:border-primary-color/20 text-center flex flex-col items-center h-full justify-center bg-card/30 cursor-pointer">
                  <div className={`w-20 h-20 ${action.color} rounded-[2.2rem] flex items-center justify-center mb-10 shadow-2xl group-hover:scale-110 group-hover:rotate-12 transition-all duration-1000`}>
                    <Icon size={38} className="text-white" />
                  </div>
                  <h3 className="font-black text-xl mb-3 group-hover:text-primary-color tracking-tighter transition-colors duration-500 leading-none">{action.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed font-bold opacity-60 transition-colors duration-500">{action.description}</p>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Community Space */}
      <Card className="p-10 md:p-20 rounded-[4.5rem] border-0 bg-card/30 backdrop-blur-3xl shadow-[0_48px_100px_-24px_rgba(0,0,0,0.15)] relative overflow-hidden group hover:shadow-[0_64px_128px_-32px_rgba(0,0,0,0.25)] transition-all duration-1000 cursor-pointer">
        <div className="absolute -top-40 -right-40 w-[35rem] h-[35rem] bg-primary-color/5 rounded-full blur-[160px] transition-all duration-1000 group-hover:scale-110 -z-10"></div>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-20 gap-12 text-center lg:text-left">
          <div>
            <h2 className="text-2xl md:text-4xl font-black tracking-tighter flex flex-col lg:flex-row items-center gap-5 leading-none">
              <Calendar size={40} className="text-primary-color" />
              Community Calendar
            </h2>
            <p className="text-muted-foreground mt-4 text-base md:text-lg font-bold opacity-70 max-w-2xl leading-relaxed">Connect with global leaders in inclusive healthcare and stay ahead of the latest research breakthroughs.</p>
          </div>
          <Link to="/events">
            <Button variant="outline" className="rounded-[2rem] border-primary-color/10 bg-background/40 hover:bg-primary-color/10 text-primary-color font-black h-14 px-8 group  uppercase tracking-[0.2em] hover:shadow-primary-color/20 cursor-pointer">
              Explore All <ChevronRight size={32} className="ml-4 group-hover:translate-x-4 transition-transform duration-700" />
            </Button>
          </Link>
        </div>
        <div className="grid md:grid-cols-3 gap-12">
          {upcomingEvents.map((event, index) => {
            const isRegistered = state.registeredEvents.includes(event.event_id);
            return (
              <Card key={`auth-ev-calendar-match-v3-${event.event_id || index}`} className="border-border/5 bg-background/25 backdrop-blur-xl rounded-[3.5rem] p-12 hover:shadow-[0_45px_100px_-25px_rgba(16,185,129,0.4)] hover:bg-card hover:border-primary-color/30 hover:-translate-y-4 transition-all duration-1000 group/ev relative cursor-pointer flex flex-col">
                <Badge variant="outline" className="mb-10 border-primary-color/10 bg-primary-color/5 text-primary-color font-black uppercase tracking-[0.4em] text-[10px] px-6 py-3 rounded-full shadow-inner w-fit">
                  {event.type || 'Webinar'}
                </Badge>
                <h3 className="font-black text-2xl mb-8 line-clamp-3 min-h-[72px] group-hover/ev:text-primary-color transition-colors duration-700 leading-tight tracking-tight uppercase ">{event.title}</h3>
                <div className="text-[12px] text-muted-foreground mb-12 space-y-6 font-black uppercase tracking-widest opacity-80 flex-grow">
                  <div className="flex items-center gap-5">
                    <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center border border-primary-color/5 group-hover/ev:bg-primary-color group-hover/ev:text-white transition-all duration-700">
                      <Clock size={22} />
                    </div>
                    <span className="text-foreground">{event.event_date ? new Date(event.event_date).toLocaleDateString() : 'Now'}</span>
                  </div>
                  <div className="flex items-center gap-5">
                     <div className="w-12 h-12 rounded-2xl bg-primary-color/5 flex items-center justify-center border border-primary-color/5 group-hover/ev:bg-primary-color group-hover/ev:text-white transition-all duration-700">
                      <MapPin size={22} />
                    </div>
                    <span className="text-foreground truncate max-w-[170px]">Denmark Hub</span>
                  </div>
                </div>
                <Button
                  size="lg"
                  variant={isRegistered ? "default" : "outline"}
                  className={`w-full rounded-2xl font-black h-18 shadow-2xl text-[10px] uppercase tracking-[0.25em] border-0 transition-all cursor-pointer ${isRegistered ? "bg-success-color hover:bg-success-color/90 text-white shadow-success-color/20" : "bg-muted/40 hover:bg-primary-color hover:text-white shadow-primary-color/10"}`}
                  onClick={(e) => handleRegister(e, event.event_id, event.title)}
                >
                  {isRegistered ? <><CheckCircle2 size={28} className="mr-3" /> Registered</> : "Apply Now"}
                </Button>
              </Card>
            );
          })}
        </div>
      </Card>
    </div>
  );
}