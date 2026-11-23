import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
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
import { Textarea } from '../ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../ui/select';
import { UserPlus, Mail, FlaskConical, AlignLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../../contexts/ThemeContext';
import { useTrials } from '../../hooks/useTrials';
import { trialService } from '../../services/trialService';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface ReferPatientModalProps {
    /** The trial to refer to. Without it, the HCP picks a recruiting trial in the dialog. */
    trialId?: string;
    children: React.ReactNode;
}

export function ReferPatientModal({ trialId, children }: ReferPatientModalProps) {
    const [open, setOpen] = useState(false);
    const { theme } = useTheme();
    const isDark = theme === 'dark';
    const queryClient = useQueryClient();

    const [selectedTrial, setSelectedTrial] = useState(trialId ?? '');
    const [email, setEmail] = useState('');
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(false);

    // Only fetched when the HCP has to pick a trial.
    const { data: trials = [] } = useTrials({ status: 'Recruiting', limit: 100 }, open && !trialId);

    const isFormValid = !!selectedTrial && EMAIL_PATTERN.test(email.trim());

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!isFormValid) {
            toast.error('Missing Information', { description: 'Choose a trial and enter the patient\'s email.' });
            return;
        }
        setLoading(true);
        try {
            const referral = await trialService.referPatient(selectedTrial, email.trim(), notes.trim());
            toast.success('Referral Sent', {
                description: referral.patient_user_id
                    ? `${referral.patient_name} has been notified.`
                    : 'We emailed the patient an invitation to join Voche and view the trial.',
            });
            queryClient.invalidateQueries({ queryKey: ['referrals', 'sent'] });
            setOpen(false);
            setSelectedTrial(trialId ?? '');
            setEmail('');
            setNotes('');
        } catch (err: any) {
            toast.error('Could not send referral', { description: err.message || 'Please try again.' });
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
                    <div className="mx-auto bg-primary/10 p-3 rounded-full mb-2 text-primary">
                        <UserPlus size={28} />
                    </div>
                    <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>Refer a Patient</DialogTitle>
                    <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-650' : 'text-zinc-350'}`}>
                        Your patient gets a notification and an email. Patients without an account are invited to join.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-5 py-4">
                    {!trialId && (
                        <div className="space-y-2">
                            <Label htmlFor="refer-trial" className={labelClass}>
                                <FlaskConical size={14} /> Trial
                            </Label>
                            <Select value={selectedTrial} onValueChange={setSelectedTrial}>
                                <SelectTrigger id="refer-trial" className="bg-muted/30 border-border">
                                    <SelectValue placeholder="Choose a recruiting trial" />
                                </SelectTrigger>
                                <SelectContent>
                                    {trials.map((t) => (
                                        <SelectItem key={t.trial_id} value={t.trial_id}>{t.title}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                    <div className="space-y-2">
                        <Label htmlFor="refer-email" className={labelClass}>
                            <Mail size={14} /> Patient email
                        </Label>
                        <Input
                            id="refer-email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="patient@example.com"
                            className="bg-muted/30 focus-visible:bg-background border-border"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="refer-notes" className={labelClass}>
                            <AlignLeft size={14} /> Clinical notes (optional)
                        </Label>
                        <Textarea
                            id="refer-notes"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            maxLength={2000}
                            placeholder="Why this trial may suit the patient..."
                            className="resize-none bg-muted/30 focus-visible:bg-background border-border min-h-[100px]"
                        />
                    </div>
                    <DialogFooter className="pt-2">
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
                        <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={!isFormValid || loading}>
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus size={16} />}
                            Send Referral
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
