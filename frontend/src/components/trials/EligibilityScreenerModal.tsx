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
import { ShieldCheck, Cake, User, Stethoscope, CheckCircle2, XCircle, HelpCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../../contexts/ThemeContext';
import { trialService } from '../../services/trialService';
import type { EligibilityRules, ScreeningResult } from '../../types/db';

interface EligibilityScreenerModalProps {
    trialId: string;
    rules: EligibilityRules;
    onConnect: () => void;
    children: React.ReactNode;
}

const RESULT_COPY: Record<ScreeningResult['result'], { title: string; text: string }> = {
    eligible: {
        title: 'You may be eligible',
        text: 'Your answers match every criterion we could check. The trial team will confirm.',
    },
    possibly_eligible: {
        title: 'You might be eligible',
        text: 'Nothing rules you out, but some criteria were not answered. The trial team can tell you more.',
    },
    not_eligible: {
        title: 'You may not be eligible',
        text: 'At least one criterion does not match your answers. Talk to your doctor about other options.',
    },
};

function YesNo({ id, value, onChange }: { id: string; value: boolean | undefined; onChange: (v: boolean) => void }) {
    return (
        <div className="grid grid-cols-2 gap-2" role="group" aria-labelledby={id}>
            {[true, false].map((option) => (
                <Button
                    key={String(option)}
                    type="button"
                    variant={value === option ? 'default' : 'outline'}
                    aria-pressed={value === option}
                    onClick={() => onChange(option)}
                    className="cursor-pointer"
                >
                    {option ? 'Yes' : 'No'}
                </Button>
            ))}
        </div>
    );
}

export function EligibilityScreenerModal({ trialId, rules, onConnect, children }: EligibilityScreenerModalProps) {
    const [open, setOpen] = useState(false);
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    const [age, setAge] = useState('');
    const [gender, setGender] = useState('');
    const [conditions, setConditions] = useState('');
    const [inclusion, setInclusion] = useState<Record<string, boolean>>({});
    const [exclusion, setExclusion] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ScreeningResult | null>(null);

    const asksAge = rules.min_age != null || rules.max_age != null;
    const asksGender = !!rules.gender && rules.gender !== 'all';
    const asksConditions = (rules.conditions?.length ?? 0) > 0;
    const ageNumber = age === '' ? undefined : Number(age);
    const isAgeValid = ageNumber === undefined || (Number.isInteger(ageNumber) && ageNumber >= 0 && ageNumber <= 120);

    const reset = () => {
        setAge('');
        setGender('');
        setConditions('');
        setInclusion({});
        setExclusion({});
        setResult(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!isAgeValid) {
            toast.error('Invalid age', { description: 'Please enter an age between 0 and 120.' });
            return;
        }
        setLoading(true);
        try {
            setResult(await trialService.screenEligibility(trialId, {
                age: ageNumber,
                gender: gender || undefined,
                conditions: conditions.split(',').map((c) => c.trim()).filter(Boolean),
                inclusion_answers: inclusion,
                exclusion_answers: exclusion,
            }));
        } catch (err: any) {
            toast.error('Eligibility check failed', { description: err.message || 'Please try again.' });
        } finally {
            setLoading(false);
        }
    };

    const labelClass = `flex items-center gap-2 ${!isDark ? 'text-zinc-700' : 'text-zinc-300'}`;
    const statusIcon = {
        met: <CheckCircle2 size={16} className="text-success-color shrink-0" aria-label="Met" />,
        not_met: <XCircle size={16} className="text-red-500 shrink-0" aria-label="Not met" />,
        unknown: <HelpCircle size={16} className="text-muted-foreground shrink-0" aria-label="Not answered" />,
    };

    return (
        <Dialog open={open} onOpenChange={(next) => { setOpen(next); if (!next) reset(); }}>
            <DialogTrigger asChild>{children}</DialogTrigger>
            <DialogContent className={`sm:max-w-[500px] max-h-[90vh] overflow-y-auto border shadow-xl ${
                !isDark
                    ? 'bg-white text-zinc-950 border-zinc-200'
                    : 'bg-zinc-900 text-white border-zinc-800'
            }`}>
                <DialogHeader>
                    <div className="mx-auto bg-primary/10 p-3 rounded-full mb-2 text-primary">
                        <ShieldCheck size={28} />
                    </div>
                    <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>
                        {result ? RESULT_COPY[result.result].title : 'Check your eligibility'}
                    </DialogTitle>
                    <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-650' : 'text-zinc-350'}`}>
                        {result
                            ? RESULT_COPY[result.result].text
                            : 'Answer a few questions to see if this trial might be a fit. Your answers are not saved.'}
                    </DialogDescription>
                </DialogHeader>

                {result ? (
                    <div className="space-y-4 py-2">
                        <div className="text-center text-sm font-medium">
                            {result.score}% of criteria met
                        </div>
                        <ul className="space-y-2">
                            {result.breakdown.map((check) => (
                                <li key={check.criterion} className="flex items-start gap-3 p-3 rounded-xl border border-border bg-muted/30">
                                    {statusIcon[check.status]}
                                    <div>
                                        <div className="text-sm font-medium">{check.criterion}</div>
                                        <div className="text-xs text-muted-foreground">{check.detail}</div>
                                    </div>
                                </li>
                            ))}
                        </ul>
                        <p className="text-xs text-muted-foreground text-center">{result.disclaimer}</p>
                        <DialogFooter className="pt-2">
                            <Button type="button" variant="ghost" onClick={() => setResult(null)} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>
                                Change answers
                            </Button>
                            {result.result !== 'not_eligible' && (
                                <Button type="button" className="gap-2 shadow-md cursor-pointer" onClick={() => { setOpen(false); reset(); onConnect(); }}>
                                    Connect with Trial
                                </Button>
                            )}
                        </DialogFooter>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5 py-4">
                        {(asksAge || asksGender) && (
                            <div className="grid grid-cols-2 gap-4">
                                {asksAge && (
                                    <div className="space-y-2">
                                        <Label htmlFor="screen-age" className={labelClass}>
                                            <Cake size={14} /> Age
                                        </Label>
                                        <Input
                                            id="screen-age"
                                            type="number"
                                            min={0}
                                            max={120}
                                            inputMode="numeric"
                                            value={age}
                                            onChange={(e) => setAge(e.target.value)}
                                            placeholder="e.g. 35"
                                            aria-invalid={!isAgeValid}
                                            className="bg-muted/30 focus-visible:bg-background border-border"
                                        />
                                    </div>
                                )}
                                {asksGender && (
                                    <div className="space-y-2">
                                        <Label htmlFor="screen-gender" className={labelClass}>
                                            <User size={14} /> Gender
                                        </Label>
                                        <Select value={gender} onValueChange={setGender}>
                                            <SelectTrigger id="screen-gender" className="bg-muted/30 border-border">
                                                <SelectValue placeholder="Select" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="female">Female</SelectItem>
                                                <SelectItem value="male">Male</SelectItem>
                                                <SelectItem value="other">Other</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}
                            </div>
                        )}

                        {asksConditions && (
                            <div className="space-y-2">
                                <Label htmlFor="screen-conditions" className={labelClass}>
                                    <Stethoscope size={14} /> Your diagnosed conditions
                                </Label>
                                <Input
                                    id="screen-conditions"
                                    value={conditions}
                                    onChange={(e) => setConditions(e.target.value)}
                                    placeholder="e.g. Malaria, Diabetes"
                                    className="bg-muted/30 focus-visible:bg-background border-border"
                                />
                                <p className="text-xs text-muted-foreground">Separate several conditions with commas.</p>
                            </div>
                        )}

                        {(rules.inclusion_list ?? []).map((item, i) => (
                            <div key={`in-${item}`} className="space-y-2">
                                <Label id={`screen-in-${i}`} className={labelClass}>Does this apply to you: {item}?</Label>
                                <YesNo id={`screen-in-${i}`} value={inclusion[item]} onChange={(v) => setInclusion((p) => ({ ...p, [item]: v }))} />
                            </div>
                        ))}
                        {(rules.exclusion_list ?? []).map((item, i) => (
                            <div key={`ex-${item}`} className="space-y-2">
                                <Label id={`screen-ex-${i}`} className={labelClass}>Does this apply to you: {item}?</Label>
                                <YesNo id={`screen-ex-${i}`} value={exclusion[item]} onChange={(v) => setExclusion((p) => ({ ...p, [item]: v }))} />
                            </div>
                        ))}

                        <DialogFooter className="pt-2">
                            <Button type="button" variant="ghost" onClick={() => setOpen(false)} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
                            <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={loading || !isAgeValid}>
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck size={16} />}
                                Check eligibility
                            </Button>
                        </DialogFooter>
                    </form>
                )}
            </DialogContent>
        </Dialog>
    );
}
