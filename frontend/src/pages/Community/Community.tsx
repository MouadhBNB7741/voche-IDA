import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback } from '../../components/ui/avatar';
import {
  MessageSquare,
  Heart,
  Reply,
  Plus,
  TrendingUp,
  Clock,
  Users,
  Search,
  Filter,
  Trash2
} from 'lucide-react';
import { Input } from '../../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { PageHeader } from '../../components/ui/PageHeader';
import { useData } from '../../contexts/DataContext';

const categories = [
  { id: 'all',      name: 'All Discussions',          count: 156, dot: 'bg-primary-color',   activeClass: 'category-active-blue-bg' },
  { id: 'hiv',      name: 'HIV/AIDS',                 count: 45,  dot: 'bg-red-500',          activeClass: 'category-active-blue-bg'     },
  { id: 'tb',       name: 'Tuberculosis',             count: 23,  dot: 'bg-blue-500',         activeClass: 'category-active-blue-bg'    },
  { id: 'malaria',  name: 'Malaria',                  count: 18,  dot: 'bg-green-500',        activeClass: 'category-active-blue-bg'   },
  { id: 'amr',      name: 'Antimicrobial Resistance', count: 12,  dot: 'bg-yellow-500',       activeClass: 'category-active-blue-bg'  },
  { id: 'vaccines', name: 'Vaccines',                 count: 34,  dot: 'bg-purple-500',       activeClass: 'category-active-blue-bg'  },
  { id: 'general',  name: 'General Health',           count: 24,  dot: 'bg-teal-color',       activeClass: 'category-active-blue-bg'    },
];

