import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
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
} from "lucide-react";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../../components/ui/dialog";
import { Textarea } from "../../components/ui/textarea";
import { Label } from "../../components/ui/label";
import { toast } from "sonner";
import { PageHeader } from "../../components/ui/PageHeader";
import { useAuth } from "../../contexts/AuthContext";
import type { PostType } from "../../types/db";
import {
  useCommunities,
  useCommunityFeed,
  useCreatePost,
  useLikePost,
} from "../../hooks/useCommunity";

const postTypeOptions: { id: PostType; name: string }[] = [
  { id: "question", name: "Question" },
  { id: "story", name: "Story" },
  { id: "discussion", name: "Discussion" },
  { id: "announcement", name: "Announcement" },
];

export default function Community() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: communities = [], isLoading: isLoadingCommunities } =
    useCommunities();
  const {
    data: feedPosts = [],
    isLoading: isLoadingFeed,
    error: feedError,
  } = useCommunityFeed();

  const [selectedCommunityId, setSelectedCommunityId] = useState<string>("");
  const activeCommunityId =
    selectedCommunityId || communities[0]?.community_id || "";

  const createPost = useCreatePost(activeCommunityId);
  const likePost = useLikePost(activeCommunityId);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState("recent");
  const [likedPosts, setLikedPosts] = useState<string[]>([]);
  const [isNewPostOpen, setIsNewPostOpen] = useState(false);

  // New Post Form State
  const [newPostTitle, setNewPostTitle] = useState("");
  const [newPostContent, setNewPostContent] = useState("");
  const [newPostType, setNewPostType] = useState<PostType | "">("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Filter posts
  const filteredPosts = feedPosts.filter((post) => {
    const matchesSearch =
      post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      post.content.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" ||
      post.community_id === selectedCategory ||
      post.post_type.toLowerCase() === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Sort posts
  const sortedPosts = [...filteredPosts].sort((a, b) => {
    if (sortBy === "popular") return b.likes_count - a.likes_count;
    if (sortBy === "replies") return b.replies_count - a.replies_count;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const totalPages = Math.ceil(sortedPosts.length / itemsPerPage);
  const paginatedPosts = sortedPosts.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );

  const handlePageChange = (newPage: number) => {
    if (newPage > 0 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleToggleLike = (postId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const isLiked = likedPosts.includes(postId);
    if (!isLiked) {
      likePost.mutate(postId);
      setLikedPosts((prev) => [...prev, postId]);
    } else {
      setLikedPosts((prev) => prev.filter((id) => id !== postId));
    }
  };

  const handleCreatePost = async () => {
    if (!newPostTitle || !newPostContent || !newPostType) {
      toast.error("Please fill in all fields");
      return;
    }
    if (!activeCommunityId) {
      toast.error("No community available");
      return;
    }

    await createPost.mutateAsync({
      title: newPostTitle,
      content: newPostContent,
      post_type: newPostType,
      tags: ["discussion", "community"],
    });

    setIsNewPostOpen(false);
    setNewPostTitle("");
    setNewPostContent("");
    setNewPostType("");
    setCurrentPage(1);
  };

  // Build category tabs from communities + 'all'
  const categoryTabs = [
    {
      id: "all",
      name: "All Discussions",
      count: feedPosts.length,
      dot: "bg-primary-color",
    },
    ...communities.map((c) => ({
      id: c.community_id,
      name: c.name,
      count: c.post_count,
      dot: "bg-blue-500",
    })),
  ];

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
              <Button
                variant="hero"
                className="gap-2 font-semibold transition-transform hover:scale-105"
              >
                <Plus size={20} />
                Start Discussion
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[525px]">
              <DialogHeader>
                <DialogTitle>Start a New Discussion</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                {/* Community selector */}
                {communities.length > 1 && (
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Label className="text-right">Community</Label>
                    <Select
                      value={activeCommunityId}
                      onValueChange={setSelectedCommunityId}
                    >
                      <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select community" />
                      </SelectTrigger>
                      <SelectContent>
                        {communities.map((c) => (
                          <SelectItem
                            key={c.community_id}
                            value={c.community_id}
                          >
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="title" className="text-right">
                    Title
                  </Label>
                  <Input
                    id="title"
                    className="col-span-3"
                    placeholder="What's on your mind?"
                    value={newPostTitle}
                    onChange={(e) => setNewPostTitle(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="post-type" className="text-right">
                    Type
                  </Label>
                  <Select
                    onValueChange={(v) => setNewPostType(v as PostType)}
                    value={newPostType}
                  >
                    <SelectTrigger className="col-span-3">
                      <SelectValue placeholder="Select a post type" />
                    </SelectTrigger>
                    <SelectContent>
                      {postTypeOptions.map((opt) => (
                        <SelectItem key={opt.id} value={opt.id}>
                          {opt.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-4 items-start gap-4">
                  <Label htmlFor="content" className="text-right pt-2">
                    Content
                  </Label>
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
                <Button
                  onClick={handleCreatePost}
                  disabled={createPost.isPending}
                >
                  {createPost.isPending ? "Posting..." : "Post Discussion"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {isLoadingCommunities
          ? [...Array(7)].map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded-xl animate-pulse" />
            ))
          : categoryTabs.map((category) => (
              <div
                key={category.id}
                className={`p-4 rounded-xl cursor-pointer transition-all duration-200 flex flex-col items-center text-center gap-2
                  ${
                    selectedCategory === category.id
                      ? "bg-primary text-primary-foreground shadow-md scale-105"
                      : "bg-card hover:bg-muted/50 hover:shadow-sm"
                  }`}
                onClick={() => {
                  setSelectedCategory(category.id);
                  setCurrentPage(1);
                }}
              >
                <div className={`w-3 h-3 rounded-full ${category.dot}`} />
                <h3 className="font-semibold text-xs md:text-sm">
                  {category.name}
                </h3>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full ${
                    selectedCategory === category.id
                      ? "bg-white/20 text-white"
                      : "text-muted-foreground bg-muted-foreground/10"
                  }`}
                >
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
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="pl-10 bg-background border-input/50"
          />
        </div>
        <div className="flex gap-2">
          <Select
            value={sortBy}
            onValueChange={(v) => {
              setSortBy(v);
              setCurrentPage(1);
            }}
          >
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
          {
            icon: Users,
            label: "Active Members",
            value: communities
              .reduce((a, c) => a + c.member_count, 0)
              .toLocaleString(),
            color: "text-primary-color",
          },
          {
            icon: MessageSquare,
            label: "Discussions",
            value: feedPosts.length.toString(),
            color: "text-blue-500",
          },
          {
            icon: Reply,
            label: "Total Replies",
            value: feedPosts
              .reduce((a, p) => a + p.replies_count, 0)
              .toString(),
            color: "text-accent-color",
          },
          {
            icon: TrendingUp,
            label: "Communities",
            value: communities.length.toString(),
            color: "text-success-color",
          },
        ].map((stat, i) => (
          <Card
            key={i}
            className="p-4 flex items-center justify-between hover:shadow-md transition-shadow"
          >
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

      {isLoadingFeed ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-6 border-0">
              <div className="animate-pulse flex gap-4">
                <div className="w-12 h-12 bg-muted rounded-full shrink-0" />
                <div className="flex-1 space-y-3">
                  <div className="h-5 w-3/4 bg-muted rounded" />
                  <div className="h-4 w-full bg-muted rounded" />
                  <div className="h-4 w-2/3 bg-muted rounded" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : feedError ? (
        <Card className="p-16 text-center border-0">
          <MessageSquare
            size={48}
            className="mx-auto mb-4 text-muted-foreground opacity-30"
          />
          <h3 className="text-lg font-medium mb-2">
            Failed to load discussions
          </h3>
          <p className="text-sm text-muted-foreground mb-6">
            Something went wrong. Please try again.
          </p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </Card>
      ) : (
        <>
          {/* Posts List */}
          <div className="space-y-4">
            {paginatedPosts.map((post) => {
              const isAuthor = post.user_id === user?.id;
              const isLiked = likedPosts.includes(post.post_id);

              return (
                <Card
                  key={post.post_id}
                  className="group p-6 hover:shadow-lg transition-all duration-300 cursor-pointer border-transparent hover:border-primary/10 relative"
                  onClick={() =>
                    navigate(
                      `/community/${post.community_id}/posts/${post.post_id}`,
                    )
                  }
                >
                  <div className="flex gap-4">
                    <Avatar className="w-12 h-12 shadow-sm bg-primary-color group-hover:scale-105 transition-transform">
                      <AvatarFallback className="bg-gradient-to-br from-primary to-secondary text-primary-foreground font-bold">
                        {(post.author_name ?? "AN")
                          .split(" ")
                          .map((n: string) => n[0])
                          .join("")}
                      </AvatarFallback>
                    </Avatar>

                    <div className="flex-1 space-y-3">
                      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-2">
                        <div className="space-y-1">
                          <h3 className="text-lg font-bold group-hover:text-primary transition-colors">
                            {post.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            <span className="font-medium text-foreground">
                              {post.author_name ?? "Anonymous"}
                            </span>
                            <span>•</span>
                            <Clock size={12} />
                            <span>
                              {new Date(post.created_at).toLocaleDateString()}
                            </span>
                            <Badge
                              variant="secondary"
                              className="bg-muted text-muted-foreground"
                            >
                              {post.post_type}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <p className="text-muted-foreground leading-relaxed line-clamp-2">
                        {post.content}
                      </p>

                      <div className="flex flex-wrap gap-2">
                        {post.tags.map((tag: string) => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-xs bg-muted/20 border-muted"
                          >
                            #{tag}
                          </Badge>
                        ))}
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-dashed border-border">
                        <div className="flex items-center gap-4 text-sm font-medium">
                          <button
                            className={`flex items-center gap-1.5 transition-colors hover:text-red-500 ${isLiked ? "text-red-500" : "text-muted-foreground"}`}
                            onClick={(e) => handleToggleLike(post.post_id, e)}
                          >
                            <Heart
                              size={16}
                              className={isLiked ? "fill-current" : ""}
                            />
                            {post.likes_count + (isLiked ? 1 : 0)}
                          </button>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Reply size={16} />
                            {post.replies_count} Replies
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-primary-color hover:text-primary hover:bg-primary/5"
                        >
                          View Discussion
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Pagination */}
          {sortedPosts.length > itemsPerPage && (
            <div className="flex justify-center items-center gap-4 py-8">
              <Button
                variant="outline"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <span className="text-sm font-medium">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          )}

          {/* Empty State */}
          {sortedPosts.length === 0 && (
            <Card className="p-12 text-center border-dashed bg-muted/30">
              <MessageSquare
                size={48}
                className="mx-auto mb-4 text-muted-foreground opacity-30"
              />
              <h3 className="text-lg font-medium mb-2">No discussions found</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Try adjusting your search or be the first to start a new topic!
              </p>
              <Button
                className="gap-2 shadow-md"
                onClick={() => setIsNewPostOpen(true)}
              >
                <Plus size={16} />
                Start New Discussion
              </Button>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
