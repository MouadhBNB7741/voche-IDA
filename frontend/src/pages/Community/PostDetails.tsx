import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { PageHeader } from '../../components/ui/PageHeader';
import {
  usePostById,
  useReplies,
  useCreateReply,
  useLikePost,
  useLikeReply,
  useReportContent,
} from '../../hooks/useCommunity';

const reportReasons = [
  { value: 'spam',           label: 'Spam' },
  { value: 'misinformation', label: 'Misinformation' },
  { value: 'harassment',     label: 'Harassment / Abuse' },
  { value: 'other',          label: 'Other' },
];

export default function PostDetail() {
  const { communityId, postId } = useParams<{ communityId: string; postId: string }>();
  const navigate = useNavigate();

  const { data: post, isLoading, error } = usePostById(communityId, postId);
  const { data: replies = [], isLoading: isLoadingReplies } = useReplies(communityId, postId);
  const createReply = useCreateReply(communityId ?? '', postId ?? '');
  const likePost = useLikePost(communityId ?? '');
  const likeReply = useLikeReply(communityId ?? '', postId ?? '');
  const reportContent = useReportContent(communityId ?? '');

  const [isLiked, setIsLiked] = useState(false);
  const [likedReplies, setLikedReplies] = useState<string[]>([]);
  const [replyText, setReplyText] = useState('');

  // Report modal state
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportTarget, setReportTarget] = useState<{ type: 'post' | 'reply'; id: string } | null>(null);
  const [reportReason, setReportReason] = useState('');

  const handleLike = () => {
    if (!post || isLiked) return;
    likePost.mutate(post.post_id);
    setIsLiked(true);
  };

  const handleReplyLike = (replyId: string) => {
    if (likedReplies.includes(replyId)) return;
    likeReply.mutate(replyId);
    setLikedReplies(prev => [...prev, replyId]);
    toast.success('Reply Liked');
  };

  const handleSubmitReply = async () => {
    if (!replyText.trim()) return;
    await createReply.mutateAsync({ content: replyText });
    setReplyText('');
  };

  const openReportModal = (type: 'post' | 'reply', targetId: string) => {
    setReportTarget({ type, id: targetId });
    setReportReason('');
    setShowReportModal(true);
  };

  const handleSubmitReport = async () => {
    if (!reportTarget || !reportReason) return;
    await reportContent.mutateAsync({
      target_type: reportTarget.type === 'reply' ? 'comment' : 'post',
      target_id: reportTarget.id,
      reason: reportReason,
    });
    setShowReportModal(false);
    setReportTarget(null);
    setReportReason('');
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto p-4 md:p-8 max-w-4xl space-y-6">
        <div className="h-9 w-32 bg-muted rounded animate-pulse" />
        <div className="h-40 bg-muted rounded-2xl animate-pulse" />
        <div className="h-64 bg-muted rounded-2xl animate-pulse" />
        <div className="h-48 bg-muted rounded-2xl animate-pulse" />
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

  const likeCount = post.likes_count + (isLiked ? 1 : 0);

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
          <Button
            variant="outline"
            className="border-white/30 text-white hover:bg-white/10"
            onClick={() => openReportModal('post', post.post_id)}
          >
            <Flag size={16} className="mr-2" />
            Report
          </Button>
        }
      />

      {/* Original Post */}
      <Card className="p-6 md:p-8 border-border/60 shadow-sm relative overflow-hidden">
        <div className="flex gap-4">
          <Avatar className="w-14 h-14 border-2 border-primary/20 shadow-sm">
            <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground text-xl font-bold">
              {(post.author_name ?? 'AN').split(' ').map(n => n[0]).join('')}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 space-y-4">
            <div>
              <h1 className="text-2xl font-bold mb-2 tracking-tight">{post.title}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <Clock size={12} />
                <span>{new Date(post.created_at).toLocaleDateString()}</span>
                {post.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="bg-muted text-muted-foreground hover:bg-muted/80">
                    #{tag}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="prose dark:prose-invert max-w-none text-foreground/90 leading-relaxed">
              <p className="whitespace-pre-wrap">{post.content}</p>
            </div>

            <div className="flex items-center justify-between pt-6 border-t border-dashed">
              <div className="flex items-center gap-4">
                <Button
                  variant={isLiked ? 'secondary' : 'ghost'}
                  size="sm"
                  className={`gap-2 transition-all ${isLiked ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20' : 'hover:bg-red-500/5 hover:text-red-500'}`}
                  onClick={handleLike}
                  disabled={isLiked}
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
              <Card key={i} className="p-6">
                <div className="animate-pulse flex gap-4">
                  <div className="w-10 h-10 bg-muted rounded-full shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-1/4 bg-muted rounded" />
                    <div className="h-4 w-full bg-muted rounded" />
                    <div className="h-4 w-3/4 bg-muted rounded" />
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
            return (
              <Card key={reply.comment_id} className="p-6 hover:bg-muted/10 transition-colors border-border/40">
                <div className="flex gap-4">
                  <Avatar className="w-10 h-10 border border-border">
                    <AvatarFallback className="bg-muted text-muted-foreground">
                      <User size={16} />
                    </AvatarFallback>
                  </Avatar>

                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-semibold">Community Member</span>
                        <span className="text-muted-foreground">•</span>
                        <span className="text-muted-foreground text-xs">
                          {new Date(reply.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-muted-foreground hover:text-destructive"
                        onClick={() => openReportModal('reply', reply.comment_id)}
                      >
                        <Flag size={12} />
                      </Button>
                    </div>

                    <p className="text-sm text-foreground/90 leading-relaxed mb-4">
                      {reply.content}
                    </p>

                    <Button
                      variant="ghost"
                      size="sm"
                      className={`h-8 px-2 gap-1.5 text-xs ${isReplyLiked ? 'text-red-500 bg-red-500/5' : 'text-muted-foreground hover:text-red-500'}`}
                      onClick={() => handleReplyLike(reply.comment_id)}
                      disabled={isReplyLiked}
                    >
                      <Heart size={14} className={isReplyLiked ? 'fill-current' : ''} />
                      {reply.likes_count + (isReplyLiked ? 1 : 0)}
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

      {/* Report Modal */}
      <Dialog open={showReportModal} onOpenChange={setShowReportModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Report {reportTarget?.type === 'post' ? 'Post' : 'Reply'}</DialogTitle>
            <DialogDescription>
              Help us keep the community safe. Please select a reason for reporting this content.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Reason for Report</Label>
              <Select value={reportReason} onValueChange={setReportReason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a reason" />
                </SelectTrigger>
                <SelectContent>
                  {reportReasons.map(reason => (
                    <SelectItem key={reason.value} value={reason.value}>
                      {reason.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReportModal(false)}>Cancel</Button>
            <Button
              onClick={handleSubmitReport}
              disabled={!reportReason || reportContent.isPending}
              variant="destructive"
            >
              {reportContent.isPending ? 'Submitting...' : 'Submit Report'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}