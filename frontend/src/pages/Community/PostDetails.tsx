import { useState, useEffect } from 'react';
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
  ShieldAlert
} from 'lucide-react';
import { mockForumPosts } from '../../data/mockData';
import type { ForumPost } from '../../data/mockData';
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

// Mock replies
const mockReplies = [
  {
    id: '1',
    author: 'Dr. Elena Martinez',
    content: 'Thank you for sharing your experience! I\'ve seen similar outcomes in my practice. The key is maintaining open communication with your healthcare team throughout the trial.',
    timestamp: '1 hour ago',
    likes: 12,
  },
  {
    id: '2',
    author: 'James K.',
    content: 'This is really helpful information. I\'m considering joining a similar trial and was wondering about the consent process. Did you find it straightforward?',
    timestamp: '45 minutes ago',
    likes: 5,
  },
  {
    id: '3',
    author: 'Community Support',
    content: 'Great discussion everyone! Remember that every clinical trial experience is unique. If you have specific questions about eligibility, please consult with the trial coordinators directly.',
    timestamp: '20 minutes ago',
    likes: 8,
  },
];

const reportReasons = [
  { value: 'spam', label: 'Spam' },
  { value: 'misinformation', label: 'Misinformation' },
  { value: 'abuse', label: 'Harassment / Abuse' },
  { value: 'other', label: 'Other' },
];