export default function Community() {
  const navigate = useNavigate();
  const { state, actions } = useData();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [likedPosts, setLikedPosts] = useState<string[]>([]);
  const [isNewPostOpen, setIsNewPostOpen] = useState(false);

  // New Post Form State
  const [newPostTitle, setNewPostTitle] = useState('');
  const [newPostContent, setNewPostContent] = useState('');
  const [newPostCategory, setNewPostCategory] = useState('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Filter posts based on search and filters
  const filteredPosts = state.forumPosts.filter(post => {
    const matchesSearch = post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.content.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' ||
      post.category.toLowerCase().replace('/', '').includes(selectedCategory);
    return matchesSearch && matchesCategory;
  });

  // Calculate pagination
  const totalPages = Math.ceil(filteredPosts.length / itemsPerPage);
  const paginatedPosts = filteredPosts.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handlePageChange = (newPage: number) => {
    if (newPage > 0 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const toggleLike = (postId: string) => {
    setLikedPosts(prev => {
      const isLiked = prev.includes(postId);
      if (isLiked) {
        return prev.filter(id => id !== postId);
      } else {
        toast.success("Post Liked");
        return [...prev, postId];
      }
    });
  };

  const handleDeletePost = (postId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this discussion?")) {
      actions.deletePost(postId);
      toast.success("Discussion deleted successfully");
    }
  };

  const handleCreatePost = () => {
    if (!newPostTitle || !newPostContent || !newPostCategory) {
      toast.error("Please fill in all fields");
      return;
    }

    actions.createPost({
      title: newPostTitle,
      content: newPostContent,
      category: newPostCategory,
      author: state.currentUser?.name || 'Anonymous',
      tags: ['discussion', 'community']
    });

    toast.success("Discussion Created", { description: "Your post has been published to the community." });
    setIsNewPostOpen(false);
    setNewPostTitle('');
    setNewPostContent('');
    setNewPostCategory('');
    setCurrentPage(1);
  };

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title="Community Forum"
        description="Connect, share experiences, and support each other on the journey to better health."
        badgeText="Safe & Supportive Community"
        variant="green"
        action={
          <Dialog open={isNewPostOpen} onOpenChange={setIsNewPostOpen}>
            <DialogTrigger asChild>
              <Button variant="hero" className="gap-2 font-semibold transition-transform hover:scale-105">
                <Plus size={20} />
                Start Discussion
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[525px]">
              <DialogHeader>
                <DialogTitle>Start a New Discussion</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="title" className="text-right">Title</Label>
                  <Input
                    id="title"
                    className="col-span-3"
                    placeholder="What's on your mind?"
                    value={newPostTitle}
                    onChange={(e) => setNewPostTitle(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="category" className="text-right">Category</Label>
                  <Select onValueChange={setNewPostCategory} value={newPostCategory}>
                    <SelectTrigger className="col-span-3">
                      <SelectValue placeholder="Select a topic" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.filter(c => c.id !== 'all').map(c => (
                        <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-4 items-start gap-4">
                  <Label htmlFor="content" className="text-right pt-2">Content</Label>
                  <Textarea
                    id="content"
                    className="col-span-3 min-h-[120px]"
                    placeholder="Share your detailed thoughts or question..."
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleCreatePost}>Post Discussion</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {categories.map((category) => (
          <div
            key={category.id}
            className={`p-4 rounded-xl cursor-pointer transition-all duration-200 flex flex-col items-center text-center gap-2
              ${selectedCategory === category.id
                ? `${category.activeClass} shadow-md scale-105`
                : 'bg-card hover:bg-muted/50 hover:shadow-sm'
              }`}
            onClick={() => { setSelectedCategory(category.id); setCurrentPage(1); }}
          >
            <div className={`w-3 h-3 rounded-full ${category.dot}`} />
            <h3 className="font-semibold text-xs md:text-sm">{category.name}</h3>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              selectedCategory === category.id
                ? 'bg-white/20 text-white'
                : 'text-muted-foreground bg-muted-foreground/10'
            }`}>
              {category.count}
            </span>
          </div>
        ))}
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-muted/30 p-4 rounded-xl border border-muted">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search discussions by topic, title, or keywords..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            className="pl-10 bg-background border-input/50"
          />
        </div>
        <div className="flex gap-2">
          <Select value={sortBy} onValueChange={(v) => { setSortBy(v); setCurrentPage(1); }}>
            <SelectTrigger className="w-[180px] bg-background">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most Recent</SelectItem>
              <SelectItem value="popular">Most Popular</SelectItem>
              <SelectItem value="replies">Most Replies</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" className="bg-background">
            <Filter size={16} />
          </Button>
        </div>
      </div>

      {/* Forum Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Users, label: 'Active Members', value: '2,847', color: 'text-primary-color' },
          { icon: MessageSquare, label: 'Discussions', value: '156', color: 'text-blue-500' },
          { icon: Reply, label: 'Total Replies', value: '834', color: 'text-accent-color' },
          { icon: TrendingUp, label: 'This Week', value: '+67', color: 'text-success-color' },
        ].map((stat, i) => (
          <Card key={i} className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
            <div className={`p-3 rounded-xl bg-muted/50 ${stat.color}`}>
              <stat.icon size={24} />
            </div>
          </Card>
        ))}
      </div>

      {/* Posts List */}
      <div className="space-y-4">
        {paginatedPosts.map((post) => {
          const isAuthor = post.userId === state.currentUser?.id;
          return (
            <Card
              key={post.id}
              className="group p-6 hover:shadow-lg transition-all duration-300 cursor-pointer border-transparent hover:border-primary/10 relative"
              onClick={() => navigate(`/community/posts/${post.id}`)}
            >
              {isAuthor && (
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={(e) => handleDeletePost(post.id, e)}
                  >
                    <Trash2 size={16} />
                  </Button>
                </div>
              )}

              <div className="flex gap-4">
                <Avatar className="w-12 h-12 shadow-sm bg-primary-color group-hover:scale-105 transition-transform">
                  <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground font-bold">
                    {post.author.split(' ').map((n: string) => n[0]).join('')}
                  </AvatarFallback>
                </Avatar>

                <div className="flex-1 space-y-3">
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-2">
                    <div className="space-y-1">
                      <h3 className="text-lg font-bold group-hover:text-primary transition-colors">{post.title}</h3>
                      <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">{post.author}</span>
                        <span>•</span>
                        <Clock size={12} />
                        <span>{post.timestamp}</span>
                        <Badge variant="secondary" className="bg-muted text-muted-foreground">
                          {post.category}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <p className="text-muted-foreground leading-relaxed line-clamp-2">
                    {post.content}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    {post.tags.map((tag: string) => (
                      <Badge key={tag} variant="outline" className="text-xs bg-muted/20 border-muted">
                        #{tag}
                      </Badge>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-dashed border-border">
                    <div className="flex items-center gap-4 text-sm font-medium">
                      <button
                        className={`flex items-center gap-1.5 transition-colors hover:text-red-500
                        ${likedPosts.includes(post.id) ? 'text-red-500' : 'text-muted-foreground'}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleLike(post.id);
                        }}
                      >
                        <Heart size={16} className={likedPosts.includes(post.id) ? 'fill-current' : ''} />
                        {post.likes + (likedPosts.includes(post.id) ? 1 : 0)}
                      </button>
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Reply size={16} />
                        {post.replies} Replies
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="ghost" className="text-primary-color hover:text-primary hover:bg-primary/5">
                        View Discussion
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {filteredPosts.length > itemsPerPage && (
        <div className="flex justify-center items-center gap-4 py-8">
          <Button
            variant="outline"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <span className="text-sm font-medium">Page {currentPage} of {totalPages}</span>
          <Button
            variant="outline"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}

      {filteredPosts.length === 0 && (
        <Card className="p-12 text-center border-dashed bg-muted/30">
          <MessageSquare size={48} className="mx-auto mb-4 text-muted-foreground opacity-30" />
          <h3 className="text-lg font-medium mb-2">No discussions found</h3>
          <p className="text-sm text-muted-foreground mb-6">
            Try adjusting your search or be the first to start a new topic!
          </p>
          <Button className="gap-2 shadow-md" onClick={() => setIsNewPostOpen(true)}>
            <Plus size={16} />
            Start New Discussion
          </Button>
        </Card>
      )}
    </div>
  );
}
