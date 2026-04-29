import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import {
  User,
  Bell,
  MapPin,
  Edit,
  Save,
  Camera,
  Heart,
  FileText,
  Lock,
  Shield,
  ChevronRight,
  Trash2,
  Palette,
  Loader2,
  X
} from 'lucide-react';
import { DesignSettings } from '../../components/profile/DesignSettings';
import { useAuth } from '../../contexts/AuthContext';
import { useData } from '../../contexts/DataContext';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';

import { InterestSelector } from '../../components/profile/InterestSelector';
import { NotificationSettings } from '../../components/profile/NotificationSettings';
import { PrivacySettings } from '../../components/profile/PrivacySettings';
import { DangerZone } from '../../components/profile/DangerZone';
import { PageHeader } from '../../components/ui/PageHeader';
import { compressImage } from '../../utils/imageUtils';

import userService from '../../services/userService';
import { useSavedTrials } from "../../hooks/useSavedTrials";
import { useTrials } from "../../hooks/useTrials";
import { useSaveTrial } from "../../hooks/useSaveTrial";

import { useQueryClient } from '@tanstack/react-query';


const languages = [
  { code: 'en', name: 'English' },
  { code: 'pt', name: 'Português' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'ar', name: 'العربية' },
];


export default function PatientDashboard() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, isProfileComplete } = useAuth();
  const { state, actions } = useData();

  useSavedTrials();
  const { data: allTrials = [] } = useTrials();
  const { toggleSave } = useSaveTrial();

  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [profileImage, setProfileImage] = useState<string | null>(null);

  // Form states
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    display_name: user?.display_name || '',
    email: user?.email || 'guest@example.com',
    role: user?.user_type || 'patient',
    organization: '',
    location: user?.location || 'Not specified',
    language: user?.language_preference || 'English',
    bio: user?.bio || 'Passionate about advancing health equity and improving access to clinical trials in underserved communities.',
    interests: (user?.interests as string[]) || []
  });

  // Sync form data when user data loads
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        display_name: user.display_name || '',
        email: user.email || '',
        role: user.user_type || 'patient',
        organization: '',
        location: user.location || 'Not specified',
        language: user.language_preference || 'English',
        bio: user.bio || '',
        interests: (user.interests as string[]) || []
      });
    }
  }, [user]);

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

  // Derived state for saved trials
  const savedTrials = allTrials.filter(trial => state.savedTrials.includes(trial.id));

  const handleSave = async () => {
    try {
      await userService.updateProfile({
        first_name: formData.first_name,
        last_name: formData.last_name,
        display_name: formData.display_name,
        bio: formData.bio,
        location: formData.location,
        language_preference: formData.language,
        interests: formData.interests,
      });
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      setIsEditing(false);
      toast.success("Profile Updated", {
        description: "Your changes have been saved successfully.",
      });
    } catch (error: any) {
      toast.error("Update Failed", {
        description:
          error?.response?.data?.detail ||
          error?.message ||
          "Could not save changes. Please try again.",
      });
    }
  };

  const handleRemoveTrial = (trialId: string) => {
    toggleSave(trialId);
  };

  const handleProfileImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Invalid file type', { description: 'Please upload an image file.' });
        return;
      }
      
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        toast.error('Invalid format', { description: 'Allowed formats: PNG, JPEG, JPG, WEBP.' });
        return;
      }
      
      if (file.size > 2 * 1024 * 1024) {
        toast.error('File too large', { description: 'File size must be less than 2MB.' });
        return;
      }

      try {
        let finalFile = file;
        try {
          finalFile = await compressImage(file);
        } catch (e) {
          console.error("Silent compression failure:", e);
        }
        const response = await userService.uploadAvatar(finalFile);
        queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
        toast.success('Profile Photo Updated', {
          description: response.message || 'Your new profile photo has been uploaded successfully.'
        });
      } catch (error: any) {
        toast.error('Upload Failed', { 
          description: error?.message || 'Could not upload avatar. Please try again.' 
        });
      }
    }
  };

  const handleDeleteAvatar = async () => {
    try {
      const response = await userService.deleteAvatar();
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast.success('Profile Photo Deleted', {
        description: response.message || 'Your profile photo has been deleted.'
      });
    } catch (error: any) {
      toast.error('Delete Failed', { 
        description: error?.message || 'Could not delete avatar. Please try again.' 
      });
    }
  };

  /**
   * Redirect incomplete users
   */
  useEffect(() => {
    if (!isLoading && isAuthenticated && !isProfileComplete) {
      navigate("/patientdashboard");
    }
  }, [isLoading, isAuthenticated, isProfileComplete, navigate]);

  const tabs = [
    { id: 'profile', label: 'Profile Settings', icon: User },
    { id: 'design', label: 'Design & Appearance', icon: Palette },
    { id: 'saved', label: 'Saved Trials', icon: Heart },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Security', icon: Shield },
    { id: 'danger', label: 'Danger Zone', icon: Lock, variant: 'destructive' }
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
          <p className="text-muted-foreground font-medium animate-pulse">Syncing your profile...</p>
        </div>
      </div>
    );
  }

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
        title={formData.first_name && formData.last_name ? `${formData.first_name} ${formData.last_name}` : formData.display_name || 'Guest User'}
        description={formData.bio}
        badgeText={user?.user_type === 'hcp' ? 'Healthcare Professional' : 'Patient Advocate'}
        variant="green"
        className="mb-0"
        action={
          <div className="relative group">
            <div className="w-24 h-24 md:w-32 md:h-32 rounded-full border-4 border-white/40 shadow-2xl overflow-hidden bg-white/10 flex items-center justify-center backdrop-blur-md">
              {profileImage ? (
                <img src={profileImage} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={48} className="text-white" />
              )}
            </div>
            
            {profileImage && (
              <button
                onClick={handleDeleteAvatar}
                className="absolute -top-1 -right-1 p-1.5 bg-destructive hover:bg-destructive/90 text-red-500 rounded-full cursor-pointer transition-all shadow-xl border-2 border-background z-20 hover:scale-110 flex items-center justify-center"
                title="Delete Photo"
              >
                <X size={18} className="stroke-[3] text-red-500 hover:text-red-600" />
              </button>
            )}

            <div className="absolute bottom-0 right-0">
              <label className="p-2.5 bg-primary-color hover:bg-primary-color/90 text-white rounded-full cursor-pointer transition-all shadow-xl border-2 border-background flex items-center justify-center z-20 hover:scale-110" title="Upload Photo">
                <Camera size={16} />
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  onChange={handleProfileImageUpload}
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
                      ? 'bg-primary/10 text-primary-color shadow-sm ring-1 ring-primary/20'
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
                >
                  {isEditing ? <Save size={16} /> : <Edit size={16} />}
                  {isEditing ? 'Save Changes' : 'Edit Profile'}
                </Button>
              </div>

              <Card className="p-6 border-border/60 shadow-sm">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      value={formData.first_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                      disabled={!isEditing}
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      value={formData.last_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                      disabled={!isEditing}
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="display_name">Display Name</Label>
                    <Input
                      id="display_name"
                      value={formData.display_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
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
                      onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                      disabled={!isEditing}
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
                          <SelectItem key={lang.code} value={lang.name}>
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

          {/* Saved Trials Tab */}
          {activeTab === 'saved' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex justify-between items-center bg-card p-4 rounded-xl border shadow-sm mb-2">
                <div>
                  <h2 className="text-lg font-bold">Your Saved Trials</h2>
                  <p className="text-sm text-muted-foreground">Manage the trials you are tracking.</p>
                </div>
                <Badge variant="secondary" className="text-white">{savedTrials.length} Saved</Badge>
              </div>

              {savedTrials.length === 0 ? (
                <Card className="p-16 text-center border-dashed bg-muted/20">
                  <Heart className="mx-auto mb-4 text-muted-foreground/30" size={48} />
                  <h4 className="font-bold text-lg mb-2">No Saved Trials Yet</h4>
                  <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                    Explore our clinical trials database and save the ones you are interested in.
                  </p>
                  <Button onClick={() => navigate('/trials')}>
                    Browse Trials
                  </Button>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {savedTrials.map((trial) => (
                    <Card key={trial.id} className="p-5 group hover:border-primary-color/50 hover:shadow-md transition-all">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex gap-2 mb-3">
                            <Badge variant="outline" className="border-primary-color/20 text-primary-color bg-primary/5">{trial.disease}</Badge>
                            <Badge variant="secondary" className="font-normal">{trial.phase}</Badge>
                          </div>
                          <h4 className="font-bold text-lg mb-2 group-hover:text-primary-color transition-colors cursor-pointer" onClick={() => navigate(`/trials/${trial.id}`)}>{trial.title}</h4>
                          <p className="text-muted-foreground line-clamp-2 mb-4 text-sm">{trial.description}</p>
                          <div className="flex items-center gap-4 text-xs font-medium text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                              <MapPin size={14} className="text-primary-color" />
                              {trial.location?.[0] || 'Remote'}
                            </span>
                            <span className="flex items-center gap-1.5">
                              <FileText size={14} className="text-primary-color" />
                              {trial.sponsor}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <Button size="sm" variant="outline" onClick={() => navigate(`/trials/${trial.id}`)}>
                            View
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
                            onClick={() => handleRemoveTrial(trial.id)}
                            title="Remove"
                          >
                            <Trash2 size={16} />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Design Tab */}
          {activeTab === 'design' && (
            <DesignSettings />
          )}

          {/* New Separate Settings Tabs */}
          {activeTab === 'notifications' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <NotificationSettings />
            </div>
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