export default function PostDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [post, setPost] = useState<ForumPost | null>(null);
  const [isLiked, setIsLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [replyText, setReplyText] = useState('');
  const [replies, setReplies] = useState(mockReplies);
  const [likedReplies, setLikedReplies] = useState<string[]>([]);

  // Report modal state
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportTarget, setReportTarget] = useState<{ type: 'post' | 'reply'; id: string } | null>(null);
  const [reportReason, setReportReason] = useState('');

  useEffect(() => {
    if (id) {
      const foundPost = mockForumPosts.find(p => p.id === id);
      setPost(foundPost || null);
      if (foundPost) {
        setLikeCount(foundPost.likes);
      }
    }
  }, [id]);

  const handleLike = () => {
    setIsLiked(!isLiked);
    setLikeCount(prev => isLiked ? prev - 1 : prev + 1);
    if (!isLiked) toast.success("Post Liked");
  };

  const handleReplyLike = (replyId: string) => {
    setLikedReplies(prev => {
      const isLiked = prev.includes(replyId);
      if (!isLiked) toast.success("Reply Liked");
      return isLiked
        ? prev.filter(id => id !== replyId)
        : [...prev, replyId];
    });
  };

  const handleSubmitReply = () => {
    if (!replyText.trim()) return;

    const newReply = {
      id: Date.now().toString(),
      author: 'You',
      content: replyText,
      timestamp: 'Just now',
      likes: 0,
    };

    setReplies(prev => [...prev, newReply]);
    setReplyText('');
    toast.success('Reply Posted', {
      description: 'Your contribution has been added to the discussion.'
    });
  };

  const openReportModal = (type: 'post' | 'reply', targetId: string) => {
    setReportTarget({ type, id: targetId });
    setReportReason('');
    setShowReportModal(true);
  };

  const handleSubmitReport = () => {
    toast.success('Report Submitted', {
      description: 'Thank you for helping keep our community safe. We will review this report shortly.'
    });
    setShowReportModal(false);
    setReportTarget(null);
    setReportReason('');
  };

  if (!post) {
    return (
      <div className="container mx-auto p-4 md:p-8">
        <Card className="p-16 text-center border-dashed">
          <AlertTriangle className="mx-auto mb-4 text-muted-foreground opacity-50" size={64} />
          <h2 className="text-xl font-semibold mb-2">Post not found</h2>
          <Button onClick={() => navigate('/community')}>Back to Community</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-4xl space-y-6 animate-in fade-in duration-300">
      {/* Back Button */}
      <Button variant="ghost" onClick={() => navigate('/community')} className="gap-2 pl-0 hover:bg-transparent hover:text-primary">
        <ArrowLeft size={16} />
        Back to Community
      </Button>

      <PageHeader
        title={post.category === 'General Discussion' ? 'General Discussion' : post.category}
        description={`Posted by ${post.author} • ${post.timestamp}`}
        variant="green"
        badgeText={post.category}
        action={
          <Button
            variant="outline"
            className="border-white/30 text-white hover:bg-white/10"
            onClick={() => openReportModal('post', post.id)}
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
              {post.author.split(' ').map(n => n[0]).join('')}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 space-y-4">
            <div>
              <h1 className="text-2xl font-bold mb-2 tracking-tight">{post.title}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                {post.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="bg-muted text-muted-foreground hover:bg-muted/80">
                    #{tag}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="prose dark:prose-invert max-w-none text-foreground/90 leading-relaxed font-normal">
              <p className="whitespace-pre-wrap">{post.content}</p>
              {/* Mocking extended content for better visual */}
              <p className="whitespace-pre-wrap mt-4">
                I wanted to share some tips for anyone considering participating in a clinical trial:
                <br /><br />
                1. Always read the informed consent document carefully. It explains the purpose, risks, and benefits.
                <br />
                2. Ask questions! Write them down before your appointment.
                <br />
                3. Know your rights. You can withdraw at any time for any reason.
                <br />
                4. Keep a symptom diary to track any side effects or changes.
                <br />
                5. Stay in touch with the study coordinator. They are your primary point of contact.
              </p>
            </div>

            <div className="flex items-center justify-between pt-6 border-t border-dashed">
              <div className="flex items-center gap-4">
                <Button
                  variant={isLiked ? "secondary" : "ghost"}
                  size="sm"
                  className={`gap-2 transition-all ${isLiked ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20' : 'hover:bg-red-500/5 hover:text-red-500'}`}
                  onClick={handleLike}
                >
                  <Heart size={18} className={isLiked ? 'fill-current' : ''} />
                  <span className="text-sm font-medium">{likeCount} Likes</span>
                </Button>
                <div className="flex items-center gap-2 text-sm text-muted-foreground px-3 py-1.5">
                  <Reply size={18} />
                  <span>{replies.length} Replies</span>
                </div>
              </div>
              <Button onClick={() => document.getElementById('reply-area')?.focus()} variant="default" size="sm" className="shadow-sm">
                Reply to Discussion
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Replies Section */}
      <div className="space-y-6">
        <h2 className="text-xl font-bold flex items-center gap-2">
          Replies <span className="text-muted-foreground text-base font-normal">({replies.length})</span>
        </h2>

        {replies.map((reply) => (
          <Card key={reply.id} className="p-6 hover:bg-muted/10 transition-colors border-border/40">
            <div className="flex gap-4">
              <Avatar className="w-10 h-10 border border-border">
                <AvatarFallback className={reply.author === 'You' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}>
                  {reply.author.split(' ').map(n => n[0]).join('')}
                </AvatarFallback>
              </Avatar>

              <div className="flex-1">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold">{reply.author}</span>
                    <span className="text-muted-foreground">•</span>
                    <span className="text-muted-foreground text-xs">{reply.timestamp}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => openReportModal('reply', reply.id)}
                  >
                    <Flag size={12} />
                  </Button>
                </div>

                <p className="text-sm text-foreground/90 leading-relaxed mb-4">{reply.content}</p>

                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-8 px-2 gap-1.5 text-xs ${likedReplies.includes(reply.id) ? 'text-red-500 bg-red-500/5' : 'text-muted-foreground hover:text-red-500'}`}
                  onClick={() => handleReplyLike(reply.id)}
                >
                  <Heart size={14} className={likedReplies.includes(reply.id) ? 'fill-current' : ''} />
                  {reply.likes + (likedReplies.includes(reply.id) ? 1 : 0)}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Reply Form */}
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
            <Button onClick={handleSubmitReply} disabled={!replyText.trim()} className="gap-2 shadow-sm">
              <Send size={16} />
              Post Reply
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
            VOCE is a safe space for support and information. Please be respectful and constructive.
            Medical advice should only come from qualified professionals. content violating our policies will be removed.
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
            <Button variant="outline" onClick={() => setShowReportModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmitReport}
              disabled={!reportReason}
              variant="destructive"
            >
              Submit Report
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}