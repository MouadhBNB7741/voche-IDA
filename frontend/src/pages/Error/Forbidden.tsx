import { ShieldAlert, Home, LogIn } from "lucide-react";
import { Button } from "../../components/ui/button";
import { useNavigate } from "react-router-dom";

export default function Forbidden() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="w-full max-w-lg text-center space-y-8 animate-in fade-in slide-in-from-bottom-5 duration-500">
        {/* Animated 403 Header Icon */}
        <div className="relative mx-auto w-36 h-36 flex items-center justify-center">
          {/* Pulsing Gradient Rings */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-destructive to-destructive/20 animate-ping opacity-20"></div>
          <div className="absolute inset-2 rounded-full bg-card border border-border shadow-inner flex items-center justify-center">
            <ShieldAlert className="text-destructive animate-pulse duration-1000" size={56} />
          </div>
        </div>

        {/* Text Details */}
        <div className="space-y-3">
          <h1 className="text-5xl font-extrabold tracking-tight text-destructive">
            403
          </h1>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">
            Access Forbidden
          </h2>
          <p className="text-muted-foreground max-w-md mx-auto text-sm leading-relaxed">
            You do not have permission to access this resource or page. If you believe this is an error, please sign in with an authorized account or contact support.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4 max-w-sm mx-auto">
          <Button
            variant="outline"
            className="w-full h-12 rounded-xl flex items-center justify-center gap-2 cursor-pointer"
            onClick={() => navigate("/login")}
          >
            <LogIn size={18} />
            Sign In / Log In
          </Button>

          <Button
            className="w-full h-12 bg-primary-color text-white hover:bg-primary-color/90 rounded-xl flex items-center justify-center gap-2 shadow-lg hover:scale-105 active:scale-95 transition-all cursor-pointer"
            onClick={() => navigate("/")}
          >
            <Home size={18} />
            Go Back Home
          </Button>
        </div>
      </div>
    </div>
  );
}
