import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "../../components/ui/skeleton";
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
  FileText,
  Video,
  BookOpen,
  Loader2,
  Star,
} from "lucide-react";
import { resourceService } from "../../services/resourceService";
import type { Resource } from "../../types/db";
import { useAuthContext } from "../../contexts/AuthContext";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { PageHeader } from "../../components/ui/PageHeader";
import { useErrorHandler } from "../../hooks/useErrorHandler";

export default function ResourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user, openAuthModal } = useAuthContext();
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

  const hasUserRated = isAuthenticated && user && resource?.reviews?.some(
    (review: any) => review.user_id === user.id
  );

  const { handleError } = useErrorHandler();

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
    onError: (err) => {
      handleError(err, "Failed to submit rating. Please try again.");
    },
  });

  const progressMutation = useMutation({
    mutationFn: () =>
      resourceService.updateProgress(resource!.resource_id, progress),
    onSuccess: () => {
      toast.success("Progress saved!");
    },
    onError: (err) => {
      handleError(err, "Failed to save progress.");
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

  const saveBlob = (blob: Blob, fileName: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // A real file is downloaded, a link is opened
  const handleDownload = async () => {
    if (!resource || isDownloading || (!resource.has_file && !resource.url)) return;
    setIsDownloading(true);
    try {
      const info = await resourceService.getDownload(resource.resource_id);
      if (info.has_file) {
        const blob = await resourceService.getFile(resource.resource_id);
        saveBlob(blob, info.file_name || resource.file_name || resource.title);
        toast.success("Download complete");
      } else if (info.download_url) {
        window.open(info.download_url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      handleError(err, "Could not download this resource. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };

  // Opens the file in a new tab (PDFs show in the browser), or the link
  const handlePreview = async () => {
    if (!resource) return;
    if (!resource.has_file) {
      if (resource.url) window.open(resource.url, "_blank", "noopener,noreferrer");
      return;
    }
    const tab = window.open("", "_blank");
    try {
      const blob = await resourceService.getFile(resource.resource_id);
      if (tab) {
        const url = window.URL.createObjectURL(blob);
        tab.location.href = url;
        window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
      } else {
        saveBlob(blob, resource.file_name || resource.title);
      }
    } catch (err) {
      tab?.close();
      handleError(err, "Could not open a preview. Please try again.");
    }
  };

  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const closeVideo = (open: boolean) => {
    setIsVideoOpen(open);
    if (!open && videoSrc) {
      window.URL.revokeObjectURL(videoSrc);
      setVideoSrc(null);
    }
  };

  const handleVideoPlay = async () => {
    if (resource && !resource.has_file && resource.url) {
      window.open(resource.url, "_blank", "noopener,noreferrer");
      return;
    }
    setVideoLoading(true);
    setIsVideoOpen(true);
    if (resource?.has_file && resource.file_type?.startsWith("video/")) {
      try {
        const blob = await resourceService.getFile(resource.resource_id);
        setVideoSrc(window.URL.createObjectURL(blob));
      } catch (err) {
        handleError(err, "Could not load this video. Please try again.");
        setIsVideoOpen(false);
      } finally {
        setVideoLoading(false);
      }
      return;
    }
    setVideoLoading(false);
  };

  const getPrimaryAction = () => {
    if (!resource) return null;
    if (!canAccess) {
      return (
        <Button 
          className="w-full gap-2 shadow-md bg-warning hover:bg-warning/90 text-warning-foreground font-semibold cursor-pointer"
          onClick={() => openAuthModal("Sign in to your Voche account to access this resource.")}
        >
          <Lock size={16} />
          Unlock Resource
        </Button>
      );
    }
    if (!resource.has_file && !resource.url) {
      return (
        <Button className="w-full gap-2" disabled>
          <BookOpen size={16} />
          No file or link yet
        </Button>
      );
    }
    switch (resource.type) {
      case "video":
        return (
          <Button className="w-full gap-2 shadow-md cursor-pointer" onClick={handleVideoPlay}>
            <Play size={16} />
            Watch Video
          </Button>
        );
      case "course":
        return (
          <Button
            className="w-full gap-2 shadow-md cursor-pointer"
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? <Loader2 size={16} className="animate-spin" /> : <Award size={16} />}
            Open Course
          </Button>
        );
      default:
        return (
          <Button
            className="w-full gap-2 shadow-md cursor-pointer"
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Download size={16} />
            )}
            {isDownloading ? "Downloading..." : resource.has_file ? "Download Resource" : "Open Resource"}
          </Button>
        );
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto p-4 md:p-8 space-y-6">
        <Skeleton className="h-9 w-32" />
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-12 w-3/4" />
            <div className="flex gap-4 items-center">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
            <Skeleton className="h-[360px] w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
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
          <Button onClick={() => navigate("/resources")} className="cursor-pointer">
            Back to Resources
          </Button>
        </Card>
      </div>
    );
  }

  const TypeIcon = getTypeIcon(resource.type);
  const approval = resource.approval_status ?? "approved";

  return (
    <div className="container mx-auto p-4 max-w-4xl space-y-6 animate-in fade-in duration-300">
      <Button
        variant="ghost"
        onClick={() => navigate("/resources")}
        className="gap-2 pl-0 hover:bg-transparent hover:text-primary-color cursor-pointer"
      >
        <ArrowLeft size={16} />
        Back to Resources
      </Button>

      {approval !== "approved" && (
        <Card className="flex items-start gap-3 p-4 border-dashed" role="status">
          <Clock size={18} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <div className="text-sm">
            {approval === "rejected" ? (
              <>
                <p className="font-semibold">This resource wasn't approved</p>
                {resource.rejection_reason && (
                  <p className="text-muted-foreground">Reason: {resource.rejection_reason}</p>
                )}
              </>
            ) : (
              <>
                <p className="font-semibold">Waiting for review</p>
                <p className="text-muted-foreground">
                  Only you and the admins can see it until it's approved.
                </p>
              </>
            )}
          </div>
        </Card>
      )}

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
          </Card>

          {/* Tags */}
          {resource.tags && resource.tags.length > 0 && (
            <Card className="p-6 border-border/60 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Tags</h2>
              <div className="flex flex-wrap gap-2">
                {resource.tags?.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="bg-secondary-color text-white hover:bg-secondary/90 transition-colors cursor-pointer px-3 py-1 border-none shadow-sm"
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
              {canAccess && resource.type !== "video" && (resource.has_file || resource.url) && (
                <Button
                  variant="outline"
                  className="w-full gap-2 border-dashed border-border cursor-pointer"
                  onClick={handlePreview}
                >
                  <Eye size={16} />
                  Preview Resource
                </Button>
              )}
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
              {resource.downloads > 0 && (
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

          {!hasUserRated ? (
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
                      onClick={() => {
                        if (!isAuthenticated) {
                          openAuthModal("Sign in to your Voche account to rate resources.");
                          return;
                        }
                        setSelectedRating(star);
                      }}
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
                      className="w-full cursor-pointer"
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
          ) : (
            <Card className="p-6 border-border/60 shadow-sm bg-muted/20">
              <h3 className="font-semibold mb-2">Rate This Resource</h3>
              <p className="text-sm text-muted-foreground">
                You have already rated this resource. Thank you for your feedback!
              </p>
              {(() => {
                const userReview = resource.reviews?.find((r) => r.user_id === user?.id);
                if (userReview) {
                  return (
                    <div className="mt-4 pt-4 border-t border-border/50">
                      <div className="flex items-center gap-1 mb-2">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            size={16}
                            className={
                              star <= userReview.rating
                                ? "fill-yellow-400 text-yellow-400"
                                : "text-gray-300"
                            }
                          />
                        ))}
                      </div>
                      {userReview.review && (
                        <p className="text-xs italic text-muted-foreground bg-white/50 p-2 rounded">
                          "{userReview.review}"
                        </p>
                      )}
                    </div>
                  );
                }
                return null;
              })()}
            </Card>
          )}

          {isAuthenticated && (resource.type === "course" || resource.type === "video") && (
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
                  className="w-full cursor-pointer"
                  onClick={() => {
                    if (!isAuthenticated) {
                      openAuthModal("Sign in to your Voche account to save progress.");
                      return;
                    }
                    progressMutation.mutate();
                  }}
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
      <Dialog open={isVideoOpen} onOpenChange={closeVideo}>
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
            ) : videoSrc ? (
              <video src={videoSrc} controls autoPlay className="h-full w-full" aria-label={resource.title} />
            ) : (
              <p className="text-sm text-white/80">This video could not be loaded.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
