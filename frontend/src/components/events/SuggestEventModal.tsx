import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '../ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Plus, Calendar, Building, AlignLeft, Type, Clock, MapPin, Link2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuthContext } from '../../contexts/AuthContext';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { eventService } from '../../services/eventService';
import type { EventType } from '../../types/db';

const EVENT_TYPES: { value: EventType; label: string }[] = [
    { value: 'webinar', label: 'Webinar' },
    { value: 'conference', label: 'Conference' },
    { value: 'training', label: 'Training' },
    { value: 'roundtable', label: 'Roundtable' },
];

const EMPTY = {
    title: '',
    type: 'webinar' as EventType,
    organizer: '',
    date: '',
    time: '',
    format: 'online' as 'online' | 'in_person',
    link: '',
    location: '',
    description: '',
};

function today(): string {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function SuggestEventModal({ children }: { children?: React.ReactNode }) {
    const [open, setOpen] = useState(false);
    const { theme } = useTheme();
    const isDark = theme === 'dark';
    const { user } = useAuthContext();
    const { handleError } = useErrorHandler();
    const queryClient = useQueryClient();
    const isAdmin = user?.user_type === 'admin';

    const [formData, setFormData] = useState(EMPTY);
    const set = (field: keyof typeof EMPTY) => (value: string) => setFormData(prev => ({ ...prev, [field]: value }));

    const link = formData.link.trim();
    const linkError = formData.format === 'online' && link && !/^https?:\/\//i.test(link)
        ? 'The link must start with https://'
        : null;
    const placeOk = formData.format === 'online' ? !!link && !linkError : formData.location.trim().length > 1;
    const isFormValid = formData.title.trim().length >= 5
        && formData.organizer.trim().length >= 2
        && !!formData.date && formData.date >= today()
        && !!formData.time
        && placeOk
        && formData.description.trim().length >= 20;

    const suggest = useMutation({
        mutationFn: () => eventService.suggest({
            title: formData.title.trim(),
            type: formData.type,
            organizer: formData.organizer.trim(),
            event_date: formData.date,
            event_time: formData.time,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
            description: formData.description.trim(),
            ...(formData.format === 'online'
                ? { virtual_link: link, location: 'Online' }
                : { location: formData.location.trim() }),
        }),
        onSuccess: (event) => {
            queryClient.invalidateQueries({ queryKey: ['events'] });
            if (event.approval_status === 'approved') {
                toast.success('Event published', { description: 'It is now listed in Events.' });
            } else {
                toast.success('Event suggested', {
                    description: "An admin will review it. We'll notify you when it's published.",
                    duration: 7000,
                });
            }
            setOpen(false);
            setFormData(EMPTY);
        },
        onError: (err) => handleError(err, 'Could not send your suggestion. Please try again.'),
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!isFormValid || suggest.isPending) return;
        suggest.mutate();
    };

    const labelClass = `flex items-center gap-2 ${!isDark ? 'text-zinc-700' : 'text-zinc-300'}`;
    const fieldClass = 'bg-muted/30 focus-visible:bg-background border-border';
    const menuClass = `border opacity-100 ${!isDark ? 'bg-white border-zinc-200 text-zinc-950' : 'bg-zinc-900 border-zinc-800 text-white'}`;
    const optionClass = !isDark
        ? 'text-zinc-900 hover:bg-zinc-100 focus:bg-zinc-100 focus:text-zinc-900'
        : 'text-white hover:bg-zinc-800 focus:bg-zinc-800 focus:text-white';

    return (
        <Dialog open={open} onOpenChange={(next) => { if (!suggest.isPending) setOpen(next); }}>
            <DialogTrigger asChild>
                {children || (
                    <Button className="gap-2">
                        <Plus size={16} />
                        Suggest Event
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className={`sm:max-w-[540px] max-h-[90vh] overflow-y-auto border shadow-xl ${
                !isDark
                    ? "bg-white text-zinc-950 border-zinc-200"
                    : "bg-zinc-900 text-white border-zinc-800"
            }`}>
                <DialogHeader>
                    <div className="mx-auto bg-primary/10 p-3 rounded-full mb-2 text-primary">
                        <Calendar size={28} />
                    </div>
                    <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>Suggest an Event</DialogTitle>
                    <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-650' : 'text-zinc-350'}`}>
                        {isAdmin
                            ? 'As an admin, your event is published straight away.'
                            : 'Know of an upcoming conference, webinar, or workshop? An admin reviews every suggestion before it is listed.'}
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label htmlFor="title" className={labelClass}>
                            <Type size={14} /> Event Title
                        </Label>
                        <Input
                            id="title"
                            value={formData.title}
                            onChange={(e) => set('title')(e.target.value)}
                            maxLength={500}
                            placeholder="e.g. Annual Global Health Summit"
                            className={fieldClass}
                        />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="event-type" className={labelClass}>Type</Label>
                            <Select value={formData.type} onValueChange={set('type')}>
                                <SelectTrigger id="event-type" className={`w-full ${fieldClass}`}><SelectValue /></SelectTrigger>
                                <SelectContent className={menuClass}>
                                    {EVENT_TYPES.map(t => (
                                        <SelectItem key={t.value} value={t.value} className={`cursor-pointer ${optionClass}`}>{t.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="organizer" className={labelClass}>
                                <Building size={14} /> Organizer
                            </Label>
                            <Input
                                id="organizer"
                                value={formData.organizer}
                                onChange={(e) => set('organizer')(e.target.value)}
                                maxLength={255}
                                placeholder="Organization name"
                                className={fieldClass}
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="date" className={labelClass}>
                                <Calendar size={14} /> Date
                            </Label>
                            <Input
                                id="date"
                                type="date"
                                min={today()}
                                value={formData.date}
                                onChange={(e) => set('date')(e.target.value)}
                                className={fieldClass}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="time" className={labelClass}>
                                <Clock size={14} /> Time
                            </Label>
                            <Input
                                id="time"
                                type="time"
                                value={formData.time}
                                onChange={(e) => set('time')(e.target.value)}
                                className={fieldClass}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <span className={labelClass}>Where</span>
                        <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Where the event takes place">
                            {(['online', 'in_person'] as const).map(format => (
                                <button
                                    key={format}
                                    type="button"
                                    role="radio"
                                    aria-checked={formData.format === format}
                                    onClick={() => set('format')(format)}
                                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${
                                        formData.format === format
                                            ? 'border-primary-color bg-primary-color/10 text-primary-color'
                                            : 'border-border hover:bg-muted/50'
                                    }`}
                                >
                                    {format === 'online' ? 'Online' : 'In person'}
                                </button>
                            ))}
                        </div>
                        {formData.format === 'online' ? (
                            <div className="space-y-1">
                                <Label htmlFor="link" className="sr-only">Online link</Label>
                                <div className="relative">
                                    <Link2 size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        id="link"
                                        type="url"
                                        value={formData.link}
                                        onChange={(e) => set('link')(e.target.value)}
                                        placeholder="https://..."
                                        className={`pl-9 ${fieldClass}`}
                                    />
                                </div>
                                {linkError && <p className="text-xs text-red-500" role="alert">{linkError}</p>}
                            </div>
                        ) : (
                            <div className="relative">
                                <Label htmlFor="location" className="sr-only">Location</Label>
                                <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    id="location"
                                    value={formData.location}
                                    onChange={(e) => set('location')(e.target.value)}
                                    maxLength={255}
                                    placeholder="City, venue"
                                    className={`pl-9 ${fieldClass}`}
                                />
                            </div>
                        )}
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="description" className={labelClass}>
                            <AlignLeft size={14} /> Description
                        </Label>
                        <Textarea
                            id="description"
                            value={formData.description}
                            onChange={(e) => set('description')(e.target.value)}
                            maxLength={5000}
                            placeholder="What is the event about, and who is it for?"
                            className={`resize-none min-h-[100px] ${fieldClass}`}
                        />
                        {formData.description && formData.description.trim().length < 20 && (
                            <p className="text-xs text-muted-foreground">At least 20 characters.</p>
                        )}
                    </div>
                    <DialogFooter className="pt-2">
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} disabled={suggest.isPending} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
                        <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={!isFormValid || suggest.isPending}>
                            {suggest.isPending ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                            {isAdmin ? 'Publish Event' : 'Submit Suggestion'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
