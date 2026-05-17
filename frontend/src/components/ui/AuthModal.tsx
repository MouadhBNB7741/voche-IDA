import { ShieldAlert, X, LogIn, UserPlus } from "lucide-react";
import { Button } from "./button";
import { useNavigate } from "react-router-dom";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
}

export function AuthModal({ isOpen, onClose, message }: AuthModalProps) {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleLogin = () => {
    onClose();
    navigate("/login");
  };

  const handleSignup = () => {
    onClose();
    navigate("/signup");
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-300"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-md bg-card text-card-foreground border border-border/80 shadow-2xl rounded-2xl p-6 md:p-8 animate-in zoom-in-95 duration-300 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button 
          onClick={onClose}
          className="absolute top-4 cursor-pointer right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X size={18} />
        </button>

        {/* Lock / Alert Illustration */}
        <div className="w-16 h-16 bg-primary-color/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-primary-color/5">
          <ShieldAlert className="text-primary-color" size={32} />
        </div>

        {/* Modal Headings */}
        <h3 className="text-2xl font-bold text-center mb-2 tracking-tight">
          Authentication Required
        </h3>
        <p className="text-center text-muted-foreground mb-8 text-sm leading-relaxed max-w-xs mx-auto">
          {message || "You need to be logged in to complete this action. Sign in to your Voche account to continue."}
        </p>

        {/* Action Buttons */}
        <div className="space-y-3">
          <Button 
            onClick={handleLogin}
            className="w-full  cursor-pointer bg-primary-color text-white hover:bg-primary-color/90 transition-all font-bold h-12 rounded-xl shadow-lg flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-[0.98]"
          >
            <LogIn size={18} />
            Sign In / Log In
          </Button>
          
          <Button 
            variant="outline"
            onClick={handleSignup}
            className="w-full cursor-pointer border border-border hover:bg-muted/50 transition-all font-medium h-12 rounded-xl flex items-center justify-center gap-2 hover:scale-[1.01] active:scale-[0.99]"
          >
            <UserPlus size={18} />
            Create an Account
          </Button>
        </div>

        {/* Dismiss Text Link */}
        <button
          onClick={onClose}
          className="w-full cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors mt-6 text-center cursor-pointer font-medium hover:underline"
        >
          Continue Browsing as Guest
        </button>
      </div>
    </div>
  );
}
