import { useState } from 'react';
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
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { BellPlus, Stethoscope, MapPin, FlaskConical, Clock, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../../contexts/ThemeContext';
import { trialService } from '../../services/trialService';
import type { AlertFrequency, TrialPhase } from '../../types/db';

const PHASES: TrialPhase[] = ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Post-Market'];
const FREQUENCIES: { value: AlertFrequency; label: string }[] = [
    { value: 'instant', label: 'Instantly (in-app and email)' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
];
const ANY = 'any';

export function TrialAlertModal({ children }: { children: React.ReactNode }) {
    const [open, setOpen] = useState(false);
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    const [condition, setCondition] = useState('');
    const [location, setLocation] = useState('');
    const [phase, setPhase] = useState<string>(ANY);
    const [frequency, setFrequency] = useState<AlertFrequency>('weekly');
    const [loading, setLoading] = useState(false);

    // An alert with no criteria would match every trial, so ask for at least one.
    const isFormValid = condition.trim() !== '' || location.trim() !== '' || phase !== ANY;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!isFormValid) {
            toast.error('Missing Information', { description: 'Choose at least a condition, location or phase.' });
            return;
        }
        setLoading(true);
        try {
            await trialService.createAlert({
                disease_area: condition.trim() || undefined,
                location: location.trim() || undefined,
                phase: phase === ANY ? undefined : (phase as TrialPhase),
                alert_frequency: frequency,
            });
            toast.success('Trial Alert Created', {
                description: "We'll let you know when a matching trial opens.",
            });
            setOpen(false);
            setCondition('');
            setLocation('');
            setPhase(ANY);
            setFrequency('weekly');
        } catch (err: any) {
            toast.error('Could not create alert', { description: err.message || 'Please try again.' });
        } finally {
            setLoading(false);
        }
    };

    const labelClass = `flex items-center gap-2 ${!isDark ? 'text-zinc-700' : 'text-zinc-300'}`;

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>{children}</DialogTrigger>
            <DialogContent className={`sm:max-w-[500px] border shadow-xl ${
                !isDark
                    ? 'bg-white text-zinc-950 border-zinc-200'
                    : 'bg-zinc-900 text-white border-zinc-800'
            }`}>
                <DialogHeader>
                    <div className="mx-auto bg-[hsl(var(--primary)/0.1)] p-3 rounded-full mb-2 text-primary-color">
                        <BellPlus size={28} />
                    </div>
                    <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>Create Trial Alert</DialogTitle>
                    <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-650' : 'text-zinc-350'}`}>
                        Get notified when a new trial matching your interests starts recruiting.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-5 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="alert-condition" className={labelClass}>
                            <Stethoscope size={14} /> Condition
                        </Label>
                        <Input
                            id="alert-condition"
                            value={condition}
                            onChange={(e) => setCondition(e.target.value)}
                            placeholder="e.g. HIV, Malaria, Tuberculosis"
                            className="bg-muted/30 focus-visible:bg-background border-border"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="alert-location" className={labelClass}>
                                <MapPin size={14} /> Location
                            </Label>
                            <Input
                                id="alert-location"
                                value={location}
                                onChange={(e) => setLocation(e.target.value)}
                                placeholder="Country or city"
                                className="bg-muted/30 focus-visible:bg-background border-border"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="alert-phase" className={labelClass}>
                                <FlaskConical size={14} /> Phase
                            </Label>
                            <Select value={phase} onValueChange={setPhase}>
                                <SelectTrigger id="alert-phase" className="bg-muted/30 border-border">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={ANY}>Any phase</SelectItem>
                                    {PHASES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="alert-frequency" className={labelClass}>
                            <Clock size={14} /> How often
                        </Label>
                        <Select value={frequency} onValueChange={(v) => setFrequency(v as AlertFrequency)}>
                            <SelectTrigger id="alert-frequency" className="bg-muted/30 border-border">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {FREQUENCIES.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter className="pt-2">
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
                        <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={!isFormValid || loading}>
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <BellPlus size={16} />}
                            Create Alert
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
