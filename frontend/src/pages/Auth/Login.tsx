import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../contexts/AuthContext';
import { Checkbox } from '../../components/ui/checkbox';
import { Eye, EyeOff, Loader2, KeyRound, Mail, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import idaLogo from '../../assets/ida.webp';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login, isLoading } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password }); 
      toast.success('Welcome back!');
    } catch (error: any) {
      console.error('Login error:', error);
      toast.error(error.message || 'Login failed. Please check your credentials.');
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
                    className="absolute right-0 top-0 h-11 w-11 text-muted-foreground hover:text-foreground"
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

            <Button type="submit" className="w-full h-11 shadow-lg shadow-primary/20 text-base font-semibold" disabled={isLoading}>
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

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Button variant="outline" className="h-11 bg-card hover:text-primary-color border-input/60">
              <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Google
            </Button>
            <Button variant="outline" className="h-11 bg-card hover:text-primary-color border-input/60">
              <svg className="mr-2 h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.57-.12 0-.23-.02-.3-.03-.01-.06-.04-.15-.04-.21.02-1.19.58-2.33 1.277-3.21.744-.89 1.978-1.58 2.893-1.58.103 0 .23.04.305.04l.03.04zm4.089 18.7c-1.472.54-2.949 1.43-4.225 1.83-.876.28-1.419.12-1.954-.76-.73-1.19-2.3-1.19-3.04 0-.58.91-1.07 1.09-1.975.75-1.562-.6-3.79-2.48-5.32-5.45-1.859-3.64.08-5.74 3.76-7.39.296-.13.568-.17.808-.17.9 0 1.554.49 2.03.49.569 0 1.562-.51 2.502-.51.93 0 1.764.57 2.28 1.1-.986.9-1.636 2.28-1.636 3.75 0 2.92 2.22 4.09 2.65 4.34-.144.5-.487 1.44-.9 2.02z" />
              </svg>
              Apple
            </Button>
          </div>

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
