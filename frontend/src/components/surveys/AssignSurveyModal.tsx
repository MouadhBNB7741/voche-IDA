import { useState } from 'react';
import { Loader2, Send, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { useTheme } from '../../contexts/ThemeContext';
import { useAssignSurvey } from '../../hooks/useSurvey';

export function AssignSurveyModal({ survey, onClose }: { survey: { survey_id: string; title: string } | null; onClose: () => void }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const assign = useAssignSurvey();
  const [emails, setEmails] = useState('');
  const [dueDate, setDueDate] = useState('');

  const list = emails.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean);

  const close = () => {
    setEmails('');
    setDueDate('');
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!survey) return;
    assign.mutate(
      { surveyId: survey.survey_id, emails: list, dueDate: dueDate ? new Date(`${dueDate}T23:59:00`).toISOString() : undefined },
      {
        onSuccess: (res) => {
          const parts = [`${res.assigned.length} assigned`];
          if (res.already_assigned.length) parts.push(`${res.already_assigned.length} already assigned`);
          if (res.not_found.length) parts.push(`not found: ${res.not_found.join(', ')}`);
          toast.success('Survey Assigned', { description: parts.join(' · ') });
          close();
        },
      },
    );
  };

  return (
    <Dialog open={!!survey} onOpenChange={o => !o && close()}>
      <DialogContent className={`sm:max-w-[500px] border shadow-xl ${
        !isDark ? 'bg-white text-zinc-950 border-zinc-200' : 'bg-zinc-900 text-white border-zinc-800'}`}>
        <DialogHeader>
          <div className="mx-auto bg-[hsl(var(--primary)/0.1)] p-3 rounded-full mb-2 text-primary-color"><UserPlus size={24} /></div>
          <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>Assign Survey</DialogTitle>
          <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-600' : 'text-zinc-400'}`}>
            {survey?.title}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5 py-4">
          <div className="space-y-2">
            <Label htmlFor="assign-emails" className={!isDark ? 'text-zinc-700' : 'text-zinc-300'}>Patient emails</Label>
            <Textarea id="assign-emails" value={emails} onChange={e => setEmails(e.target.value)}
              placeholder="patient@example.com, another@example.com"
              className="border border-[hsl(var(--border))] resize-none border border-[hsl(var(--border))] min-h-[100px]" />
            <p className="text-xs text-muted-foreground">Separate emails with commas or new lines. Up to 100.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="assign-due" className={!isDark ? 'text-zinc-700' : 'text-zinc-300'}>Due date (optional)</Label>
            <Input id="assign-due" type="date" value={dueDate} min={new Date().toISOString().slice(0, 10)}
              onChange={e => setDueDate(e.target.value)} className="border border-[hsl(var(--border))]" />
          </div>
          <DialogFooter className="pt-2">
            <Button type="button" variant="ghost" onClick={close} className={`cursor-pointer ${!isDark ? 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}>Cancel</Button>
            <Button type="submit" className="gap-2 shadow-md cursor-pointer" disabled={list.length === 0 || list.length > 100 || assign.isPending}>
              {assign.isPending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              Assign
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
