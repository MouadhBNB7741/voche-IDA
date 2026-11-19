import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import Cookies from 'universal-cookie';
import { ArrowRight, Building2, HeartHandshake, Loader2, Stethoscope, User } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { InterestSelector } from '../../components/profile/InterestSelector';
import { LicenceVerification } from '../../components/profile/LicenceVerification';
import { useAuth } from '../../contexts/AuthContext';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import userService from '../../services/userService';
import type { OnboardingDetails } from '../../services/userService';
import type { UserType } from '../../types/db';
import { dashboardPathFor } from '../../utils/dashboard';
import idaLogo from '../../assets/ida.webp';

const roles: { value: UserType; label: string; description: string; icon: typeof User }[] = [
  { value: 'patient', label: 'Patient / Participant', description: 'Find trials, resources and support.', icon: User },
  { value: 'caregiver', label: 'Caregiver', description: 'Support someone in your care.', icon: HeartHandshake },
  { value: 'hcp', label: 'Healthcare Professional', description: 'Verify your license and share your expertise.', icon: Stethoscope },
  { value: 'org_member', label: 'Organization Member', description: 'Represent your organization on VOCHE.', icon: Building2 },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isLoading } = useAuth();
  const { handleError } = useErrorHandler();

  const [selectedRole, setSelectedRole] = useState<UserType | null>(null);
  const [roleConfirmed, setRoleConfirmed] = useState(false);
  const [interests, setInterests] = useState<string[]>([]);
  const [location, setLocation] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  if (!user) {
    if (!isLoading && !new Cookies().get('voche_token')) {
      return <Navigate to="/login" replace />;
    }
    return (
      <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Loading">
        <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
      </div>
    );
  }

  if (user.onboarding_completed_at && !isSaving) {
    return <Navigate to={dashboardPathFor(user.user_type)} replace />;
  }

  const needsRole = !user.user_type;
  const role = user.user_type ?? selectedRole;
  const showRoleStep = needsRole && !roleConfirmed;
  const totalSteps = needsRole ? 2 : 1;
  const currentStep = showRoleStep ? 1 : totalSteps;

  const finish = async (details: OnboardingDetails = {}) => {
    try {
      setIsSaving(true);
      await userService.completeOnboarding({ ...(needsRole && role ? { user_type: role } : {}), ...details });
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      toast.success('Welcome to VOCHE!');
      navigate(dashboardPathFor(role), { replace: true });
    } catch (error) {
      handleError(error, 'Could not save your details. Please try again.');
      setIsSaving(false);
    }
  };

  const finishWithDetails = () => {
    const trimmedLocation = location.trim();
    finish({
      ...(interests.length ? { interests } : {}),
      ...(trimmedLocation ? { location: trimmedLocation } : {}),
    });
  };

  return (
    <div className="min-h-screen bg-background px-4 py-8 md:py-12 animate-in fade-in duration-500">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <img src={idaLogo} alt="" className="w-8 h-8 object-contain rounded-lg" />
            <span className="font-bold text-xl tracking-tight">VOCHE</span>
          </div>
          <span className="text-sm text-muted-foreground">Step {currentStep} of {totalSteps}</span>
        </div>

        <Card className="p-6 md:p-8 border-border/60 shadow-sm">
          {showRoleStep ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">How will you use VOCHE?</h1>
                <p className="text-muted-foreground mt-1">Choose the role that describes you best.</p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3" role="radiogroup" aria-label="Your role">
                {roles.map((option) => {
                  const Icon = option.icon;
                  const isSelected = selectedRole === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      onClick={() => setSelectedRole(option.value)}
                      className={`text-left rounded-xl border p-4 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-primary-color bg-primary-color/10 ring-1 ring-primary-color/40'
                          : 'border-border hover:border-primary-color/60 hover:bg-muted/50'
                      }`}
                    >
                      <Icon size={20} className={isSelected ? 'text-primary-color' : 'text-muted-foreground'} />
                      <span className="block font-semibold mt-2">{option.label}</span>
                      <span className="block text-sm text-muted-foreground mt-0.5">{option.description}</span>
                    </button>
                  );
                })}
              </div>
              <div className="flex justify-end">
                <Button onClick={() => setRoleConfirmed(true)} disabled={!selectedRole} className="gap-2">
                  Continue
                  <ArrowRight size={16} />
                </Button>
              </div>
            </div>
          ) : role === 'hcp' ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Verify your medical license</h1>
                <p className="text-muted-foreground mt-1">
                  Verified professionals get access to clinical tools. You can also do this later from your dashboard.
                </p>
              </div>
              <LicenceVerification submitLabel="Submit and finish" onSubmitted={() => finish()} />
              <div className="flex justify-end border-t pt-4">
                <Button variant="ghost" onClick={() => finish()} disabled={isSaving}>
                  I'll do this later
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Personalize your experience</h1>
                <p className="text-muted-foreground mt-1">
                  Tell us what matters to you. You can change this anytime from your dashboard.
                </p>
              </div>
              <InterestSelector selectedInterests={interests} onChange={setInterests} isEditing />
              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Lagos, Nigeria"
                  autoComplete="address-level2"
                  maxLength={255}
                  className="bg-muted/30"
                />
                <p className="text-xs text-muted-foreground">Used to show you trials and events near you.</p>
              </div>
              <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
                <Button variant="ghost" onClick={() => finish()} disabled={isSaving}>
                  Skip for now
                </Button>
                <Button onClick={finishWithDetails} disabled={isSaving} className="gap-2">
                  {isSaving && <Loader2 size={16} className="animate-spin" />}
                  Finish
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
