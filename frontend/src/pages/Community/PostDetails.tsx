import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback } from '../../components/ui/avatar';
import { Textarea } from '../../components/ui/textarea';
import {
  ArrowLeft,
  Heart,
  Reply,
  Flag,
  Clock,
  Send,
  AlertTriangle,
  User,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { PageHeader } from '../../components/ui/PageHeader';
import { ReportModal, type ReportTarget } from '../../components/community/ReportModal';
import {
  ModerationStatusBadge,
  VerifiedHcpBadge,
  moderationHint,
} from '../../components/community/ModerationBadges';
import { useAuthContext } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import {
  usePostById,
  useReplies,
  useCreateReply,
  useLikePost,
  useUnlikePost,
  useLikeReply,
  useUnlikeReply,
  useDeletePost,
  useDeleteReply,
} from '../../hooks/useCommunity';

export default function PostDetail() {
  const { communityId, postId } = useParams<{ communityId: string; postId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user, openAuthModal } = useAuthContext();
  const { theme } = useTheme();
  const isDark = theme === "dark";

  const { data: post, isLoading, error } = usePostById(communityId, postId);
  const { data: replies = [], isLoading: isLoadingReplies } = useReplies(communityId, postId);
  const createReply = useCreateReply(communityId ?? '', postId ?? '');
  const likePost = useLikePost(communityId ?? '');
  const unlikePost = useUnlikePost(communityId ?? '');
  const likeReply = useLikeReply(communityId ?? '', postId ?? '');
  const unlikeReply = useUnlikeReply(communityId ?? '', postId ?? '');
  const deletePostMutation = useDeletePost(communityId ?? '');
  const deleteReplyMutation = useDeleteReply(communityId ?? '', postId ?? '');

  const [isLiked, setIsLiked] = useState(false);
  const [likedReplies, setLikedReplies] = useState<string[]>([]);
  const [replyText, setReplyText] = useState('');

  const [reportedItems, setReportedItems] = useState<string[]>([]);

  useEffect(() => {
    if (post) {
      setIsLiked(post.is_liked_by_me || false);
    }
  }, [post?.post_id, post?.is_liked_by_me]);

  useEffect(() => {
    if (replies) {
      const likedIds = replies
        .filter((r: any) => r.is_liked_by_me)
        .map((r: any) => r.comment_id);
      
      setLikedReplies(prev => {
        if (prev.length === likedIds.length && prev.every((val, index) => val === likedIds[index])) {
          return prev;
        }
        return likedIds;
      });
    }
  }, [replies]);

  // Report modal state
  const [reportTarget, setReportTarget] = useState<ReportTarget | null>(null);

  // Delete confirmation modal state
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'post' | 'reply'; id: string } | null>(null);

  const handleLike = () => {
    if (!isAuthenticated) {
      openAuthModal("Sign in to your Voche account to react to community posts.");
      return;
    }
    if (!post) return;
    if (isLiked) {
      unlikePost.mutate(post.post_id);
      setIsLiked(false);
      toast.success('Post Unliked');
    } else {
      likePost.mutate(post.post_id);
      setIsLiked(true);
      toast.success('Post Liked');
    }
  };

  const handleReplyLike = (replyId: string) => {
    if (!isAuthenticated) {
      openAuthModal("Sign in to your Voche account to react to replies.");
      return;
    }
    const isReplyLiked = likedReplies.includes(replyId);
    if (isReplyLiked) {
      unlikeReply.mutate(replyId);
      setLikedReplies(prev => prev.filter(id => id !== replyId));
      toast.success('Reply Unliked');
    } else {
      likeReply.mutate(replyId);
      setLikedReplies(prev => [...prev, replyId]);
      toast.success('Reply Liked');
    }
  };

  const handleSubmitReply = async () => {
    if (!isAuthenticated) {
      openAuthModal("Sign in to your Voche account to reply to discussions.");
      return;
    }
    if (!replyText.trim()) return;
    await createReply.mutateAsync({ content: replyText });
    setReplyText('');
  };

  const openReportModal = (type: 'post' | 'comment', targetId: string) => {
    if (!isAuthenticated) {
      openAuthModal("Sign in to your Voche account to report inappropriate content.");
      return;
    }
    setReportTarget({ type, id: targetId });
  };

  const handleDeletePostClick = () => {
    if (!post) return;
    setDeleteTarget({ type: 'post', id: post.post_id });
  };

  const handleDeleteReplyClick = (replyId: string) => {
    setDeleteTarget({ type: 'reply', id: replyId });
  };

  const executeDelete = async () => {
    if (!deleteTarget) return;
    try {
      if (deleteTarget.type === 'post') {
        await deletePostMutation.mutateAsync(deleteTarget.id);
        setDeleteTarget(null);
        navigate('/community');
      } else {
        await deleteReplyMutation.mutateAsync(deleteTarget.id);
        setDeleteTarget(null);
      }
    } catch (err) {
      // Error is handled by the delete mutations
      setDeleteTarget(null);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto p-4 md:p-8 max-w-4xl space-y-6">
        <Skeleton className="h-9 w-32" />
        
        {/* Page title area skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
        </div>

        {/* Post body skeleton */}
        <Card className="p-6 md:p-8 space-y-4 border-0">
          <div className="flex gap-4">
            <Skeleton className="w-14 h-14 rounded-full shrink-0" />
            <div className="flex-1 space-y-3">
              <Skeleton className="h-6 w-1/2" />
              <div className="flex gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          </div>
          <div className="space-y-2 pt-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <div className="border-t border-dashed pt-4 flex gap-4">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
          </div>
        </Card>

        {/* Replies loading skeleton */}
        <div className="space-y-4 pt-4">
          <Skeleton className="h-6 w-32" />
          {[...Array(2)].map((_, i) => (
            <Card key={i} className="p-6 border-0">
              <div className="flex gap-4">
                <Skeleton className="w-10 h-10 rounded-full shrink-0" />
                <div className="flex-1 space-y-3">
                  <Skeleton className="h-4 w-1/4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-5/6" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="container mx-auto p-4 md:p-8">
        <Button variant="ghost" onClick={() => navigate('/community')} className="gap-2 pl-0 mb-6">
          <ArrowLeft size={16} />
          Back to Community
        </Button>
        <Card className="p-16 text-center border-dashed">
          <AlertTriangle className="mx-auto mb-4 text-muted-foreground opacity-50" size={64} />
          <h2 className="text-xl font-semibold mb-2">Post not found</h2>
          <p className="text-muted-foreground mb-6">
            This discussion may have been removed or doesn't exist.
          </p>
          <Button onClick={() => navigate('/community')}>Back to Community</Button>
        </Card>
      </div>
    );
  }

  const initialLiked = post.is_liked_by_me || false;
  let likeCount = post.likes_count;
  if (isLiked && !initialLiked) {
    likeCount += 1;
  } else if (!isLiked && initialLiked) {
    likeCount = Math.max(0, likeCount - 1);
  }

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-4xl space-y-6 animate-in fade-in duration-300">
      <Button variant="ghost" onClick={() => navigate('/community')} className="gap-2 pl-0 hover:bg-transparent hover:text-primary">
        <ArrowLeft size={16} />
        Back to Community
      </Button>

      <PageHeader
        title={post.title}
        description={`Posted by ${post.author_name ?? 'Anonymous'} • ${new Date(post.created_at).toLocaleDateString()}`}
        variant="green"
        badgeText={post.post_type}
        action={
          <div className="flex items-center gap-2">
            {post.user_id === user?.id && (
              <Button
                variant="destructive"
                className="cursor-pointer bg-red-650 hover:bg-red-750 text-white flex items-center gap-1.5"
                onClick={handleDeletePostClick}
                disabled={deletePostMutation.isPending}
              >
                <Trash2 size={16} />
                Delete Post
              </Button>
            )}
            {post.user_id !== user?.id && !reportedItems.includes(post.post_id) && (
              <Button
                variant="outline"
                className="border-white/30 text-white hover:bg-white/10 cursor-pointer"
                onClick={() => openReportModal('post', post.post_id)}
              >
                <Flag size={16} className="mr-2" />
                Report
              </Button>
            )}
          </div>
        }
      />

      {/* Original Post */}
      <Card className="p-6 md:p-8 border-border/60 shadow-sm relative overflow-hidden">
        <div className="flex gap-4">
          <Avatar className="w-14 h-14  shadow-sm">
            <AvatarFallback className="bg-primary-color text-primary-foreground text-xl font-bold">
              {(post.author_name ?? 'AN').split(' ').map(n => n[0]).join('')}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 space-y-4">
            <div>
              <h1 className="text-2xl font-bold mb-2 tracking-tight">{post.title}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <span className="font-semibold text-foreground flex flex-wrap items-center gap-1.5">
                  {post.author_name ?? 'Anonymous'}
                  <VerifiedHcpBadge show={post.author_is_verified_hcp} />
                  {post.user_id === user?.id && (
                    <Badge variant="secondary" className="bg-primary-color/15 text-primary-color border-primary-color/30 text-[10px] py-0 px-2 font-semibold">
                      Author
                    </Badge>
                  )}
                  <ModerationStatusBadge status={post.moderation_status} />
                </span>
                <span>•</span>
                <Clock size={12} />
                <span>{new Date(post.created_at).toLocaleDateString()}</span>
                {post.tags?.map((tag) => (
                  <Badge key={tag} variant="secondary" className="bg-muted text-muted-foreground hover:bg-muted/80">
                    #{tag}
                  </Badge>
                ))}
              </div>
            </div>

            {moderationHint(post.moderation_status) && (
              <p className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
                <ShieldAlert size={16} className="shrink-0" aria-hidden="true" />
                {moderationHint(post.moderation_status)}
              </p>
            )}

            <div className="prose dark:prose-invert max-w-none text-foreground/90 leading-relaxed">
              <p className="whitespace-pre-wrap">{post.content}</p>
            </div>

            <div className="flex items-center justify-between pt-6 border-t border-dashed">
              <div className="flex items-center gap-4">
                <Button
                  variant={isLiked ? 'secondary' : 'ghost'}
                  size="sm"
                  className={`gap-2 transition-all cursor-pointer ${isLiked ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20' : 'hover:bg-red-500/5 hover:text-red-500'}`}
                  onClick={handleLike}
                  disabled={likePost.isPending || unlikePost.isPending}
                >
                  <Heart size={18} className={isLiked ? 'fill-current' : ''} />
                  <span className="text-sm font-medium">{likeCount} Likes</span>
                </Button>
                <div className="flex items-center gap-2 text-sm text-muted-foreground px-3 py-1.5">
                  <Reply size={18} />
                  <span>{replies.length} Replies</span>
                </div>
              </div>
              <Button
                onClick={() => document.getElementById('reply-area')?.focus()}
                variant="default"
                size="sm"
                className="shadow-sm"
              >
                Reply to Discussion
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <div className="space-y-6">
        <h2 className="text-xl font-bold flex items-center gap-2">
          Replies{' '}
          <span className="text-muted-foreground text-base font-normal">
            ({replies.length})
          </span>
        </h2>

        {isLoadingReplies ? (
          <div className="space-y-4">
            {[...Array(2)].map((_, i) => (
              <Card key={i} className="p-6 border-0">
                <div className="flex gap-4">
                  <Skeleton className="w-10 h-10 rounded-full shrink-0" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-1/4" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : replies.length === 0 ? (
          <Card className="p-8 text-center border-dashed text-muted-foreground">
            <Reply size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No replies yet. Be the first to respond!</p>
          </Card>
        ) : (
          replies.map((reply) => {
            const isReplyLiked = likedReplies.includes(reply.comment_id);
            const initialReplyLiked = reply.is_liked_by_me || false;
            let replyLikesCount = reply.likes_count;
            if (isReplyLiked && !initialReplyLiked) {
              replyLikesCount += 1;
            } else if (!isReplyLiked && initialReplyLiked) {
              replyLikesCount = Math.max(0, replyLikesCount - 1);
            }

            return (
              <Card key={reply.comment_id} className="p-6 hover:bg-muted/10 transition-colors border-border/40">
                <div className="flex gap-4">
                  <Avatar className="w-10 h-10 shadow-sm bg-primary-color shrink-0">
                    <AvatarFallback className="bg-primary from-primary to-secondary text-primary-foreground font-bold text-xs">
                      {(reply.author_name ?? 'CM')
                        .split(' ')
                        .map((n: string) => n[0])
                        .join('')}
                    </AvatarFallback>
                  </Avatar>

                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-semibold">{reply.author_name ?? 'Community Member'}</span>
                        <VerifiedHcpBadge show={reply.author_is_verified_hcp} />
                        {reply.user_id === post.user_id && (
                          <Badge variant="secondary" className="bg-primary-color/10 text-primary-color border-primary-color/20 text-[9px] py-0 px-1.5 font-semibold">
                            Author
                          </Badge>
                        )}
                        <ModerationStatusBadge status={reply.moderation_status} />
                        <span className="text-muted-foreground">•</span>
                        <span className="text-muted-foreground text-xs">
                          {new Date(reply.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {reply.user_id === user?.id && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-red-500 hover:text-red-700 hover:bg-red-500/10 cursor-pointer"
                            onClick={() => handleDeleteReplyClick(reply.comment_id)}
                            disabled={deleteReplyMutation.isPending}
                          >
                            <Trash2 size={13} />
                          </Button>
                        )}
                        {reply.user_id !== user?.id && !reportedItems.includes(reply.comment_id) && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive cursor-pointer"
                            onClick={() => openReportModal('comment', reply.comment_id)}
                            aria-label="Report this reply"
                            title="Report this reply"
                          >
                            <Flag size={13} />
                          </Button>
                        )}
                      </div>
                    </div>

                    <p className="text-sm text-foreground/90 leading-relaxed mb-4">
                      {reply.content}
                    </p>

                    <Button
                      variant="ghost"
                      size="sm"
                      className={`h-8 px-2 gap-1.5 text-xs cursor-pointer ${isReplyLiked ? 'text-red-500 bg-red-500/5' : 'text-muted-foreground hover:text-red-500'}`}
                      onClick={() => handleReplyLike(reply.comment_id)}
                      disabled={likeReply.isPending || unlikeReply.isPending}
                    >
                      <Heart size={14} className={isReplyLiked ? 'fill-current' : ''} />
                      {replyLikesCount}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })
        )}
      </div>

      <Card className="p-6 bg-muted/30 border-muted">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <User size={18} /> Add your reply
        </h3>
        <div className="space-y-4">
          <Textarea
            id="reply-area"
            placeholder="Share your thoughts, ask questions, or provide support..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={4}
            className="bg-background resize-none focus-visible:ring-primary"
          />
          <div className="flex justify-end">
            <Button
              onClick={handleSubmitReply}
              disabled={!replyText.trim() || createReply.isPending}
              className="gap-2 shadow-sm"
            >
              <Send size={16} />
              {createReply.isPending ? 'Posting...' : 'Post Reply'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Community Guidelines */}
      <div className="flex items-start gap-4 p-4 rounded-xl bg-info/10 border border-info/20">
        <ShieldAlert className="text-info shrink-0 mt-0.5" size={20} />
        <div>
          <h4 className="font-semibold text-info mb-1 text-sm">Community Guidelines</h4>
          <p className="text-xs text-muted-foreground leading-relaxed">
            VOCHE is a safe space for support and information. Please be respectful and constructive.
            Medical advice should only come from qualified professionals.
          </p>
        </div>
      </div>

      <ReportModal
        communityId={communityId ?? ''}
        target={reportTarget}
        onClose={() => setReportTarget(null)}
        onReported={(target) => setReportedItems(prev => [...prev, target.id])}
      />

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <DialogContent className={`sm:max-w-[425px] border shadow-xl ${
          !isDark 
            ? "bg-white text-zinc-950 border-zinc-200" 
            : "bg-zinc-900 text-white border-zinc-800"
        }`}>
          <DialogHeader>
            <DialogTitle className={!isDark ? 'text-zinc-950' : 'text-white'}>
              Confirm Deletion
            </DialogTitle>
            <DialogDescription className={!isDark ? 'text-zinc-500' : 'text-zinc-400'}>
              Are you sure you want to delete this {deleteTarget?.type}? This action is permanent and cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 pt-4">
            <Button 
              variant="outline" 
              onClick={() => setDeleteTarget(null)}
              className={`cursor-pointer ${
                !isDark 
                  ? 'border-zinc-200 hover:bg-zinc-50 text-zinc-900' 
                  : 'border-zinc-800 hover:bg-zinc-800 text-white'
              }`}
            >
              Cancel
            </Button>
            <Button
              onClick={executeDelete}
              variant="destructive"
              className="cursor-pointer bg-red-600 text-white hover:bg-red-700 hover:scale-[1.02] active:scale-[0.98] transition-transform"
              disabled={deletePostMutation.isPending || deleteReplyMutation.isPending}
            >
              {(deletePostMutation.isPending || deleteReplyMutation.isPending) ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}