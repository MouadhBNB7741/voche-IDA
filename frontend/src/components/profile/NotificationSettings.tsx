import { Switch } from '../ui/switch';
import { Card } from '../ui/card';
import { useSettings } from '../../contexts/SettingsContext';

export function NotificationSettings() {
    const { notifications, updateNotifications } = useSettings();

    const handleToggle = (key: keyof typeof notifications) => {
        updateNotifications({ [key]: !notifications[key] });
    };

    const items = [
        { key: 'newTrials', label: 'New Trials', desc: 'Get notified when new trials match your interests.' },
        { key: 'forumReplies', label: 'Forum Replies', desc: 'Receive notifications when someone replies to your posts.' },
        { key: 'eventReminders', label: 'Event Reminders', desc: 'Get reminders for upcoming events you are attending.' },
        { key: 'weeklyDigest', label: 'Weekly Digest', desc: 'A weekly summary of top trials and community news.' },
        { key: 'researchUpdates', label: 'Research Updates', desc: 'Stay updated on the latest research findings.' },
        { key: 'communityNews', label: 'Community News', desc: 'News and stories from the Voche community.' },
    ] as const;

    return (
        <Card className="voce-card">
            <div className="mb-6">
                <h3 className="text-lg font-semibold mb-1">Notification Preferences</h3>
                <p className="text-sm text-muted-foreground">Manage how and when you want to be notified.</p>
            </div>
            <div className="space-y-6">
                {items.map((item) => (
                    <div key={item.key} className="flex items-start justify-between">
                        <div className="space-y-0.5">
                            <div className="font-medium">{item.label}</div>
                            <div className="text-sm text-muted-foreground">{item.desc}</div>
                        </div>
                        <Switch
                            checked={notifications[item.key]}
                            onCheckedChange={() => handleToggle(item.key)}
                        />
                    </div>
                ))}
            </div>
        </Card>
    );
}
