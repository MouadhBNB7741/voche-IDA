import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Calendar,
  MapPin,
  Clock,
  Video,
  Users,
  Search,
  Filter,
  ArrowRight,
  Plus,
  Share2,
  CalendarPlus,
  Building,
  CheckCircle2
} from 'lucide-react';
import { Input } from '../../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { PageHeader } from '../../components/ui/PageHeader';
import { SuggestEventModal } from '../../components/events/SuggestEventModal';
import { useData } from '../../contexts/DataContext';
import { toast } from 'sonner';

export default function Events() {
  const navigate = useNavigate();
  const { state, actions } = useData();
  const [searchQuery, setSearchQuery] = useState('');
  const [eventType, setEventType] = useState('all');

  const filteredEvents = state.events.filter(event => {
    const matchesSearch = event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = eventType === 'all' || event.type === eventType;
    return matchesSearch && matchesType;
  });

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'webinar': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
      case 'conference': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
      case 'training': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
      case 'roundtable': return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const handleRegister = (e: React.MouseEvent, eventId: string, title: string) => {
    e.stopPropagation();
    if (state.registeredEvents.includes(eventId)) {
      actions.unregisterEvent(eventId);
      toast.info("Registration Cancelled", { description: "You are no longer registered." });
    } else {
      actions.registerEvent(eventId, title);
      toast.success("Registration Successful", { description: "You have been registered!" });
    }
  };

  const handleShare = (e: React.MouseEvent, title: string) => {
    e.stopPropagation();
    toast.success("Share Link Copied", { description: `Link for ${title} copied to clipboard` });
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
          {state.events.slice(0, 3).map(event => {
            const isRegistered = state.registeredEvents.includes(event.event_id);
            return (
              <Card
                key={event.event_id}
                className="group overflow-hidden cursor-pointer hover:shadow-xl transition-all duration-300 border-border/60"
                onClick={() => navigate(`/events/${event.event_id}`)}
              >
                <div className="h-32 bg-muted/50 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10"></div>
                  {/* Mock Image Placeholder */}
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
                  <h3 className="font-bold text-lg mb-2 line-clamp-2 group-hover:text-primary transition-colors">{event.title}</h3>
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
                      className={`flex-1 shadow-sm transition-all ${isRegistered ? "bg-green-600 hover:bg-green-700 text-white" : ""}`}
                      variant={isRegistered ? "default" : "default"}
                      onClick={(e) => handleRegister(e, event.event_id, event.title)}
                    >
                      {isRegistered ? (
                        <>
                          <CheckCircle2 size={16} className="mr-2" /> Registered
                        </>
                      ) : "Register Now"}
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={(e) => handleShare(e, event.title)}
                      className="text-muted-foreground hover:text-foreground hover:bg-muted"
                    >
                      <Share2 size={18} />
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* All Events List */}
      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-bold">All Upcoming Events</h2>
        <div className="space-y-4">
          {filteredEvents.map(event => {
            const isRegistered = state.registeredEvents.includes(event.event_id);
            return (
              <div
                key={event.event_id}
                className="flex flex-col md:flex-row gap-4 p-4 rounded-xl bg-card shadow-md hover:border-primary/20 transition-all cursor-pointer group"
                onClick={() => navigate(`/events/${event.event_id}`)}
              >
                <div className="flex-shrink-0 w-full md:w-48 bg-muted/30 rounded-lg flex flex-col items-center justify-center p-4">
                  <span className="text-2xl font-bold text-foreground">{new Date(event.event_date).getDate()}</span>
                  <span className="text-sm font-semibold text-muted-foreground uppercase">{new Date(event.event_date).toLocaleDateString('en-US', { month: 'short' })}</span>
                  <span className="text-xs text-muted-foreground mt-1">{new Date(event.event_date).getFullYear()}</span>
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
                    <h3 className="font-bold text-lg mb-1 group-hover:text-primary transition-colors">{event.title}</h3>
                    <p className="text-muted-foreground text-sm line-clamp-2">{event.description}</p>
                  </div>

                  <div className="flex items-center gap-4 mt-3 text-xs font-medium text-muted-foreground">
                    <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded">
                      <MapPin size={12} /> {event.location || (event.type === 'webinar' ? 'Online' : 'Global')}
                    </span>
                    <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-1 rounded">
                      <Users size={12} /> {event.participants} registered
                    </span>
                  </div>
                </div>

                <div className="flex flex-col justify-center gap-2 min-w-[140px]">
                  <Button
                    size="sm"
                    className={`w-full shadow-sm ${isRegistered ? "bg-green-600 hover:bg-green-700 text-white" : ""}`}
                    variant={isRegistered ? "default" : "outline"}
                    onClick={(e) => handleRegister(e, event.event_id, event.title)}
                  >
                    {isRegistered ? <><CheckCircle2 size={14} className="mr-2" /> Registered</> : "Register"}
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
            )
          })}
        </div>
      </div>

    </div>
  );
}