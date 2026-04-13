import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../contexts/AuthContext';
import { Eye, EyeOff, Loader2, Mail, Lock, User, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import type { UserType } from '../../types/db';
import idaLogo from '../../assets/ida.webp';

export default function Register() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [userType, setUserType] = useState<UserType>('patient');
  const [showPassword, setShowPassword] = useState(false);
  const { register, isLoading } = useAuth();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    try {
      await register({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        user_type: userType
      });
      
      toast.success('Registration successful!');
    } catch (error: any) {
      console.error('Registration error:', error);
      toast.error(error.message || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex animate-in fade-in duration-500">
      {/* Branding Section */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[#0f172a] text-white flex-col justify-between p-12 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-3xl rounded-full"></div>
          <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-secondary/20 rounded-full blur-3xl rounded-full"></div>
          <div className="absolute top-[30%] right-[30%] w-[200px] h-[200px] bg-accent/20 rounded-full blur-3xl rounded-full"></div>
        </div>

        <div className="z-10 relative">
          <div className="flex items-center gap-3 mb-6">
            <img src={idaLogo} alt="Voche Logo" className="w-10 h-10 object-contain rounded-xl shadow-lg shadow-primary/20" />
            <span className="font-bold text-2xl tracking-tight">Voche Platform</span>
          </div>
        </div>

        <div className="z-10 relative max-w-lg mb-20 space-y-6">
          <h1 className="text-5xl font-bold leading-tight tracking-tight">
            Empowering <span className="gradient-text-signup">Patients</span> & Researchers
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed">
            Create an account to access personalized clinical trials, connect with a supportive community, and contribute to medical advancement.
          </p>
        </div>

        <div className="z-10 relative flex justify-between items-center text-sm text-slate-400">
          <p>©{new Date().getFullYear()} Voche Platform. All rights reserved.</p>
          <div className="flex gap-4">
            <Link to="#" className="hover:text-white transition-colors">Privacy</Link>
            <Link to="#" className="hover:text-white transition-colors">Terms</Link>
          </div>
        </div>
      </div>

      {/* SignUp Form Section */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background relative overflow-y-auto">
        <div className="w-full max-w-md space-y-8 my-auto">
          <div className="lg:hidden absolute top-8 left-8 flex items-center gap-2">
            <img src={idaLogo} alt="Voche Logo" className="w-8 h-8 object-contain rounded-lg" />
            <span className="font-bold text-xl">voche</span>
          </div>

          <div className="space-y-2 text-center lg:text-left mt-8 lg:mt-0">
            <h2 className="text-3xl font-bold tracking-tight">Create an account</h2>
            <p className="text-muted-foreground">
              Join the Voche community today
            </p>
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="firstName"
                      placeholder="John"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="pl-9 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="lastName"
                      placeholder="Doe"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="pl-9 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">I am a...</Label>
                <Select onValueChange={(val) => setUserType(val as UserType)} defaultValue={userType}>
                  <SelectTrigger className="h-11 bg-muted/30 border-input/60 focus:bg-background transition-all">
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="patient">Patient / Participant</SelectItem>
                    <SelectItem value="hcp">Healthcare Professional</SelectItem>
                    <SelectItem value="org_member">Organization Member</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pl-9 pr-10 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                      required
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:text-foreground"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="confirmPassword"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="pl-9 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                      required
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-start space-x-2 pt-2 pb-2">
              <input
                type="checkbox"
                id="consent"
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-color focus:ring-primary"
                required
              />
              <Label htmlFor="consent" className="text-sm font-normal text-muted-foreground leading-snug">
                I agree to the <Link to="#" className="text-primary-color hover:underline">Terms of Service</Link> and <Link to="#" className="text-primary-color hover:underline">Privacy Policy</Link>, and consent to data processing.
              </Label>
            </div>

            <Button type="submit" className="w-full h-11 shadow-lg shadow-primary/20 text-base font-semibold" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  Create Account <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          <div className="text-center text-sm pt-4">
            <span className="text-muted-foreground">Already have an account? </span>
            <Link to="/login" className="font-semibold text-primary-color hover:text-primary-color/80 transition-colors">
              Log in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}