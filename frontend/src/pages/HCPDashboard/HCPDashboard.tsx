import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import {
  User,
  Edit,
  Save,
  FileText,
  Lock,
  Shield,
  ChevronRight,
  Palette,
  Stethoscope,
  Camera,
  Loader2,
  X,
  Bell,
  Star,
  UserPlus,
  Send,
  FlaskConical,
  NotebookPen
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { ReferPatientModal } from '../../components/trials/ReferPatientModal';
import { ManagedTrialsPanel } from '../../components/trials/ManagedTrialsPanel';
import { ObservationsPanel } from '../../components/trials/ObservationsPanel';
import { ReferralStatusBadge } from '../../components/trials/ReferralStatusBadge';
import { trialService } from '../../services/trialService';
import { formatMessageDate } from '../../utils/date';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';

import { InterestSelector } from '../../components/profile/InterestSelector';
import { DesignSettings } from '../../components/profile/DesignSettings';
import { PrivacySettings } from '../../components/profile/PrivacySettings';
import { DangerZone } from '../../components/profile/DangerZone';
import { NotificationSettings } from '../../components/profile/NotificationSettings';
import { LicenceVerification } from '../../components/profile/LicenceVerification';
import { PageHeader } from '../../components/ui/PageHeader';
import { useAvatarUpload } from '../../hooks/useAvatarUpload';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { languages, toLanguageCode } from '../../utils/languages';
import { roleLabelFor } from '../../utils/dashboard';
import userService from '../../services/userService';
import { apiClient } from '../../lib/apiClient';
import { SYSTEM } from '../../lib/api';

export default function HCPDashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isAuthenticated } = useAuth();
  const { handleError } = useErrorHandler();
  const { isAvatarLoading, handleAvatarUpload, handleAvatarDelete } = useAvatarUpload();

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [profileImage, setProfileImage] = useState<string | null>(null);

  // Sync profile image from backend
  useEffect(() => {
    if (user?.avatar) {
      if (user.avatar.startsWith('http')) {
        setProfileImage(user.avatar);
      } else {
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const cleanBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
        const cleanAvatarPath = user.avatar.startsWith('/') ? user.avatar : `/${user.avatar}`;
        setProfileImage(`${cleanBaseUrl}${cleanAvatarPath}`);
      }
    } else {
      setProfileImage(null);
    }
  }, [user]);

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    location: '',
    language: 'en',
    bio: '',
    interests: [] as string[],
  });

  // Sync form data when user data loads, without overwriting changes being typed
  useEffect(() => {
    if (user && !isEditing) {
      setFormData({
        name: user.display_name || '',
        email: user.email || '',
        location: user.location || '',
        language: toLanguageCode(user.language_preference),
        bio: user.bio || '',
        interests: (user.interests as string[]) || [],
      });
    }
  }, [user, isEditing]);

  // Doctor feedback
  const [feedbackData, setFeedbackData] = useState({
    category: '',
    rating: 0,
    message: '',
  });
  const [isSendingFeedback, setIsSendingFeedback] = useState(false);

  const isFeedbackValid =
    !!feedbackData.category && feedbackData.rating > 0 && feedbackData.message.trim().length >= 10;

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await userService.updateProfile({
        display_name: formData.name.trim(),
        location: formData.location.trim(),
        language_preference: formData.language,
        bio: formData.bio,
        interests: formData.interests,
      });
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      setIsEditing(false);
      toast.success('Profile Updated', {
        description: 'Your changes have been saved successfully.'
      });
    } catch (error) {
      handleError(error, 'Could not save your changes. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!isFeedbackValid) return;
    try {
      setIsSendingFeedback(true);
      await apiClient.post(SYSTEM.FEEDBACK, {
        category: feedbackData.category,
        rating: feedbackData.rating,
        message: feedbackData.message.trim(),
      });
      toast.success('Feedback Submitted', { description: 'Thank you for your feedback!' });
      setFeedbackData({ category: '', rating: 0, message: '' });
    } catch (error) {
      handleError(error, 'Could not send your feedback. Please try again.');
    } finally {
      setIsSendingFeedback(false);
    }
  };

  const isDoctor = user?.user_type === 'hcp';
  const isVerifiedDoctor = isDoctor && !!user?.is_verified;

  const { data: referrals = [], isLoading: referralsLoading } = useQuery({
    queryKey: ['referrals', 'sent'],
    queryFn: trialService.getSentReferrals,
    enabled: isVerifiedDoctor && activeTab === 'referrals',
  });

  const verificationRequired = (what: string) => (
    <Card className="p-16 text-center border-dashed bg-muted/20">
      <Shield className="mx-auto mb-4 text-muted-foreground/30" size={48} />
      <h4 className="font-bold text-lg mb-2">Verification Required</h4>
      <p className="text-muted-foreground mb-6 max-w-sm mx-auto">{what} is available once your medical license is verified.</p>
      <Button onClick={() => setActiveTab('doctor')} className="cursor-pointer">Go to License Verification</Button>
    </Card>
  );

  const tabs = [
    { id: 'profile', label: 'Profile Settings', icon: User },
    { id: 'design', label: 'Design & Appearance', icon: Palette },
    ...(isDoctor ? [{ id: 'doctor', label: 'Doctor Tools', icon: Stethoscope }] : []),
    ...(isDoctor ? [{ id: 'mytrials', label: 'My Trials', icon: FlaskConical }] : []),
    ...(isDoctor ? [{ id: 'referrals', label: 'Patient Referrals', icon: Send }] : []),
    ...(isDoctor ? [{ id: 'observations', label: 'Observations', icon: NotebookPen }] : []),
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Security', icon: Shield },
    { id: 'danger', label: 'Danger Zone', icon: Lock, variant: 'destructive' }
  ];

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto p-4 max-w-2xl mt-20 animate-in fade-in duration-500">
        <Card className="p-12 text-center shadow-lg border-border/80">
          <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mx-auto mb-6">
            <User className="text-muted-foreground" size={40} />
          </div>
          <h2 className="text-2xl font-bold mb-3">Login Required</h2>
          <p className="text-muted-foreground mb-8 max-w-sm mx-auto">
            Please log in or register to access your profile, saved trials, and personalized settings.
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg" onClick={() => navigate('/login')} className="px-8">Login</Button>
            <Button size="lg" variant="outline" onClick={() => navigate('/signup')} className="px-8">Register</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-7xl space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title={formData.name}
        description={formData.bio}
        badgeText={roleLabelFor(user?.user_type)}
        variant="green"
        className="mb-0"
        action={
          <div className="relative group">
            <div className="w-24 h-24 md:w-32 md:h-32 rounded-full border-4 border-white/20 shadow-xl overflow-hidden bg-white/10 flex items-center justify-center backdrop-blur-sm">
              {profileImage ? (
                <img src={profileImage} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={48} className="text-white/80" />
              )}
            </div>

            {profileImage && (
              <button
                type="button"
                onClick={handleAvatarDelete}
                className="absolute -top-1 -right-1 p-1.5 bg-white text-red-600 rounded-full cursor-pointer transition-all shadow-xl border-2 border-white z-20 hover:scale-110 flex items-center justify-center"
                title="Delete Photo"
                aria-label="Delete photo"
              >
                <X size={18} className="stroke-[3]" />
              </button>
            )}

            <div className="absolute bottom-0 right-0">
              <label className="p-2.5 bg-primary-color hover:bg-primary-color/90 text-white rounded-full cursor-pointer transition-all shadow-xl border-2 border-background flex items-center justify-center z-20 hover:scale-110 relative" title="Upload Photo">
                {isAvatarLoading ? <Loader2 size={16} className="animate-spin" /> : <Camera size={16} />}
                <input
                  type="file"
                  className="sr-only"
                  accept="image/png,image/jpeg,image/webp"
                  aria-label="Upload photo"
                  onChange={handleAvatarUpload}
                  disabled={isAvatarLoading}
                />
              </label>
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-4 gap-8 mt-10">
        {/* Sidebar Navigation */}
        <nav className="space-y-2 lg:sticky lg:top-24 h-fit">
          <Card className="p-2 border-border/60 shadow-sm overflow-hidden">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-lg transition-all duration-200 text-left font-medium text-sm
                    ${isActive
                      ? 'bg-primary-color/10 text-primary-color shadow-sm ring-1 ring-primary/20'
                      : tab.variant === 'destructive'
                        ? 'text-destructive hover:bg-destructive/10'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }
                  `}
                >
                  <Icon size={18} className={isActive ? "text-primary-color" : "opacity-70"} />
                  {tab.label}
                  {isActive && <ChevronRight size={14} className="ml-auto text-primary-color opacity-50" />}
                </button>
              );
            })}
          </Card>
        </nav>

        {/* Content Area */}
        <div className="lg:col-span-3 space-y-6">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-between items-center bg-card p-4 rounded-xl border shadow-sm">
                <div>
                  <h2 className="text-lg font-bold">Personal Information</h2>
                  <p className="text-sm text-muted-foreground">Manage your personal details and public profile.</p>
                </div>
                <Button
                  variant={isEditing ? "default" : "outline"}
                  size="sm"
                  onClick={() => isEditing ? handleSave() : setIsEditing(true)}
                  className="gap-2"
                  disabled={isSaving || (isEditing && !formData.name.trim())}
                >
                  {isEditing ? <Save size={16} /> : <Edit size={16} />}
                  {isEditing ? 'Save Changes' : 'Edit Profile'}
                </Button>
              </div>

              <Card className="p-6 border-border/60 shadow-sm">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      disabled={!isEditing}
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      readOnly
                      disabled
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Location</Label>
                    <Input
                      id="location"
                      value={formData.location}
                      onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                      disabled={!isEditing}
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="Language">Preferred Language</Label>
                    <Select
                      value={formData.language}
                      onValueChange={(value) => setFormData(prev => ({ ...prev, language: value }))}
                      disabled={!isEditing}
                    >
                      <SelectTrigger className="bg-muted/30">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {languages.map(lang => (
                          <SelectItem key={lang.code} value={lang.code}>
                            {lang.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="mt-6 space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio}
                    onChange={(e) => setFormData(prev => ({ ...prev, bio: e.target.value }))}
                    disabled={!isEditing}
                    rows={4}
                    className="resize-none bg-muted/30"
                    placeholder="Tell us a little about yourself..."
                  />
                </div>
              </Card>

              <Card className="p-6 border-border/60 shadow-sm">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold">Interests & Focus Areas</h3>
                  <p className="text-sm text-muted-foreground">Select topics you are interested in to personalize your experience.</p>
                </div>
                <InterestSelector
                  selectedInterests={formData.interests}
                  onChange={(interests) => setFormData(prev => ({ ...prev, interests }))}
                  isEditing={isEditing}
                />
              </Card>
            </div>
          )}

          {/* Doctor Tools Tab */}
          {activeTab === 'doctor' && isDoctor && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <Card className="p-6 border-border/60 shadow-sm">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <FileText size={18} className="text-primary-color" />
                  License Verification
                </h3>
                <p className="text-muted-foreground mb-6 text-sm">
                  Submit your medical license for verification. Verified HCPs get access to exclusive patient recruitment tools.
                </p>
                <LicenceVerification />
              </Card>

              <Card className="p-6 border-border/60 shadow-sm">
                <h3 className="text-lg font-bold mb-4">Submit Clinical Feedback</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select
                      value={feedbackData.category}
                      onValueChange={(value) => setFeedbackData(prev => ({ ...prev, category: value }))}
                    >
                      <SelectTrigger className="bg-muted/30">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="trial">Clinical Trial Protocol</SelectItem>
                        <SelectItem value="platform">Platform Usability</SelectItem>
                        <SelectItem value="patient">Patient Eligibility</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label id="feedback-rating">Rating</Label>
                    <div className="flex gap-1" role="radiogroup" aria-labelledby="feedback-rating">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          type="button"
                          role="radio"
                          aria-checked={feedbackData.rating === value}
                          aria-label={`${value} out of 5`}
                          onClick={() => setFeedbackData(prev => ({ ...prev, rating: value }))}
                          className="p-1 cursor-pointer rounded-md hover:bg-muted transition-colors"
                        >
                          <Star
                            size={22}
                            className={value <= feedbackData.rating ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground'}
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Message</Label>
                    <Textarea
                      value={feedbackData.message}
                      onChange={(e) => setFeedbackData(prev => ({ ...prev, message: e.target.value }))}
                      rows={5}
                      placeholder="Share your detailed feedback (at least 10 characters)..."
                      maxLength={5000}
                      className="bg-muted/30 resize-none"
                    />
                  </div>
                  <Button onClick={handleFeedbackSubmit} className="w-full sm:w-auto" disabled={!isFeedbackValid || isSendingFeedback}>
                    {isSendingFeedback ? 'Sending...' : 'Submit Feedback'}
                  </Button>
                </div>
              </Card>
            </div>
          )}
          {/* Referrals Tab */}
          {activeTab === 'referrals' && isDoctor && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-between items-center gap-4 bg-card p-4 rounded-xl border shadow-sm">
                <div>
                  <h2 className="text-lg font-bold">Patient Referrals</h2>
                  <p className="text-sm text-muted-foreground">Patients you referred to trials, and where each one stands.</p>
                </div>
                {isVerifiedDoctor && (
                  <ReferPatientModal>
                    <Button size="sm" className="gap-2 cursor-pointer">
                      <UserPlus size={16} />
                      Refer a Patient
                    </Button>
                  </ReferPatientModal>
                )}
              </div>

              {!isVerifiedDoctor ? (
                <Card className="p-16 text-center border-dashed bg-muted/20">
                  <Shield className="mx-auto mb-4 text-muted-foreground/30" size={48} />
                  <h4 className="font-bold text-lg mb-2">Verification Required</h4>
                  <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                    Referring patients is available once your medical license is verified.
                  </p>
                  <Button onClick={() => setActiveTab('doctor')} className="cursor-pointer">Go to License Verification</Button>
                </Card>
              ) : referralsLoading ? (
                <div className="py-16 flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary-color" /></div>
              ) : referrals.length === 0 ? (
                <Card className="p-16 text-center border-dashed bg-muted/20">
                  <Send className="mx-auto mb-4 text-muted-foreground/30" size={48} />
                  <h4 className="font-bold text-lg mb-2">No Referrals Yet</h4>
                  <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                    Refer a patient to a recruiting trial and follow their progress here.
                  </p>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {referrals.map((r) => (
                    <Card key={r.id} className="p-5 hover:border-primary-color/50 hover:shadow-md transition-all">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h4
                            className="font-bold mb-1 hover:text-primary-color transition-colors cursor-pointer"
                            onClick={() => navigate(`/trials/${r.trial_id}`)}
                          >
                            {r.trial_title}
                          </h4>
                          <p className="text-sm text-muted-foreground break-words">
                            {r.patient_name}{r.patient_name !== r.patient_email && r.patient_email ? ` · ${r.patient_email}` : ''}
                          </p>
                          {r.clinical_notes && <p className="text-sm mt-2 line-clamp-2">{r.clinical_notes}</p>}
                          <p className="text-xs text-muted-foreground mt-2">Sent {formatMessageDate(r.created_at)}</p>
                        </div>
                        <ReferralStatusBadge status={r.status} />
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'mytrials' && isDoctor && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="bg-card p-4 rounded-xl border shadow-sm">
                <h2 className="text-lg font-bold">My Trials</h2>
                <p className="text-sm text-muted-foreground">Trials an administrator assigned to you. Move each one through its lifecycle.</p>
              </div>
              {isVerifiedDoctor ? <ManagedTrialsPanel /> : verificationRequired('Managing trials')}
            </div>
          )}

          {activeTab === 'observations' && isDoctor && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="bg-card p-4 rounded-xl border shadow-sm">
                <h2 className="text-lg font-bold">Clinical Observations</h2>
                <p className="text-sm text-muted-foreground">Log observations on your trials and see recent ones from your team.</p>
              </div>
              {isVerifiedDoctor ? <ObservationsPanel /> : verificationRequired('Logging observations')}
            </div>
          )}

          {/* Design Tab */}
          {activeTab === 'design' && (
            <DesignSettings />
          )}

          {activeTab === 'notifications' && (
            <NotificationSettings />
          )}

          {activeTab === 'privacy' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <PrivacySettings />
            </div>
          )}

          {activeTab === 'danger' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <DangerZone />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
