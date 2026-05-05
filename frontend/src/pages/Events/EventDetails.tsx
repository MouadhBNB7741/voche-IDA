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
  Video,
  Loader2
} from 'lucide-react';
import { PageHeader } from '../../components/ui/PageHeader';
import { toast } from 'sonner';

import {
  useEventById,
  useRegisterEvent,
  useCancelRegistration
} from '../../hooks/useEvents';

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: event, isLoading, isError } = useEventById(id);
  const registerMutation = useRegisterEvent(id);
  const cancelMutation = useCancelRegistration(id);

  const isRegistered = event?.is_registered;

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
      </div>
    );
  }

  // Error 
  if (isError || !event) {
    return (
      <div className="container mx-auto p-8 text-center">
        <h2 className="text-2xl font-bold mb-4">Event not found</h2>
        <Button onClick={() => navigate('/events')}>Return to Events</Button>
      </div>
    );
  }

  const handleRegister = () => {
    if (isRegistered) {
      cancelMutation.mutate();
    } else {
      registerMutation.mutate();
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Link Copied', {
      description: 'Event link copied to clipboard.'
    });
  };

  const handleAddToCalendar = () => {
    toast.success('Added to Calendar', {
      description: 'Event has been added to your calendar.'
    });
  };

  const locationText =
    event.location || (event.type === 'webinar' ? 'Online' : 'Global');

  const distanceText = event.timezone ?? 'Online';

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
        badgeText={`${event.type} • ${distanceText}`}
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
              className={`shadow-lg hover:scale-105 transition-transform font-bold gap-2 ${
                isRegistered
                  ? 'bg-primary-color text-white'
                  : 'bg-white text-orange-600 hover:bg-gray-100'
              }`}
              onClick={handleRegister}
              disabled={
                registerMutation.isPending || cancelMutation.isPending
              }
            >
              {isRegistered && <CheckCircle2 size={20} />}
              {isRegistered ? 'Registered' : 'Register Now'}
            </Button>
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <Card className="p-8 border-border/60 shadow-sm">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Building className="text-accent-color" />
              Event Details
            </h2>

            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-orange-50">
                  <Calendar className="text-orange-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Date</h4>
                    <p className="text-muted-foreground">
                      {new Date(event.event_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50">
                  <Clock className="text-blue-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Time</h4>
                    <p className="text-muted-foreground">
                      {event.event_time}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-green-50">
                  <MapPin className="text-green-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Location</h4>
                    <p className="text-muted-foreground">{locationText}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-50">
                  <Users className="text-purple-600 mt-1" size={20} />
                  <div>
                    <h4 className="font-semibold text-sm">Organizer</h4>
                    <p className="text-muted-foreground">
                      {event.organizer}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-muted-foreground leading-relaxed">
              {event.description}
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              {event.tags?.map(tag => (
                <Badge key={tag}>#{tag}</Badge>
              ))}
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="p-6 border-border/60 shadow-sm sticky top-24">
            <h3 className="font-bold mb-4">Registration Status</h3>

            {isRegistered ? (
              <div className="text-center p-4 bg-green-100 rounded-xl mb-4">
                <CheckCircle2 className="mx-auto mb-2 text-green-600" />
                <p className="text-sm font-semibold">
                  You are registered
                </p>
              </div>
            ) : (
              <Button className="w-full mb-4" onClick={handleRegister}>
                Register Now
              </Button>
            )}

            <div className="space-y-3">
              <Button variant="outline" className="w-full" onClick={handleShare}>
                <Share2 size={16} /> Share
              </Button>

              {event.type === 'webinar' && (
                <Button variant="outline" className="w-full">
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