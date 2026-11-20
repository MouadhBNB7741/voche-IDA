import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileUp, Link2, Loader2, Upload, X } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuthContext } from '../../contexts/AuthContext';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { resourceService } from '../../services/resourceService';
import { languages } from '../../utils/languages';
import type { ResourceType } from '../../types/db';

const MB = 1024 * 1024;
// Same limits as the backend (Mouadh's answer Q37)
const FILE_RULES: Record<string, { label: string; max: number }> = {
  'application/pdf': { label: 'PDF', max: 5 * MB },
  'video/mp4': { label: 'MP4 video', max: 20 * MB },
  'video/webm': { label: 'WebM video', max: 20 * MB },
};

const TYPES: { value: ResourceType; label: string; accepts: string }[] = [
  { value: 'document', label: 'Document', accepts: 'application/pdf' },
  { value: 'toolkit', label: 'Toolkit', accepts: 'application/pdf' },
  { value: 'video', label: 'Video', accepts: 'video/mp4,video/webm' },
  { value: 'course', label: 'Course', accepts: 'application/pdf,video/mp4,video/webm' },
];

interface SubmitResourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categories: string[];
}

const EMPTY = {
  title: '',
  description: '',
  type: 'document' as ResourceType,
  category: '',
  language: 'en',
  url: '',
  tags: '',
};

/**
 * Share an educational resource: a PDF or video file, a link, or both.
 * Admins' resources are published at once; others wait for an admin's approval.
 */
