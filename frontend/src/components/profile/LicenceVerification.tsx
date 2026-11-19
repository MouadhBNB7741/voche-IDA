import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Clock, FileText, Loader2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Skeleton } from '../ui/skeleton';
import { doctorService } from '../../services/doctorService';
import type { DoctorVerification } from '../../services/doctorService';
import { useErrorHandler } from '../../hooks/useErrorHandler';

const QUERY_KEY = ['doctor-verification'];
const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 5 * 1024 * 1024;

const emptyForm = {
  specialization: '',
  license_number: '',
  institution: '',
  country: '',
  issuing_region: '',
  expiration_date: '',
};

const fields = [
  { key: 'specialization', label: 'Specialization', placeholder: 'e.g. Cardiology', autoComplete: 'off' },
  { key: 'license_number', label: 'Medical license number', placeholder: 'e.g. MD-12345', autoComplete: 'off' },
  { key: 'institution', label: 'Institution', placeholder: 'e.g. General Hospital', autoComplete: 'organization' },
  { key: 'country', label: 'Country', placeholder: 'e.g. Nigeria', autoComplete: 'country-name' },
  { key: 'issuing_region', label: 'Issuing region', placeholder: 'e.g. Lagos', autoComplete: 'off' },
] as const;

interface LicenceVerificationProps {
  submitLabel?: string;
  onSubmitted?: (verification: DoctorVerification) => void;
}

function VerificationStatus({ verification }: { verification: DoctorVerification }) {
  const { handleError } = useErrorHandler();
  const approved = verification.status === 'approved';
  const Icon = approved ? CheckCircle2 : Clock;

  const openDocument = async () => {
    try {
      await doctorService.openDocument(verification.verification_id);
    } catch (error) {
      handleError(error, 'Could not open your document. Please try again.');
    }
  };

  return (
    <div className={`rounded-xl border p-5 ${approved ? 'border-success/40 bg-success/5' : 'border-amber-500/40 bg-amber-500/5'}`}>
      <p className="font-bold flex items-center gap-2">
        <Icon size={18} className={approved ? 'text-success' : 'text-amber-600'} />
        {approved ? 'Your license is verified' : 'Your license is under review'}
      </p>
      <p className="text-sm text-muted-foreground mt-1">
        License {verification.license_number}, {verification.institution}
        {approved ? '.' : '. We will let you know once an admin has reviewed it.'}
      </p>
      {verification.has_document && (
        <Button type="button" variant="outline" size="sm" className="mt-4 gap-2" onClick={openDocument}>
          <FileText size={16} />
          View uploaded document
        </Button>
      )}
    </div>
  );
}

/**
 * Shows the doctor's verification status, or the form to submit their licence.
 */
export function LicenceVerification({ submitLabel = 'Submit for review', onSubmitted }: LicenceVerificationProps) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const [form, setForm] = useState(emptyForm);
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: verification, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: doctorService.getMine,
  });

  const today = new Date().toISOString().split('T')[0];
  const isComplete = Object.values(form).every((value) => value.trim()) && !!file;

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    e.target.value = '';
    if (!selected) return;
    if (!ALLOWED_TYPES.includes(selected.type)) {
      toast.error('Invalid file type', { description: 'Please upload a PDF, JPG, PNG or WEBP file.' });
      return;
    }
    if (selected.size > MAX_SIZE) {
      toast.error('File too large', { description: 'Your document must be 5 MB or smaller.' });
      return;
    }
    setFile(selected);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!isComplete || !file) return;

    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, value.trim()));
    data.append('file', file);

    try {
      setIsSubmitting(true);
      const submitted = await doctorService.submit(data);
      queryClient.setQueryData(QUERY_KEY, submitted);
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      toast.success('License submitted', { description: 'An admin will review your document.' });
      setForm(emptyForm);
      setFile(null);
      onSubmitted?.(submitted);
    } catch (error) {
      handleError(error, 'Could not submit your license. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <Skeleton className="h-40 w-full" />;
  }

  if (verification && verification.status !== 'rejected') {
    return <VerificationStatus verification={verification} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {verification?.status === 'rejected' && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm flex gap-2">
          <AlertCircle size={18} className="text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Your last submission was not approved</p>
            {verification.rejection_reason && (
              <p className="text-muted-foreground mt-1">{verification.rejection_reason}</p>
            )}
            <p className="text-muted-foreground mt-1">Please check your details and submit again.</p>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {fields.map((field) => (
          <div key={field.key} className="space-y-2">
            <Label htmlFor={field.key}>{field.label}</Label>
            <Input
              id={field.key}
              value={form[field.key]}
              onChange={(e) => setForm((prev) => ({ ...prev, [field.key]: e.target.value }))}
              placeholder={field.placeholder}
              autoComplete={field.autoComplete}
              maxLength={100}
              required
              className="bg-muted/30"
            />
          </div>
        ))}
        <div className="space-y-2">
          <Label htmlFor="expiration_date">Expiry date</Label>
          <Input
            id="expiration_date"
            type="date"
            min={today}
            value={form.expiration_date}
            onChange={(e) => setForm((prev) => ({ ...prev, expiration_date: e.target.value }))}
            required
            className="bg-muted/30"
          />
        </div>
      </div>

      <label className="block border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary-color hover:bg-primary-color/5 focus-within:border-primary-color focus-within:ring-2 focus-within:ring-primary-color/30 transition-all duration-300">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp"
          onChange={handleFileChange}
          className="sr-only"
        />
        <Upload className="mx-auto mb-3 text-muted-foreground" size={28} />
        {file ? (
          <>
            <span className="font-bold flex items-center justify-center gap-2 break-all">
              <FileText size={16} className="shrink-0" />
              {file.name}
            </span>
            <span className="block text-xs text-muted-foreground mt-1">Click to choose a different file</span>
          </>
        ) : (
          <>
            <span className="block font-bold mb-1">Click to upload your license</span>
            <span className="block text-xs text-muted-foreground">PDF, JPG, PNG or WEBP, up to 5 MB. Only admins can see it.</span>
          </>
        )}
      </label>

      <Button type="submit" className="w-full sm:w-auto gap-2" disabled={!isComplete || isSubmitting}>
        {isSubmitting && <Loader2 size={16} className="animate-spin" />}
        {isSubmitting ? 'Submitting...' : submitLabel}
      </Button>
    </form>
  );
}
