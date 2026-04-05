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
  Palette
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

const languages = [
  { code: 'en', name: 'English' },
  { code: 'pt', name: 'Português' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'ar', name: 'العربية' },
];

export default function PatientDashboard() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const { state, actions } = useData();

  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [profileImage, setProfileImage] = useState<string | null>(null);

  // Derived state for saved trials
  const savedTrials = state.trials.filter(trial => state.savedTrials.includes(trial.trial_id));

  // Form states
  const [formData, setFormData] = useState({
    name: user?.display_name || 'Guest User',
    email: user?.email || 'guest@example.com',
    role: user?.user_type || 'patient',
    organization: '',
    location: 'Not specified',
    language: 'English',
    bio: 'Passionate about advancing health equity and improving access to clinical trials in underserved communities.',
    interests: ['HIV Prevention', 'Clinical Trials'] as string[]
  });

  useEffect(() => {
    // Load mock profile image
    const storedImage = localStorage.getItem('voce_profile_image');
    if (storedImage) {
      setProfileImage(storedImage);
    }
  }, []);

  const handleSave = () => {
    setIsEditing(false);
    toast.success('Profile Updated', {
      description: 'Your changes have been saved successfully.'
    });
  };

  const handleRemoveTrial = (trialId: string) => {
    actions.unsaveTrial(trialId);
    toast.info('Trial Removed', {
      description: 'The trial has been removed from your saved list.'
    });
  };

  const handleProfileImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Invalid file type', { description: 'Please upload an image file.' });
        return;
      }

      try {
        const compressedImage = await compressImage(file);
        setProfileImage(compressedImage);
        localStorage.setItem('voce_profile_image', compressedImage);
        toast.success('Profile Photo Updated', {
          description: 'Your new profile photo has been saved and optimized.'
        });
      } catch (error) {
        toast.error('Upload Failed', { description: 'Could not process image. Please try again.' });
      }
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile Settings', icon: User },
    { id: 'design', label: 'Design & Appearance', icon: Palette },
    { id: 'saved', label: 'Saved Trials', icon: Heart },
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
            <Button size="lg" variant="outline" onClick={() => navigate('/register')} className="px-8">Register</Button>
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
        badgeText={user?.user_type === 'hcp' ? 'Healthcare Professional' : 'Patient Advocate'}
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
            <label className="absolute bottom-0 right-0 p-2.5 bg-background text-foreground rounded-full cursor-pointer hover:bg-muted transition-all shadow-lg border border-border" title="Upload Photo">
              <Camera size={16} />
              <input
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleProfileImageUpload}
              />
            </label>
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
                    <Card key={trial.trial_id} className="p-5 group hover:border-primary-color/50 hover:shadow-md transition-all">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex gap-2 mb-3">
                            <Badge variant="outline" className="border-primary-color/20 text-primary-color bg-primary/5">{trial.disease_area}</Badge>
                            <Badge variant="secondary" className="font-normal">{trial.phase}</Badge>
                          </div>
                          <h4 className="font-bold text-lg mb-2 group-hover:text-primary-color transition-colors cursor-pointer" onClick={() => navigate(`/trials/${trial.trial_id}`)}>{trial.title}</h4>
                          <p className="text-muted-foreground line-clamp-2 mb-4 text-sm">{trial.summary}</p>
                          <div className="flex items-center gap-4 text-xs font-medium text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                              <MapPin size={14} className="text-primary-color" />
                              {trial.countries?.[0] || 'International'}
                            </span>
                            <span className="flex items-center gap-1.5">
                              <FileText size={14} className="text-primary-color" />
                              {trial.sponsor}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <Button size="sm" variant="outline" onClick={() => navigate(`/trials/${trial.trial_id}`)}>
                            View
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
                            onClick={() => handleRemoveTrial(trial.trial_id)}
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