export function SubmitResourceModal({ open, onOpenChange, categories }: SubmitResourceModalProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { user } = useAuthContext();
  const { handleError } = useErrorHandler();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState(EMPTY);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const typeInfo = TYPES.find((t) => t.value === form.type) ?? TYPES[0];
  const set = (field: keyof typeof EMPTY) => (value: string) => setForm((prev) => ({ ...prev, [field]: value }));

  const reset = () => {
    setForm(EMPTY);
    setFile(null);
    setFileError(null);
  };

  const checkFile = (candidate: File | null, type: ResourceType = form.type): string | null => {
    if (!candidate) return null;
    const rule = FILE_RULES[candidate.type];
    const allowed = (TYPES.find((t) => t.value === type)?.accepts ?? '').split(',');
    if (!rule || !allowed.includes(candidate.type)) {
      return type === 'video' ? 'Choose an MP4 or WebM video.' : `Choose a ${type === 'course' ? 'PDF or video' : 'PDF'} file.`;
    }
    if (candidate.size > rule.max) {
      const extra = rule.max > 5 * MB ? ' For longer videos, add a YouTube or Vimeo link instead.' : '';
      return `${rule.label} files can be at most ${rule.max / MB} MB.${extra}`;
    }
    return null;
  };

  const onFileChosen = (candidate: File | null) => {
    setFile(candidate);
    setFileError(checkFile(candidate));
  };

  const onTypeChange = (value: string) => {
    const type = value as ResourceType;
    setForm((prev) => ({ ...prev, type }));
    setFileError(checkFile(file, type));
  };

  const link = form.url.trim();
  const linkError = link && !/^https?:\/\//i.test(link) ? 'The link must start with https://' : null;
  const titleOk = form.title.trim().length >= 5;
  const descriptionOk = form.description.trim().length >= 20;
  const canSend = titleOk && descriptionOk && !!form.category && (!!file || !!link) && !fileError && !linkError;

  const submit = useMutation({
    mutationFn: () => {
      const data = new FormData();
      data.append('title', form.title.trim());
      data.append('description', form.description.trim());
      data.append('type', form.type);
      data.append('category', form.category);
      data.append('language', form.language);
      if (link) data.append('url', link);
      if (form.tags.trim()) data.append('tags', form.tags);
      if (file) data.append('file', file);
      return resourceService.submit(data);
    },
    onSuccess: (resource) => {
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      queryClient.invalidateQueries({ queryKey: ['resources', 'mine'] });
      if (resource.approval_status === 'approved') {
        toast.success('Resource published', { description: 'It is now in the Resources hub.' });
      } else {
        toast.success('Resource sent for review', {
          description: "An admin will check it. We'll notify you when it's published.",
          duration: 7000,
        });
      }
      reset();
      onOpenChange(false);
    },
    onError: (err) => handleError(err, 'Could not share the resource. Please try again.'),
  });

  const fieldClass = isDark ? 'bg-zinc-950 border-zinc-800' : 'bg-white border-zinc-200';
  const labelClass = isDark ? 'text-zinc-300' : 'text-zinc-700';
  const optionClass = isDark
    ? 'text-white hover:bg-zinc-800 focus:bg-zinc-800 focus:text-white'
    : 'text-zinc-900 hover:bg-zinc-100 focus:bg-zinc-100 focus:text-zinc-900';
  const menuClass = `border opacity-100 ${isDark ? 'bg-zinc-900 border-zinc-800 text-white' : 'bg-white border-zinc-200 text-zinc-950'}`;

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!submit.isPending) onOpenChange(next); }}>
      <DialogContent className={`sm:max-w-[560px] max-h-[90vh] overflow-y-auto border shadow-xl ${
        isDark ? 'bg-zinc-900 text-white border-zinc-800' : 'bg-white text-zinc-950 border-zinc-200'
      }`}>
        <DialogHeader>
          <DialogTitle className={isDark ? 'text-white' : 'text-zinc-950'}>Share a resource</DialogTitle>
          <DialogDescription className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
            {user?.user_type === 'admin'
              ? 'As an admin, your resource is published straight away.'
              : 'An admin reviews every resource before it appears in the hub.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="resource-title" className={labelClass}>Title</Label>
            <Input
              id="resource-title"
              value={form.title}
              onChange={(e) => set('title')(e.target.value)}
              maxLength={500}
              placeholder="e.g. Understanding clinical trial phases"
              className={fieldClass}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="resource-type" className={labelClass}>Type</Label>
              <Select value={form.type} onValueChange={onTypeChange}>
                <SelectTrigger id="resource-type" className={`w-full ${fieldClass}`}><SelectValue /></SelectTrigger>
                <SelectContent className={menuClass}>
                  {TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value} className={`cursor-pointer ${optionClass}`}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="resource-category" className={labelClass}>Category</Label>
              <Select value={form.category} onValueChange={set('category')}>
                <SelectTrigger id="resource-category" className={`w-full ${fieldClass}`}>
                  <SelectValue placeholder="Choose" />
                </SelectTrigger>
                <SelectContent className={menuClass}>
                  {categories.map((c) => (
                    <SelectItem key={c} value={c} className={`cursor-pointer ${optionClass}`}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="resource-language" className={labelClass}>Language</Label>
              <Select value={form.language} onValueChange={set('language')}>
                <SelectTrigger id="resource-language" className={`w-full ${fieldClass}`}><SelectValue /></SelectTrigger>
                <SelectContent className={menuClass}>
                  {languages.map((l) => (
                    <SelectItem key={l.code} value={l.code} className={`cursor-pointer ${optionClass}`}>{l.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="resource-description" className={labelClass}>Description</Label>
            <Textarea
              id="resource-description"
              value={form.description}
              onChange={(e) => set('description')(e.target.value)}
              maxLength={5000}
              rows={4}
              placeholder="What is it about, and who is it for?"
              className={`resize-none ${fieldClass}`}
            />
            {form.description && !descriptionOk && (
              <p className="text-xs text-muted-foreground">At least 20 characters.</p>
            )}
          </div>

          <div className="space-y-2">
            <Label className={labelClass}>File</Label>
            <input
              ref={fileInput}
              type="file"
              accept={typeInfo.accepts}
              className="sr-only"
              aria-label="Choose a file to upload"
              onChange={(e) => onFileChosen(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <div className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${fieldClass}`}>
                <FileUp size={18} className="shrink-0 text-primary-color" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{(file.size / MB).toFixed(1)} MB</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 cursor-pointer"
                  aria-label="Remove the file"
                  onClick={() => { onFileChosen(null); if (fileInput.current) fileInput.current.value = ''; }}
                >
                  <X size={16} />
                </Button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                className={`flex w-full flex-col items-center gap-1 rounded-lg border border-dashed px-4 py-5 text-sm transition-colors cursor-pointer ${
                  isDark ? 'border-zinc-700 hover:bg-zinc-800/60' : 'border-zinc-300 hover:bg-zinc-50'
                }`}
              >
                <Upload size={20} className="text-muted-foreground" />
                <span className="font-medium">Choose a file</span>
                <span className="text-xs text-muted-foreground">
                  {form.type === 'video'
                    ? 'MP4 or WebM, up to 20 MB'
                    : form.type === 'course'
                      ? 'PDF up to 5 MB, or MP4/WebM up to 20 MB'
                      : 'PDF, up to 5 MB'}
                </span>
              </button>
            )}
            {fileError && <p className="text-xs text-red-500" role="alert">{fileError}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="resource-url" className={`flex items-center gap-1.5 ${labelClass}`}>
              <Link2 size={14} /> Link <span className="font-normal text-muted-foreground">(optional with a file)</span>
            </Label>
            <Input
              id="resource-url"
              type="url"
              value={form.url}
              onChange={(e) => set('url')(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className={fieldClass}
            />
            {linkError && <p className="text-xs text-red-500" role="alert">{linkError}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="resource-tags" className={labelClass}>
              Tags <span className="font-normal text-muted-foreground">(optional, separated by commas)</span>
            </Label>
            <Input
              id="resource-tags"
              value={form.tags}
              onChange={(e) => set('tags')(e.target.value)}
              maxLength={500}
              placeholder="trials, oncology, patients"
              className={fieldClass}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submit.isPending}
            className={`cursor-pointer ${isDark ? 'border-zinc-800 hover:bg-zinc-800 text-white' : 'border-zinc-200 hover:bg-zinc-50 text-zinc-900'}`}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => submit.mutate()}
            disabled={!canSend || submit.isPending}
            className="gap-2 cursor-pointer"
          >
            {submit.isPending && <Loader2 size={16} className="animate-spin" />}
            {submit.isPending ? 'Sending...' : user?.user_type === 'admin' ? 'Publish' : 'Send for review'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default SubmitResourceModal;
