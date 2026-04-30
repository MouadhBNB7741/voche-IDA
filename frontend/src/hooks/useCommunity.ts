import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { communityService } from '../services/communityService';
import type { CreatePostPayload, CreateReplyPayload, ReportPayload } from '../services/communityService';


// Fetch all communities 
export function useCommunities() {
  return useQuery({
    queryKey: ['communities'],
    queryFn: communityService.getCommunities,
    retry: false,
  });
}


// Fetch single community
export function useCommunityById(id: string | undefined) {
  return useQuery({
    queryKey: ['community', id],
    queryFn: () => communityService.getCommunityById(id!),
    enabled: !!id,
    retry: false,
  });
}

// Fetch global feed 
export function useCommunityFeed() {
  return useQuery({
    queryKey: ['community', 'feed'],
    queryFn: communityService.getFeed,
    retry: false,
  });
}

// Fetch posts for a specific community
export function useCommunityPosts(communityId: string | undefined) {
  return useQuery({
    queryKey: ['community', communityId, 'posts'],
    queryFn: () => communityService.getPosts(communityId!),
    enabled: !!communityId,
    retry: false,
  });
}

// Fetch a single post with details
export function usePostById(communityId: string | undefined, postId: string | undefined) {
  return useQuery({
    queryKey: ['community', communityId, 'posts', postId],
    queryFn: () => communityService.getPostById(communityId!, postId!),
    enabled: !!communityId && !!postId,
    retry: false,
  });
}

// Create a new post
export function useCreatePost(communityId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreatePostPayload) =>
      communityService.createPost(communityId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['community', communityId, 'posts'] });
      queryClient.invalidateQueries({ queryKey: ['community', 'feed'] });
      toast.success('Discussion Created', {
        description: 'Your post has been published to the community.',
      });
    },

    onError: () => {
      toast.error('Failed to create post', {
        description: 'Something went wrong. Please try again.',
      });
    },
  });
}

// Like a post 
export function useLikePost(communityId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (postId: string) =>
      communityService.likePost(communityId, postId),

    onMutate: async (postId) => {
      await queryClient.cancelQueries({ queryKey: ['community', 'feed'] });
      await queryClient.cancelQueries({ queryKey: ['community', communityId, 'posts'] });

      const previousFeed = queryClient.getQueryData(['community', 'feed']);

      queryClient.setQueryData<any[]>(['community', 'feed'], (old = []) =>
        old.map(post =>
          post.post_id === postId
            ? { ...post, likes_count: post.likes_count + 1 }
            : post
        )
      );

      return { previousFeed };
    },

    onError: (_err, _postId, context) => {
      if (context?.previousFeed) {
        queryClient.setQueryData(['community', 'feed'], context.previousFeed);
      }
      toast.error('Could not like post. Please try again.');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['community', 'feed'] });
      queryClient.invalidateQueries({ queryKey: ['community', communityId, 'posts'] });
    },
  });
}

// Fetch replies for a post
export function useReplies(communityId: string | undefined, postId: string | undefined) {
  return useQuery({
    queryKey: ['community', communityId, 'posts', postId, 'replies'],
    queryFn: () => communityService.getReplies(communityId!, postId!),
    enabled: !!communityId && !!postId,
    retry: false,
  });
}

// Create a reply on a post
export function useCreateReply(communityId: string, postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateReplyPayload) =>
      communityService.createReply(communityId, postId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId, 'replies'],
      });

      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId],
      });
      toast.success('Reply Posted', {
        description: 'Your contribution has been added to the discussion.',
      });
    },

    onError: () => {
      toast.error('Failed to post reply. Please try again.');
    },
  });
}

// Like a reply 
export function useLikeReply(communityId: string, postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (replyId: string) =>
      communityService.likeReply(communityId, replyId),

    onMutate: async (replyId) => {
      const key = ['community', communityId, 'posts', postId, 'replies'];
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData(key);

      queryClient.setQueryData<any[]>(key, (old = []) =>
        old.map(reply =>
          reply.comment_id === replyId
            ? { ...reply, likes_count: reply.likes_count + 1 }
            : reply
        )
      );

      return { previous };
    },

    onError: (_err, _replyId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ['community', communityId, 'posts', postId, 'replies'],
          context.previous
        );
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId, 'replies'],
      });
    },
  });
}

// Report content
export function useReportContent(communityId: string) {
  return useMutation({
    mutationFn: (payload: ReportPayload) =>
      communityService.reportContent(communityId, payload),

    onSuccess: () => {
      toast.success('Report Submitted', {
        description: 'Thank you for helping keep our community safe.',
      });
    },

    onError: () => {
      toast.error('Could not submit report. Please try again.');
    },
  });
}