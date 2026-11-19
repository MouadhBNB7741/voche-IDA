import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../contexts/AuthContext';
import { Checkbox } from '../../components/ui/checkbox';
import { Eye, EyeOff, Loader2, KeyRound, Mail, ArrowRight } from 'lucide-react';
import { GoogleSignInButton, isGoogleSignInEnabled } from '../../components/auth/GoogleSignInButton';
import idaLogo from '../../assets/ida.webp';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, loginWithGoogle, isLoading } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
    } catch (error: any) {
      console.error('Login error:', error);
    }
  };

  const handleGoogle = async (credential: string) => {
    try {
      await loginWithGoogle(credential);
    } catch (error) {
      console.error('Google sign-in error:', error);
    }
  };

  return (
    <div className="min-h-screen flex animate-in fade-in duration-500">
      {/* Branding Section */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[#0f172a] text-white flex-col justify-between p-12 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary-color/20 rounded-full blur-3xl rounded-full"></div>
          <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-secondary-color/20 rounded-full blur-3xl rounded-full"></div>
          <div className="absolute top-[40%] left-[20%] w-[300px] h-[300px] bg-accent-color/20 rounded-full blur-3xl rounded-full"></div>
        </div>

        <div className="z-10 relative">
          <div className="flex items-center gap-3 mb-6">
            <img src={idaLogo} alt="Voche Logo" className="w-10 h-10 object-contain rounded-xl shadow-lg shadow-primary/20" />
            <span className="font-bold text-2xl tracking-tight">Voche Platform</span>
          </div>
        </div>

        <div className="z-10 relative max-w-lg mb-20 space-y-6">
          <h1 className="text-5xl font-bold leading-tight tracking-tight">
            Advancing Health <span className="gradient-text-login">Equity</span> Together
          </h1>
          <p className="text-lg text-slate-300 leading-relaxed">
            Join a global community dedicated to making clinical trials and health resources accessible to everyone, everywhere.
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

      {/* Login Form Section */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background relative">
        <div className="w-full max-w-md space-y-8">
          <div className="lg:hidden absolute top-8 left-8 flex items-center gap-2">
            <img src={idaLogo} alt="Voche Logo" className="w-8 h-8 object-contain rounded-lg" />
            <span className="font-bold text-xl">voche</span>
          </div>

          <div className="space-y-2 text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight">Welcome back</h2>
            <p className="text-muted-foreground">
              Enter your credentials to access your account
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
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
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    to="/forgot-password"
                    className="text-sm font-medium text-primary-color hover:text-primary-color/80 transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
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
                    className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:text-foreground cursor-pointer"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox id="remember" className="text-primary-color"/>
              <label
                htmlFor="remember"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-muted-foreground"
              >
                Remember me for 30 days
              </label>
            </div>

            <Button type="submit" className="w-full h-11 shadow-lg shadow-primary/20 text-base font-semibold cursor-pointer" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  Login<ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {isGoogleSignInEnabled && (
            <>
              <div className="flex items-center gap-3 text-xs uppercase text-muted-foreground">
                <span className="h-px flex-1 bg-[hsl(var(--border))]" />
                Or continue with
                <span className="h-px flex-1 bg-[hsl(var(--border))]" />
              </div>

              <GoogleSignInButton text="signin_with" onCredential={handleGoogle} disabled={isLoading} />
            </>
          )}

          <div className="text-center text-sm">
            <span className="text-muted-foreground">Don't have an account? </span>
            <Link to="/signup" className="font-semibold text-primary-color hover:text-primary-color/80 transition-colors">
              Sign up for free
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}