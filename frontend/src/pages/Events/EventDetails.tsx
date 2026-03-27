import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import {
  Calendar,
  Clock,
  MapPin,
  Users,
  Building,
  ArrowLeft,
  Share2,
  CalendarPlus,
  CheckCircle2,
  Video
} from 'lucide-react';
import { PageHeader } from '../../components/ui/PageHeader';
import { toast } from 'sonner';
import { useData } from '../../contexts/DataContext';

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state, actions } = useData();

  const event = state.events.find(e => e.id === id);
  const isRegistered = id ? state.registeredEvents.includes(id) : false;

  if (!event) {
    return (
      <div className="container mx-auto p-8 text-center animate-in fade-in">
        <h2 className="text-2xl font-bold mb-4">Event not found</h2>
        <Button onClick={() => navigate('/events')}>Return to Events</Button>
      </div>
    );
  }

  const handleRegister = () => {
    if (isRegistered) {
      actions.unregisterEvent(event.id);
      toast.info("Registration Cancelled", {
        description: `You are no longer registered for ${event.title}.`
      });
    } else {
      actions.registerEvent(event.id, event.title);
      toast.success("Registration Successful", {
        description: `You have been registered for ${event.title}. Check your email for details.`
      });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success("Link Copied", {
      description: "Event link copied to clipboard."
    });
  };

  const handleAddToCalendar = () => {
    toast.success("Added to Calendar", {
      description: "Event has been added to your calendar."
    });
  };

  // Mock related events based on type
  const relatedEvents = state.events
    .filter(e => e.type === event.type && e.id !== event.id)
    .slice(0, 3);

  // Helper for safe distance access
  const locationText = event.location || (event.type === 'webinar' ? 'Online' : 'Global');
  const distanceText = event.distance ?? 'Online';

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <Button
        variant="ghost"
        onClick={() => navigate('/events')}
        className="mb-4 pl-0 hover:pl-2 transition-all"
      >
        <ArrowLeft size={16} className="mr-2" /> Back to Events
      </Button>

      <PageHeader
        title={event.title}
        description={event.description}
        variant="green"
        badgeText={`${event.type.charAt(0).toUpperCase() + event.type.slice(1)} • ${distanceText}`}
        action={
          <div className="flex gap-3">
            <Button
              variant="secondary"
              size="lg"
              className="shadow-lg hover:scale-105 transition-transform font-bold gap-2"
              onClick={handleAddToCalendar}
            >
              <CalendarPlus size={20} />
              Add to Calendar
            </Button>
            <Button
              size="lg"
              className={`shadow-lg hover:scale-105 transition-transform font-bold gap-2 ${isRegistered ? "bg-primary-color hover:bg-primary-color text-white border-green-600" : "bg-white text-orange-600 hover:bg-gray-100"}`}
              onClick={handleRegister}
            >
              {isRegistered ? <CheckCircle2 size={20} /> : <CheckCircle2 size={20} className="hidden" />}
              {isRegistered ? "Registered" : "Register Now"}
            </Button>
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          <Card className="p-8 border-border/60 shadow-sm">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Building className="text-accent-color" />
              Event Details
            </h2>

            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-orange-50 dark:bg-orange-900/10">
                  <Calendar className="text-orange-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Date</h4>
                    <p className="text-muted-foreground">{new Date(event.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/10">
                  <Clock className="text-blue-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Time</h4>
                    <p className="text-muted-foreground">{event.time} (UTC)</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-green-50 dark:bg-green-900/10">
                  <MapPin className="text-green-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Location</h4>
                    <p className="text-muted-foreground">{locationText}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-50 dark:bg-purple-900/10">
                  <Users className="text-purple-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Organizer</h4>
                    <p className="text-muted-foreground">{event.organizer}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="prose dark:prose-invert max-w-none">
              <h3 className="font-bold text-lg mb-3">About this Event</h3>
              <p className="text-muted-foreground leading-relaxed mb-6">
                This event brings together experts, advocates, and community members to discuss critical issues in health equity.
                Participants will have the opportunity to engage in Q&A sessions, network with peers, and access exclusive resources.
                {event.description}
              </p>

              <h3 className="font-bold text-lg mb-3">Agenda Highlights</h3>
              <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
                <li>Opening Keynote: The Future of Global Health Equity</li>
                <li>Panel Discussion: Barriers to Clinical Trial Participation</li>
                <li>Interactive Workshop: Community Advocacy Strategies</li>
                <li>Networking & Resource Sharing</li>
              </ul>
            </div>

            <div className="mt-8 pt-6 border-t flex flex-wrap gap-2">
              {event.tags.map(tag => (
                <Badge key={tag} variant="secondary" className="px-3 py-1 text-white">#{tag}</Badge>
              ))}
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="p-6 border-border/60 shadow-sm sticky top-24">
            <h3 className="font-bold mb-4">Registration Status</h3>
            {isRegistered ? (
              <div className="text-center p-6 bg-primary-color dark:bg-green-900/10 rounded-xl border border-green-100 dark:border-green-900/30 mb-4 animate-in zoom-in">
                <div className="w-12 h-12 bg-green-100 dark:bg-primary-color rounded-full flex items-center justify-center mx-auto mb-3 text-green-600">
                  <CheckCircle2 size={24} />
                </div>
                <h4 className="font-bold text-primary-color dark:text-primary-color mb-1">You are Registered!</h4>
                <p className="text-xs text-primary-color dark:text-primary-color">Check your email for access link.</p>
              </div>
            ) : (
              <div className="text-center p-6 bg-muted/30 rounded-xl border border-border/50 mb-4">
                <p className="text-sm text-muted-foreground mb-4">Registration is open to all community members.</p>
                <Button className="w-full" onClick={handleRegister}>Register Now</Button>
              </div>
            )}

            <div className="space-y-3">
              <Button variant="outline" className="w-full justify-start gap-3" onClick={handleShare}>
                <Share2 size={16} /> Share Event
              </Button>
              {event.type === 'webinar' && (
                <Button variant="outline" className="w-full justify-start gap-3">
                  <Video size={16} /> Test Video Access
                </Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}