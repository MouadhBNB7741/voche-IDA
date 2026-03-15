import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../contexts/AuthContext';
import type { AuthUser } from '../../services/authService';
import { Eye, EyeOff, Loader2, Mail, Lock, User, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import idaLogo from '../../assets/ida.webp';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<AuthUser['role']>('patient');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await register(email, password, name, role);
      await new Promise(resolve => setTimeout(resolve, 800));
      toast.success('Registration successful!', {
        description: 'Please check your email to verify your account.',
      });
      navigate('/');
    } catch (error) {
      toast.error('Registration failed', {
        description: 'Please try again later.',
      });
    } finally {
      setLoading(false);
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
            <img src={idaLogo} alt="VOCE Logo" className="w-10 h-10 object-contain rounded-xl shadow-lg shadow-primary/20" />
            <span className="font-bold text-2xl tracking-tight">VOCE Platform</span>
          </div>
        </div>

        <div className="z-10 relative max-w-lg mb-20 space-y-6">
          <h1 className="text-5xl font-bold leading-tight tracking-tight">
            Empowering <span className="text-transparent bg-clip-text bg-gradient-to-r from-secondary to-info">Patients</span> & Researchers
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed">
            Create an account to access personalized clinical trials, connect with a supportive community, and contribute to medical advancement.
          </p>
        </div>

        <div className="z-10 relative flex justify-between items-center text-sm text-slate-400">
          <p>©{new Date().getFullYear()} VOCE Platform. All rights reserved.</p>
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
            <img src={idaLogo} alt="VOCE Logo" className="w-8 h-8 object-contain rounded-lg" />
            <span className="font-bold text-xl">VOCE</span>
          </div>

          <div className="space-y-2 text-center lg:text-left mt-8 lg:mt-0">
            <h2 className="text-3xl font-bold tracking-tight">Create an account</h2>
            <p className="text-muted-foreground">
              Join the VOCE community today
            </p>
          </div>

          <form onSubmit={handleRegister} className="space-y-5">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="name"
                    placeholder="John Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="pl-9 h-11 bg-muted/30 border-input/60 focus:bg-background transition-all"
                    required
                  />
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
                <Select onValueChange={(val) => setRole(val as AuthUser['role'])} defaultValue={role}>
                  <SelectTrigger className="h-11 bg-muted/30 border-input/60 focus:bg-background transition-all">
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="patient">Patient / Participant</SelectItem>
                    <SelectItem value="hcp">Healthcare Professional</SelectItem>
                    <SelectItem value="caregiver">Caregiver</SelectItem>
                    <SelectItem value="researcher">Researcher</SelectItem>
                    <SelectItem value="admin">Administrator</SelectItem>
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
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                required
              />
              <Label htmlFor="consent" className="text-sm font-normal text-muted-foreground leading-snug">
                I agree to the <Link to="#" className="text-primary hover:underline">Terms of Service</Link> and <Link to="#" className="text-primary hover:underline">Privacy Policy</Link>, and consent to data processing.
              </Label>
            </div>

            <Button type="submit" className="w-full h-11 shadow-lg shadow-primary/20 text-base font-semibold" disabled={loading}>
              {loading ? (
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
            <Link to="/login" className="font-semibold text-primary hover:text-primary/80 transition-colors">
              Log in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}