import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Calendar, MapPin, Clock, Video, Users, Search, 
  ArrowRight, Plus, Share2, Building,
  CheckCircle2, Loader2,
} from 'lucide-react';
import { Input } from '../../components/ui/input';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '../../components/ui/select';
import { PageHeader } from '../../components/ui/PageHeader';
import { SuggestEventModal } from '../../components/events/SuggestEventModal';
import { toast } from 'sonner';
import { apiClient } from '../../lib/apiClient';
import { EVENTS } from '../../lib/api';
import type { Event } from '../../types/db';

const fetchEvents = async (): Promise<Event[]> => {
  const res = await apiClient.get(EVENTS.LIST);
  return res.data?.data ?? res.data;
};

const registerForEvent = async (id: string): Promise<void> => {
  await apiClient.post(EVENTS.REGISTER(id));
};

const cancelRegistration = async (id: string): Promise<void> => {
  await apiClient.delete(EVENTS.REGISTER(id));
};

export default function Events() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [eventType, setEventType] = useState('all');

  const { data: events = [], isLoading, isError } = useQuery({
    queryKey: ['events'],
    queryFn: fetchEvents,
    staleTime: 5 * 60 * 1000,
  });

  const registerMutation = useMutation({
    mutationFn: (id: string) => registerForEvent(id),
    onSuccess: (_, id) => {
      toast.success('Registration Successful', { description: 'You have been registered!' });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: () => toast.error('Registration failed. Please try again.'),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelRegistration(id),
    onSuccess: (_, id) => {
      toast.info('Registration Cancelled');
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: () => toast.error('Cancellation failed. Please try again.'),
  });

  const handleRegister = (e: React.MouseEvent, event: Event) => {
    e.stopPropagation();
    if (event.is_registered) {
      cancelMutation.mutate(event.event_id);
    } else {
      registerMutation.mutate(event.event_id);
    }
  };

  const handleShare = (e: React.MouseEvent, title: string) => {
    e.stopPropagation();
    toast.success('Share Link Copied', { description: `Link for ${title} copied to clipboard` });
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'webinar': return 'bg-blue-100 text-blue-700';
      case 'conference': return 'bg-purple-100 text-purple-700';
      case 'training': return 'bg-green-100 text-green-700';
      case 'roundtable': return 'bg-orange-100 text-orange-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const filteredEvents = events.filter(event => {
    const matchesSearch =
      event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (event.description || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = eventType === 'all' || event.type === eventType;
    return matchesSearch && matchesType;
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
          <p className="text-muted-foreground animate-pulse">Loading events...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-12 text-center max-w-md">
          <Calendar className="mx-auto mb-4 text-muted-foreground/30" size={48} />
          <h3 className="text-xl font-bold mb-2">Failed to load events</h3>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title="Global Events & Training"
        description="Join webinars, conferences, and training sessions from leading experts worldwide."
        badgeText={`${filteredEvents.length} Upcoming Events`}
        variant="green"
        action={
          <SuggestEventModal>
            <Button variant="hero" className="gap-2 font-semibold transition-transform hover:scale-105">
              <Plus size={20} className="stroke-[3px]" />
              Suggest Event
            </Button>
          </SuggestEventModal>
        }
      />

      {/* Search and Filter */}
      <Card className="p-6 border-border/60 shadow-sm">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search events..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-11"
            />
          </div>
          <div className="w-full md:w-48">
            <Select value={eventType} onValueChange={setEventType}>
              <SelectTrigger className="h-11">
                <SelectValue placeholder="Event Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="webinar">Webinars</SelectItem>
                <SelectItem value="conference">Conferences</SelectItem>
                <SelectItem value="training">Training</SelectItem>
                <SelectItem value="roundtable">Roundtables</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Featured Events */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Video className="text-accent" /> Featured Events
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.slice(0, 3).map(event => (
            <Card
              key={event.event_id}
              className="group overflow-hidden cursor-pointer hover:shadow-xl transition-all duration-300 border-border/60"
              onClick={() => navigate(`/events/${event.event_id}`)}
            >
              <div className="h-32 bg-muted/50 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10" />
                <div className="absolute inset-0 bg-accent/10 flex items-center justify-center">
                  <Calendar size={48} className="text-accent/20 group-hover:scale-110 transition-transform duration-500" />
                </div>
                <div className="absolute bottom-3 left-3 z-20">
                  <Badge className={`${getEventTypeColor(event.type)} border-0 font-bold`}>
                    {event.type.toUpperCase()}
                  </Badge>
                </div>
              </div>
              <div className="p-5">
                <h3 className="font-bold text-lg mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                  {event.title}
                </h3>
                <div className="space-y-2 text-sm text-muted-foreground mb-4">
                  <div className="flex items-center gap-2">
                    <Calendar size={14} className="text-accent" />
                    {new Date(event.event_date).toLocaleDateString()} • {event.event_time}
                  </div>
                  <div className="flex items-center gap-2">
                    <Building size={14} />
                    {event.organizer}
                  </div>
                  <div className="flex items-center gap-2">
                    <Users size={14} />
                    {event.participants} attending
                  </div>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button
                    className={`flex-1 shadow-sm transition-all ${event.is_registered ? 'bg-green-600 hover:bg-green-700 text-white' : ''}`}
                    onClick={(e) => handleRegister(e, event)}
                    disabled={registerMutation.isPending || cancelMutation.isPending}
                  >
                    {event.is_registered ? (
                      <><CheckCircle2 size={16} className="mr-2" /> Registered</>
                    ) : 'Register Now'}
                  </Button>
                  <Button variant="outline" size="icon" onClick={(e) => handleShare(e, event.title)}>
                    <Share2 size={18} />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* All Events List */}
      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-bold">All Upcoming Events</h2>
        <div className="space-y-4">
          {filteredEvents.map(event => (
            <div
              key={event.event_id}
              className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-card shadow-md hover:border-primary/20 transition-all cursor-pointer group"
              onClick={() => navigate(`/events/${event.event_id}`)}
            >
              <div className="flex-shrink-0 w-full md:w-48 bg-muted/30 rounded-lg flex flex-col items-center justify-center p-4">
                <span className="text-2xl font-bold text-foreground">
                  {new Date(event.event_date).getDate()}
                </span>
                <span className="text-sm font-semibold text-muted-foreground uppercase">
                  {new Date(event.event_date).toLocaleDateString('en-US', { month: 'short' })}
                </span>
                <span className="text-xs text-muted-foreground mt-1">
                  {new Date(event.event_date).getFullYear()}
                </span>
              </div>

              <div className="flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                      {event.type}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock size={12} /> {event.event_time}
                    </span>
                  </div>
                  <h3 className="font-bold text-lg mb-1 group-hover:text-primary transition-colors">
                    {event.title}
                  </h3>
                  <p className="text-muted-foreground text-sm line-clamp-2">
                    {event.description || 'No description available.'}
                  </p>
                </div>
                <div className="flex items-center gap-4 mt-3 text-xs font-medium text-muted-foreground">
                  <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded">
                    <MapPin size={12} /> {event.location || 'Online'}
                  </span>
                  <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded">
                    <Users size={12} /> {event.participants} registered
                  </span>
                </div>
              </div>

              <div className="flex flex-col justify-center gap-2 min-w-[140px]">
                <Button
                  size="sm"
                  className={`w-full shadow-sm ${event.is_registered ? 'bg-green-600 hover:bg-green-700 text-white' : ''}`}
                  variant={event.is_registered ? 'default' : 'outline'}
                  onClick={(e) => handleRegister(e, event)}
                  disabled={registerMutation.isPending || cancelMutation.isPending}
                >
                  {event.is_registered
                    ? <><CheckCircle2 size={14} className="mr-2" /> Registered</>
                    : 'Register'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-muted-foreground"
                  onClick={(e) => { e.stopPropagation(); navigate(`/events/${event.event_id}`); }}
                >
                  Details <ArrowRight size={14} className="ml-1" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Empty state */}
      {filteredEvents.length === 0 && (
        <Card className="p-16 text-center">
          <Calendar size={48} className="mx-auto mb-4 text-muted-foreground opacity-20" />
          <h3 className="text-lg font-bold mb-2">No events found</h3>
          <p className="text-sm text-muted-foreground">Try adjusting your search or filters.</p>
        </Card>
      )}
    </div>
  );
}