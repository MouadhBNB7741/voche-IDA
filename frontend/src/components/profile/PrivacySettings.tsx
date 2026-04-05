import { Switch } from '../ui/switch';
import { Card } from '../ui/card';
import { useSettings } from '../../contexts/SettingsContext';

export function PrivacySettings() {
    const { privacy, updatePrivacy } = useSettings();

    const handleToggle = (key: keyof typeof privacy) => {
        updatePrivacy({ [key]: !privacy[key] });
    };

    const items = [
        { key: 'profileVisible', label: 'Public Profile', desc: 'Allow others to see your basic profile information.' },
        { key: 'showLocation', label: 'Show Location', desc: 'Display your city/country on your public profile.' },
        { key: 'showOrganization', label: 'Show Organization', desc: 'Display your organization affiliation.' },
        { key: 'allowMessages', label: 'Allow Direct Messages', desc: 'Allow other verified users to send you messages.' },
        { key: 'shareActivity', label: 'Share Activity', desc: 'Show your saved trials and event attendance on your profile.' },
    ] as const;

    return (
        <Card className="voce-card">
            <div className="mb-6">
                <h3 className="text-lg font-semibold mb-1">Privacy Settings</h3>
                <p className="text-sm text-muted-foreground">Control your visibility and data sharing preferences.</p>
            </div>
            <div className="space-y-6">
                {items.map((item) => (
                    <div key={item.key} className="flex items-start justify-between">
                        <div className="space-y-0.5">
                            <div className="font-medium">{item.label}</div>
                            <div className="text-sm text-muted-foreground">{item.desc}</div>
                        </div>
                        <Switch
                            checked={privacy[item.key]}
                            onCheckedChange={() => handleToggle(item.key)}
                        />
                    </div>
                ))}
            </div>
        </Card>
    );
}
