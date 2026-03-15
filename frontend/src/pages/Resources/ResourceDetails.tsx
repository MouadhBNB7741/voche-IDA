import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  ArrowLeft,
  Download,
  Play,
  Award,
  Star,
  Clock,
  Globe,
  Eye,
  Lock,
  LogIn,
  FileText,
  Video,
  BookOpen,
  Loader2
} from 'lucide-react';
import { resourceService } from '../../services/resourceService';
import type { ExtendedResource } from '../../services/resourceService';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { PageHeader } from '../../components/ui/PageHeader';

export default function ResourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [resource, setResource] = useState<ExtendedResource | null>(null);
  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);

  useEffect(() => {
    if (id) {
      const foundResource = resourceService.getById(id);
      setResource(foundResource || null);
    }
  }, [id]);

  const canAccess = resource ? resourceService.canAccess(resource.id, isAuthenticated) : false;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'video': return Video;
      case 'course': return Award;
      case 'document': return FileText;
      default: return BookOpen;
    }
  };

  const simulateDownload = () => {
    if (isDownloading) return;
    setIsDownloading(true);

    toast.info('Starting Download', {
      description: `Preparing ${resource?.title}...`
    });

    setTimeout(() => {
      // Mock download logic
      const blob = new Blob(["Mock PDF Content"], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${resource?.title || 'resource'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setIsDownloading(false);
      toast.success('Download Complete', {
        description: 'File has been saved to your device.'
      });
    }, 1500);
  };

  const handleVideoPlay = () => {
    setVideoLoading(true);
    setIsVideoOpen(true);
    // Simulate loading buffer
    setTimeout(() => setVideoLoading(false), 1000);
  };

  const getPrimaryAction = () => {
    if (!resource) return null;

    if (!canAccess) {
      return (
        <Button asChild className="w-full gap-2 shadow-md">
          <Link to="/login">
            <LogIn size={16} />
            Login to Access
          </Link>
        </Button>
      );
    }

    switch (resource.type) {
      case 'video':
        return (
          <Button className="w-full gap-2 shadow-md" onClick={handleVideoPlay}>
            <Play size={16} />
            Watch Video
          </Button>
        );
      case 'course':
        return (
          <Button className="w-full gap-2 shadow-md" onClick={() => toast.success('Course Started')}>
            <Award size={16} />
            Start Course
          </Button>
        );
      default:
        return (
          <Button className="w-full gap-2 shadow-md" onClick={simulateDownload} disabled={isDownloading}>
            {isDownloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            {isDownloading ? 'Downloading...' : 'Download Resource'}
          </Button>
        );
    }
  };

  if (!resource) {
    return (
      <div className="container mx-auto p-4">
        <Card className="p-16 text-center border-dashed">
          <BookOpen size={48} className="mx-auto mb-4 text-muted-foreground/30" />
          <h2 className="text-xl font-semibold mb-2">Resource not found</h2>
          <Button onClick={() => navigate('/resources')}>Back to Resources</Button>
        </Card>
      </div>
    );
  }

  const TypeIcon = getTypeIcon(resource.type);

  return (
    <div className="container mx-auto p-4 max-w-4xl space-y-6 animate-in fade-in duration-300">
      {/* Back Button */}
      <Button variant="ghost" onClick={() => navigate('/resources')} className="gap-2 pl-0 hover:bg-transparent hover:text-primary">
        <ArrowLeft size={16} />
        Back to Resources
      </Button>

      <PageHeader
        title={resource.title}
        description={resource.description}
        variant="orange"
        badgeText={`${resource.category} • ${resource.type.charAt(0).toUpperCase() + resource.type.slice(1)}`}
        action={
          <div className="hidden md:flex gap-4 items-center bg-white/10 p-3 rounded-xl backdrop-blur-sm">
            <div className="text-center">
              <div className="text-xl font-bold text-white">{resource.rating}</div>
              <div className="text-[10px] text-white/80 uppercase">Rating</div>
            </div>
            <div className="w-px bg-white/20 h-8"></div>
            <div className="text-center">
              <div className="text-xl font-bold text-white">{resource.language.slice(0, 2).toUpperCase()}</div>
              <div className="text-[10px] text-white/80 uppercase">Lang</div>
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Locked State */}
          {resource.requiresAuth && !isAuthenticated && (
            <Card className="p-6 bg-warning/5 border-warning/20 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center shrink-0">
                  <Lock className="text-warning-foreground" size={24} />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-warning-foreground">Login Required</h3>
                  <p className="text-sm text-foreground/80">
                    This resource is available only to registered users.
                  </p>
                </div>
                <Button asChild className="shadow-sm">
                  <Link to="/login">Login</Link>
                </Button>
              </div>
            </Card>
          )}

          {/* About */}
          <Card className="p-6 border-border/60 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BookOpen size={20} className="text-primary" />
              About This Resource
            </h2>
            <p className="text-muted-foreground leading-relaxed whitespace-pre-line">
              {resource.description}
            </p>
            <div className="mt-6 p-5 bg-muted/40 rounded-xl border border-border/50">
              <h3 className="font-bold mb-3 text-xs uppercase tracking-wide text-muted-foreground">Topics Covered</h3>
              <ul className="grid sm:grid-cols-2 gap-2 text-sm">
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" />Introduction to Key Concepts</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" />Advanced Methodologies</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" />Case Studies & Analysis</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" />Implementation Guide</li>
              </ul>
            </div>
          </Card>

          {/* Tags */}
          <Card className="p-6 border-border/60 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Tags</h2>
            <div className="flex flex-wrap gap-2">
              {resource.tags?.map((tag) => (
                <Badge key={tag} variant="secondary" className="hover:bg-secondary/20 transition-colors cursor-pointer px-3 py-1">
                  #{tag}
                </Badge>
              ))}
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Action Card */}
          <Card className="p-6 shadow-lg border-primary/20 bg-card relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <TypeIcon size={100} />
            </div>
            <div className="space-y-4 relative z-10">
              <div className="flex justify-center mb-4">
                <div className="bg-primary/10 p-4 rounded-full text-primary">
                  <TypeIcon size={40} />
                </div>
              </div>

              {getPrimaryAction()}

              <Button
                variant="outline"
                className="w-full gap-2 border-dashed border-border"
                onClick={() => toast.info('Opening Preview...')}
              >
                <Eye size={16} />
                Preview Resource
              </Button>
            </div>
          </Card>

          {/* Details */}
          <Card className="p-6 border-border/60 shadow-sm">
            <h3 className="font-semibold mb-4">Resource Details</h3>
            <div className="space-y-4 text-sm">
              <div className="flex justify-between border-b border-border/50 pb-2"><span className="text-muted-foreground">Type</span><span className="font-medium capitalize">{resource.type}</span></div>
              <div className="flex justify-between border-b border-border/50 pb-2"><span className="text-muted-foreground">Category</span><span className="font-medium">{resource.category}</span></div>
              <div className="flex justify-between border-b border-border/50 pb-2"><span className="text-muted-foreground">Language</span><span className="font-medium">{resource.language}</span></div>
              {resource.downloads && <div className="flex justify-between border-b border-border/50 pb-2"><span className="text-muted-foreground">Downloads</span><span className="font-medium">{resource.downloads.toLocaleString()}</span></div>}
              {resource.duration && <div className="flex justify-between border-b border-border/50 pb-2"><span className="text-muted-foreground">Duration</span><span className="font-medium">{resource.duration}</span></div>}
              <div className="flex justify-between pt-1"><span className="text-muted-foreground">Author</span><span className="font-medium truncate max-w-[150px]" title={resource.author}>{resource.author}</span></div>
            </div>
          </Card>
        </div>
      </div>

      {/* Video Modal */}
      <Dialog open={isVideoOpen} onOpenChange={setIsVideoOpen}>
        <DialogContent className="sm:max-w-4xl p-0 overflow-hidden bg-black border-none">
          <DialogHeader className="sr-only">
            <DialogTitle>Video Player</DialogTitle>
          </DialogHeader>
          <div className="relative aspect-video flex items-center justify-center bg-black group">
            {videoLoading ? (
              <div className="flex flex-col items-center gap-2 text-white">
                <Loader2 size={48} className="animate-spin text-primary" />
                <p className="text-sm font-medium">Loading Media...</p>
              </div>
            ) : (
              <div className="w-full h-full bg-slate-900 flex flex-col items-center justify-center text-white p-8 text-center relative">
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-60"></div>
                <div className="relative z-10">
                  <Play size={80} className="mb-6 text-primary drop-shadow-lg cursor-pointer hover:scale-110 transition-transform" />
                  <h3 className="text-2xl font-bold mb-2 tracking-tight">{resource?.title}</h3>
                  <p className="text-slate-300 max-w-lg mx-auto text-lg">Mock Video Player - In production this would be an embedded video stream.</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}