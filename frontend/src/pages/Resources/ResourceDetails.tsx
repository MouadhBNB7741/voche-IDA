import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Textarea } from "../../components/ui/textarea";

import {
  ArrowLeft,
  Download,
  Play,
  Award,
  Clock,
  Globe,
  Eye,
  Lock,
  LogIn,
  FileText,
  Video,
  BookOpen,
  Loader2,
  Star,
} from "lucide-react";
import { resourceService } from "../../services/resourceService";
import type { Resource } from "../../types/db";
import { useAuth } from "../../contexts/AuthContext";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { PageHeader } from "../../components/ui/PageHeader";

export default function ResourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);

  const [hoveredStar, setHoveredStar] = useState(0);
  const [selectedRating, setSelectedRating] = useState(0);
  const [review, setReview] = useState("");

  const [progress, setProgress] = useState(0);

  const queryClient = useQueryClient();

  // useQuery
  const {
    data: resource,
    isLoading,
    isError,
  } = useQuery<Resource>({
    queryKey: ["resource", id],
    queryFn: () => resourceService.getById(id!),
    enabled: !!id,
  });

  const canAccess = resource
    ? resourceService.canAccess(
        resource.requires_auth ?? false,
        isAuthenticated,
      )
    : false;

  const ratingMutation = useMutation({
    mutationFn: () =>
      resourceService.rateResource(
        resource!.resource_id,
        selectedRating,
        review,
      ),
    onSuccess: (data) => {
      toast.success(`Rating submitted! New average: ${data.new_average}`);
      queryClient.invalidateQueries({ queryKey: ["resource", id] });
      setSelectedRating(0);
      setReview("");
    },
    onError: () => {
      toast.error("Failed to submit rating. Please try again.");
    },
  });

  const progressMutation = useMutation({
    mutationFn: () =>
      resourceService.updateProgress(resource!.resource_id, progress),
    onSuccess: () => {
      toast.success("Progress saved!");
    },
    onError: () => {
      toast.error("Failed to save progress.");
    },
  });

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "video":
        return Video;
      case "course":
        return Award;
      case "document":
        return FileText;
      default:
        return BookOpen;
    }
  };

  const simulateDownload = () => {
    if (isDownloading) return;
    setIsDownloading(true);
    toast.info("Starting Download", {
      description: `Preparing ${resource?.title}...`,
    });
    setTimeout(() => {
      const blob = new Blob(["Mock PDF Content"], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${resource?.title || "resource"}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setIsDownloading(false);
      toast.success("Download Complete", {
        description: "File has been saved to your device.",
      });
    }, 1500);
  };

  const handleVideoPlay = () => {
    setVideoLoading(true);
    setIsVideoOpen(true);
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
      case "video":
        return (
          <Button className="w-full gap-2 shadow-md" onClick={handleVideoPlay}>
            <Play size={16} />
            Watch Video
          </Button>
        );
      case "course":
        return (
          <Button
            className="w-full gap-2 shadow-md"
            onClick={() => toast.success("Course Started")}
          >
            <Award size={16} />
            Start Course
          </Button>
        );
      default:
        return (
          <Button
            className="w-full gap-2 shadow-md"
            onClick={simulateDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Download size={16} />
            )}
            {isDownloading ? "Downloading..." : "Download Resource"}
          </Button>
        );
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary-color" />
          <p className="text-muted-foreground animate-pulse">
            Loading resource...
          </p>
        </div>
      </div>
    );
  }

  // handle invalid id
  if (isError || !resource) {
    return (
      <div className="container mx-auto p-4">
        <Card className="p-16 text-center border-dashed">
          <BookOpen
            size={48}
            className="mx-auto mb-4 text-muted-foreground/30"
          />
          <h2 className="text-xl font-semibold mb-2">Resource not found</h2>
          <p className="text-muted-foreground mb-6">
            This resource doesn't exist or has been removed.
          </p>
          <Button onClick={() => navigate("/resources")}>
            Back to Resources
          </Button>
        </Card>
      </div>
    );
  }

  const TypeIcon = getTypeIcon(resource.type);

  return (
    <div className="container mx-auto p-4 max-w-4xl space-y-6 animate-in fade-in duration-300">
      <Button
        variant="ghost"
        onClick={() => navigate("/resources")}
        className="gap-2 pl-0 hover:bg-transparent hover:text-primary"
      >
        <ArrowLeft size={16} />
        Back to Resources
      </Button>

      <PageHeader
        title={resource.title}
        description={resource.description}
        variant="green"
        badgeText={`${resource.category} • ${resource.type.charAt(0).toUpperCase() + resource.type.slice(1)}`}
        action={
          <div className="hidden md:flex gap-4 items-center bg-white/10 p-3 rounded-xl backdrop-blur-sm">
            <div className="text-center">
              <div className="text-xl font-bold text-white">
                {resource.rating}
              </div>
              <div className="text-[10px] text-white/80 uppercase">Rating</div>
            </div>
            <div className="w-px bg-white/20 h-8"></div>
            <div className="text-center">
              <div className="text-xl font-bold text-white">
                {resource.language.slice(0, 2).toUpperCase()}
              </div>
              <div className="text-[10px] text-white/80 uppercase">Lang</div>
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Locked State */}
          {resource.requires_auth && !isAuthenticated && (
            <Card className="p-6 bg-warning/5 border-warning/20 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center shrink-0">
                  <Lock className="text-warning-foreground" size={24} />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-warning-foreground">
                    Login Required
                  </h3>
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
              <h3 className="font-bold mb-3 text-xs uppercase tracking-wide text-muted-foreground">
                Topics Covered
              </h3>
              <ul className="grid sm:grid-cols-2 gap-2 text-sm">
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  Introduction to Key Concepts
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  Advanced Methodologies
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  Case Studies & Analysis
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                  Implementation Guide
                </li>
              </ul>
            </div>
          </Card>

          {/* Tags */}
          {resource.tags && resource.tags.length > 0 && (
            <Card className="p-6 border-border/60 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Tags</h2>
              <div className="flex flex-wrap gap-2">
                {resource.tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="hover:bg-secondary/20 transition-colors cursor-pointer px-3 py-1"
                  >
                    #{tag}
                  </Badge>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
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
                onClick={() => toast.info("Opening Preview...")}
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
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium capitalize">{resource.type}</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Category</span>
                <span className="font-medium">{resource.category}</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Language</span>
                <span className="font-medium flex items-center gap-1">
                  <Globe size={12} />
                  {resource.language}
                </span>
              </div>
              {resource.downloads && (
                <div className="flex justify-between border-b border-border/50 pb-2">
                  <span className="text-muted-foreground">Downloads</span>
                  <span className="font-medium">
                    {resource.downloads.toLocaleString()}
                  </span>
                </div>
              )}
              {resource.duration && (
                <div className="flex justify-between border-b border-border/50 pb-2">
                  <span className="text-muted-foreground">Duration</span>
                  <span className="font-medium flex items-center gap-1">
                    <Clock size={12} />
                    {resource.duration}
                  </span>
                </div>
              )}
              {resource.author && (
                <div className="flex justify-between pt-1">
                  <span className="text-muted-foreground">Author</span>
                  <span
                    className="font-medium truncate max-w-[150px]"
                    title={resource.author}
                  >
                    {resource.author}
                  </span>
                </div>
              )}
            </div>
          </Card>

          <Card className="p-6 border-border/60 shadow-sm">
            <h3 className="font-semibold mb-4">Rate This Resource</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    size={28}
                    className={`cursor-pointer transition-colors ${
                      star <= (hoveredStar || selectedRating)
                        ? "fill-yellow-400 text-yellow-400"
                        : "text-gray-300"
                    }`}
                    onMouseEnter={() => setHoveredStar(star)}
                    onMouseLeave={() => setHoveredStar(0)}
                    onClick={() => setSelectedRating(star)}
                  />
                ))}
                {selectedRating > 0 && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    {selectedRating}/5
                  </span>
                )}
              </div>
              {selectedRating > 0 && (
                <div className="space-y-3">
                  <Textarea
                    placeholder="Write a review (optional)..."
                    value={review}
                    onChange={(e) => setReview(e.target.value)}
                    rows={3}
                    className="resize-none bg-muted/30"
                  />
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => ratingMutation.mutate()}
                    disabled={ratingMutation.isPending}
                    style={{
                      backgroundColor: "hsl(var(--primary))",
                      color: "white",
                    }}
                  >
                    {ratingMutation.isPending
                      ? "Submitting..."
                      : "Submit Rating"}
                  </Button>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Current average: {resource.rating} / 5
              </p>
            </div>
          </Card>

          {(resource.type === "course" || resource.type === "video") && (
            <Card className="p-6 border-border/60 shadow-sm">
              <h3 className="font-semibold mb-4">Your Progress</h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Completion</span>
                  <span className="font-medium text-primary-color">
                    {progress}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={progress}
                  onChange={(e) => setProgress(Number(e.target.value))}
                  className="w-full accent-primary"
                />
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-color rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => progressMutation.mutate()}
                  disabled={progressMutation.isPending}
                >
                  {progressMutation.isPending ? "Saving..." : "Save Progress"}
                </Button>
              </div>
            </Card>
          )}
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
                  <Play
                    size={80}
                    className="mb-6 text-primary drop-shadow-lg cursor-pointer hover:scale-110 transition-transform"
                  />
                  <h3 className="text-2xl font-bold mb-2 tracking-tight">
                    {resource.title}
                  </h3>
                  <p className="text-slate-300 max-w-lg mx-auto text-lg">
                    Mock Video Player — in production this would be an embedded
                    video stream.
                  </p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
