import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Mail, ArrowRight, Loader2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { authService } from '../../services/authService';
import idaLogo from '../../assets/ida.webp';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await authService.forgotPassword(email);
      setSubmitted(true);
      toast.success('Reset email sent!');
    } catch (error: any) {
      toast.error(error.message || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

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
              <h2 className="text-3xl font-bold tracking-tight">Forgot password?</h2>
              <p className="text-muted-foreground">
                Enter your email and we'll send you a reset link.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
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

              <Button type="submit" className="w-full h-11 text-base font-semibold" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    Send Reset Link <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </>
        ) : (
          // Success state
          <div className="space-y-4 text-center">
            <div className="text-5xl">📧</div>
            <h2 className="text-2xl font-bold">Check your email</h2>
            <p className="text-muted-foreground">
              We sent a password reset link to <span className="font-semibold text-foreground">{email}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Didn't receive it? Check your spam folder or try again.
            </p>
            <Button variant="outline" onClick={() => setSubmitted(false)} className="mt-4">
              Try again
            </Button>
          </div>
        )}

        <div className="text-center text-sm pt-4">
          <Link to="/login" className="flex items-center justify-center gap-1 text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft size={14} /> Back to login
          </Link>
        </div>

      </div>
    </div>
  );
}