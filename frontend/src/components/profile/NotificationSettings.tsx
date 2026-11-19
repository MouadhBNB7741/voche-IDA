import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Skeleton } from '../ui/skeleton';
import { Switch } from '../ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { notificationService } from '../../services/notificationService';
import type { NotificationPreferences } from '../../services/notificationService';

const QUERY_KEY = ['notification-preferences'];

const channels = [
    { key: 'emailAlerts', label: 'Email alerts', desc: 'Receive notifications by email.' },
    { key: 'pushNotifications', label: 'Push notifications', desc: 'Receive notifications in your browser.' },
] as const;

const notificationTypes = [
    { key: 'trial_match', label: 'Trial matches', desc: 'New trials that match your interests.' },
    { key: 'trial_alert', label: 'Trial alerts', desc: 'Updates from the trial alerts you created.' },
    { key: 'community_reply', label: 'Community replies', desc: 'Someone replies to your posts or comments.' },
    { key: 'community_like', label: 'Community likes', desc: 'Someone likes your posts or comments.' },
    { key: 'event_reminder', label: 'Event reminders', desc: 'Reminders for events you registered for.' },
    { key: 'event_update', label: 'Event updates', desc: 'Changes to events you registered for.' },
    { key: 'org_request_update', label: 'Organization requests', desc: 'Decisions on your requests to join a group.' },
    { key: 'resource_update', label: 'Resource updates', desc: 'New or updated learning resources.' },
    { key: 'survey_available', label: 'Surveys', desc: 'New surveys you can take part in.' },
    { key: 'system_announcement', label: 'Announcements', desc: 'Important news about the platform.' },
] as const;

export function NotificationSettings() {
    const queryClient = useQueryClient();

    const { data: prefs, isLoading, isError, refetch } = useQuery({
        queryKey: QUERY_KEY,
        queryFn: notificationService.getPreferences,
    });

    const mutation = useMutation({
        mutationFn: notificationService.updatePreferences,
        onMutate: async (change: Partial<NotificationPreferences>) => {
            await queryClient.cancelQueries({ queryKey: QUERY_KEY });
            const previous = queryClient.getQueryData<NotificationPreferences>(QUERY_KEY);
            if (previous) {
                queryClient.setQueryData<NotificationPreferences>(QUERY_KEY, {
                    ...previous,
                    ...change,
                    notificationTypes: { ...previous.notificationTypes, ...change.notificationTypes },
                });
            }
            return { previous };
        },
        onSuccess: (updated) => {
            queryClient.setQueryData(QUERY_KEY, updated);
            toast.success('Preferences saved');
        },
        onError: (_error, _change, context) => {
            queryClient.setQueryData(QUERY_KEY, context?.previous);
            toast.error('Could not save your preferences. Please try again.');
        },
    });

    if (isLoading) {
        return (
            <Card className="p-6 border-border/60 shadow-sm space-y-4">
                <Skeleton className="h-6 w-56" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
            </Card>
        );
    }

    if (isError || !prefs) {
        return (
            <Card className="p-6 border-border/60 shadow-sm text-center space-y-4">
                <p className="text-sm text-muted-foreground">Your notification preferences could not be loaded.</p>
                <Button variant="outline" onClick={() => refetch()}>Try again</Button>
            </Card>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Card className="p-6 border-border/60 shadow-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-1">Notification Preferences</h3>
                    <p className="text-sm text-muted-foreground">Choose how and how often we contact you.</p>
                </div>
                <div className="space-y-6">
                    {channels.map((channel) => (
                        <div key={channel.key} className="flex items-start justify-between gap-4">
                            <div className="space-y-0.5">
                                <Label htmlFor={channel.key} className="font-medium">{channel.label}</Label>
                                <p className="text-sm text-muted-foreground">{channel.desc}</p>
                            </div>
                            <Switch
                                id={channel.key}
                                checked={!!prefs[channel.key]}
                                onCheckedChange={(value) => mutation.mutate({ [channel.key]: value })}
                            />
                        </div>
                    ))}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-0.5">
                            <Label htmlFor="frequency" className="font-medium">Frequency</Label>
                            <p className="text-sm text-muted-foreground">How often we send your notifications.</p>
                        </div>
                        <Select
                            value={prefs.frequency || 'instant'}
                            onValueChange={(value) => mutation.mutate({ frequency: value as NotificationPreferences['frequency'] })}
                        >
                            <SelectTrigger id="frequency" className="w-full sm:w-44 bg-muted/30">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="instant">Instant</SelectItem>
                                <SelectItem value="daily">Daily</SelectItem>
                                <SelectItem value="weekly">Weekly</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </Card>

            <Card className="p-6 border-border/60 shadow-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-1">What to notify me about</h3>
                    <p className="text-sm text-muted-foreground">Turn off the topics you do not want to hear about.</p>
                </div>
                <div className="space-y-6">
                    {notificationTypes.map((type) => (
                        <div key={type.key} className="flex items-start justify-between gap-4">
                            <div className="space-y-0.5">
                                <Label htmlFor={type.key} className="font-medium">{type.label}</Label>
                                <p className="text-sm text-muted-foreground">{type.desc}</p>
                            </div>
                            <Switch
                                id={type.key}
                                checked={prefs.notificationTypes?.[type.key] ?? true}
                                onCheckedChange={(value) => mutation.mutate({ notificationTypes: { [type.key]: value } })}
                            />
                        </div>
                    ))}
                </div>
            </Card>
        </div>
    );
}
