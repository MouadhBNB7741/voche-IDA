import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
import { Checkbox } from '../ui/checkbox';
import { FileSignature, PenLine, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../../contexts/ThemeContext';
import { trialService } from '../../services/trialService';

interface DigitalConsentModalProps {
    referralId: string;
    children: React.ReactNode;
}

export function DigitalConsentModal({ referralId, children }: DigitalConsentModalProps) {
    const [open, setOpen] = useState(false);
    const { theme } = useTheme();
    const isDark = theme === 'dark';
    const queryClient = useQueryClient();

    const [agreed, setAgreed] = useState(false);
    const [signedName, setSignedName] = useState('');
    const [loading, setLoading] = useState(false);

    const { data: form, isLoading, error } = useQuery({
        queryKey: ['referrals', referralId, 'consent'],
        queryFn: () => trialService.getConsentForm(referralId),
        enabled: open,
    });

    const isFormValid = agreed && signedName.trim().length >= 2;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form || !isFormValid) {
            toast.error('Missing Information', { description: 'Tick the box and type your full name to sign.' });
            return;
        }
        setLoading(true);
        try {
            await trialService.signConsent(referralId, form.version, signedName.trim());
            toast.success('Consent Signed', {
                description: 'The trial team will contact you about the next steps.',
            });
            queryClient.invalidateQueries({ queryKey: ['referrals'] });
            setOpen(false);
            setAgreed(false);
            setSignedName('');
        } catch (err: any) {
            toast.error('Could not sign consent', { description: err.message || 'Please try again.' });
            // e.g. the consent text changed while the dialog was open
            queryClient.invalidateQueries({ queryKey: ['referrals', referralId, 'consent'] });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>{children}</DialogTrigger>
            <DialogContent className={`sm:max-w-[560px] max-h-[90vh] overflow-y-auto border shadow-xl ${
                !isDark
                    ? 'bg-white text-zinc-950 border-zinc-200'
                    : 'bg-zinc-900 text-white border-zinc-800'
            }`}>
                <DialogHeader>
                    <div className="mx-auto bg-primary/10 p-3 rounded-full mb-2 text-primary">
                        <FileSignature size={28} />
                    </div>
                    <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>Digital Consent</DialogTitle>
                    <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-650' : 'text-zinc-350'}`}>
                        {form ? form.trial_title : 'Read the consent carefully before you sign.'}
                    </DialogDescription>
                </DialogHeader>

                {isLoading ? (
                    <div className="py-10 flex justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary-color" /></div>
                ) : error || !form ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">Could not load the consent form. Please try again.</p>
                ) : form.signed_at ? (
                    <div className="space-y-4 py-4">
                        <div className="whitespace-pre-line text-sm p-4 rounded-xl border border-border bg-muted/30">{form.text}</div>
                        <p className="text-sm text-center">
                            Signed by <strong>{form.signed_name}</strong> on {new Date(form.signed_at).toLocaleDateString()} (version {form.version}).
                        </p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5 py-4">
                        <div
                            className="whitespace-pre-line text-sm p-4 rounded-xl border border-border bg-muted/30 max-h-60 overflow-y-auto"
                            tabIndex={0}
                            aria-label="Consent text"
                        >
                            {form.text}
                        </div>
                        <div className="flex items-start gap-3">
                            <Checkbox id="consent-agree" checked={agreed} onCheckedChange={(v) => setAgreed(v === true)} className="mt-0.5" />
                            <Label htmlFor="consent-agree" className="text-sm leading-snug cursor-pointer">
                                I have read and understood this consent, and I agree to it.
                            </Label>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="consent-name" className={`flex items-center gap-2 ${!isDark ? 'text-zinc-700' : 'text-zinc-300'}`}>
                                <PenLine size={14} /> Type your full name to sign
                            </Label>
                            <Input
                                id="consent-name"
                                value={signedName}
                                onChange={(e) => setSignedName(e.target.value)}
                                maxLength={200}
                                autoComplete="name"
                                className="bg-muted/30 focus-visible:bg-background border-border"
                            />
                        </div>
                        <DialogFooter className="pt-2">
                            <Button type="button" variant="ghost" onClick={() => setOpen(false)} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
                            <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={!isFormValid || loading}>
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSignature size={16} />}
                                Sign Consent
                            </Button>
                        </DialogFooter>
                    </form>
                )}
            </DialogContent>
        </Dialog>
    );
}
