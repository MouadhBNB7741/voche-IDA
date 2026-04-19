import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Lock, ArrowRight, Loader2, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { authService } from '../../services/authService';
import idaLogo from '../../assets/ida.webp';

export default function ResetPassword() {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Extract token from URL
  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      toast.error('Invalid or missing reset token. Please request a new reset link.');
      return;
    }

    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setIsLoading(true);
    try {
      await authService.resetPassword(token, newPassword);
      setSubmitted(true);
      toast.success('Password reset successfully!');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Reset failed. Your link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="text-5xl">⚠️</div>
          <h2 className="text-2xl font-bold">Invalid Reset Link</h2>
          <p className="text-muted-foreground">
            This reset link is invalid or has expired.
          </p>
          <Link to="/forgot-password">
            <Button className="mt-4">Request a new reset link</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background animate-in fade-in duration-500">
      <div className="w-full max-w-md space-y-8">

        <div className="flex items-center gap-2 mb-6">
          <img src={idaLogo} alt="Voche Logo" className="w-8 h-8 object-contain rounded-lg" />
          <span className="font-bold text-xl">voche</span>
        </div>

        {!submitted ? (
          <>
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tight">Reset your password</h2>
              <p className="text-muted-foreground">Enter your new password below.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="newPassword"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
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
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
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

              <Button type="submit" className="w-full h-11 text-base font-semibold" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Resetting...
                  </>
                ) : (
                  <>
                    Reset Password <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </>
        ) : (
          <div className="space-y-4 text-center">
            <div className="text-5xl">✅</div>
            <h2 className="text-2xl font-bold">Password reset!</h2>
            <p className="text-muted-foreground">
              Your password has been successfully updated.
            </p>
            <Button onClick={() => navigate('/login')} className="mt-4 w-full h-11">
              Back to Login <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        )}

        {!submitted && (
          <div className="text-center text-sm pt-4">
            <Link to="/login" className="flex items-center justify-center gap-1 text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft size={14} /> Back to login
            </Link>
          </div>
        )}

      </div>
    </div>
  );
}