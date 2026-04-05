import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import {
  User,
  Bell,
  Globe,
  MapPin,
  Edit,
  Save,
  Camera,
  Heart,
  FileText,
  Lock,
  Shield,
  Upload,
  ChevronRight,
  Trash2,
  Stethoscope,
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

export default function HCPDashboard() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [profileImage, setProfileImage] = useState<string | null>(null);

  // Form states
    const [formData, setFormData] = useState({
      name: user?.name || 'Guest User',
      email: user?.email || 'guest@example.com',
      role: user?.role || 'patient',
      organization: '',
      location: 'Not specified',
      language: 'English',
      bio: 'Passionate about advancing health equity and improving access to clinical trials in underserved communities.',
      interests: ['HIV Prevention', 'Clinical Trials'] as string[]
    });


  // Doctor feedback 
  const [feedbackData, setFeedbackData] = useState({
    category: '',
    message: '',
  });

  const handleSave = () => {
    setIsEditing(false);
    toast.success('Profile Updated', {
      description: 'Your changes have been saved successfully.'
    });
  };

  const handleDocFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      toast.success('File Uploaded', {
        description: `${file.name} has been uploaded successfully. Pending verification.`
      });
    }
  };

  const handleFeedbackSubmit = () => {
    if (!feedbackData.category || !feedbackData.message) {
      toast.error('Error', { description: 'Please fill in all fields.' });
      return;
    }
    toast.success('Feedback Submitted', { description: 'Thank you for your feedback!' });
    setFeedbackData({ category: '', message: '' });
  };

  const isDoctor = user?.role === 'hcp';

  const tabs = [
    { id: 'profile', label: 'Profile Settings', icon: User },
    { id: 'design', label: 'Design & Appearance', icon: Palette },
    ...(isDoctor ? [{ id: 'doctor', label: 'Doctor Tools', icon: Stethoscope }] : []),
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
        badgeText={user?.role === 'hcp' ? 'Healthcare Professional' : 'Patient Advocate'}
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

          {/* Doctor Tools Tab */}
          {activeTab === 'doctor' && isDoctor && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <Card className="p-6 border-border/60 shadow-sm">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <FileText size={18} className="text-primary-color" />
                  License Verification
                </h3>
                <p className="text-muted-foreground mb-6 text-sm">
                  Upload your medical license for verification. Verified HCPs get access to exclusive patient recruitment tools.
                </p>

                <div
                  className="border-2 border-dashed border-border rounded-xl p-10 text-center cursor-pointer hover:border-primary-color hover:bg-primary-color/5 transition-all duration-300 group"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleDocFileUpload}
                    accept=".pdf,.jpg,.jpeg,.png"
                    className="hidden"
                  />
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/10 transition-colors">
                    <Upload className="text-muted-foreground group-hover:text-primary-color transition-colors" size={28} />
                  </div>

                  {uploadedFile ? (
                    <div className="animate-in zoom-in duration-300">
                      <p className="font-bold text-success flex items-center justify-center gap-2">
                        <FileText size={16} />
                        {uploadedFile.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">Uploaded - Pending verification</p>
                    </div>
                  ) : (
                    <div>
                      <p className="font-bold text-lg mb-1">Drag & drop or click to upload</p>
                      <p className="text-xs text-muted-foreground">PDF or Image (max 10MB)</p>
                    </div>
                  )}
                </div>
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
                    <Label>Message</Label>
                    <Textarea
                      value={feedbackData.message}
                      onChange={(e) => setFeedbackData(prev => ({ ...prev, message: e.target.value }))}
                      rows={5}
                      placeholder="Share your detailed feedback..."
                      className="bg-muted/30 resize-none"
                    />
                  </div>
                  <Button onClick={handleFeedbackSubmit} className="w-full sm:w-auto">Submit Feedback</Button>
                </div>
              </Card>
            </div>
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
