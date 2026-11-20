import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { communityService } from '../services/communityService';
import type { CreatePostPayload, CreateReplyPayload, ReportPayload } from '../services/communityService';
import { useErrorHandler } from './useErrorHandler';



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
export function useCommunityFeed(params?: {
  page?: number;
  limit?: number;
  category?: string;
  sort?: string;
}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['community', 'feed', params],
    queryFn: () => communityService.getFeed(params),
    retry: false,
    enabled: options?.enabled,
  });
}

// Fetch posts for a specific community
export function useCommunityPosts(communityId: string | undefined, params?: { page?: number; limit?: number; sort?: string }) {
  return useQuery({
    queryKey: ['community', communityId, 'posts', params],
    queryFn: () => communityService.getPosts(communityId!, params),
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
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (payload: CreatePostPayload) =>
      communityService.createPost(communityId, payload),

    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['community'] });
      // The API wraps the post as { success, data }
      const post = (result as any)?.data ?? result;
      if (post?.moderation_status === 'pending') {
        toast.info('Your post is waiting for review', {
          description: 'A moderator will check it before other members can see it. You can still see it in the feed.',
          duration: 8000,
        });
        return;
      }
      toast.success('Discussion Created', {
        description: 'Your post has been published to the community.',
      });
    },

    onError: (err) => {
      handleError(err, 'Failed to create post. Please try again.');
    },
  });
}

// Like a post 
export function useLikePost(communityId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (postId: string) =>
      communityService.likePost(communityId, postId),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['community'] });
    },

    onError: (err) => {
      handleError(err, 'Could not like post. Please try again.');
    },
  });
}

// Unlike a post
export function useUnlikePost(communityId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (postId: string) =>
      communityService.unlikePost(communityId, postId),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['community'] });
    },

    onError: (err) => {
      handleError(err, 'Could not unlike post. Please try again.');
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
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (payload: CreateReplyPayload) =>
      communityService.createReply(communityId, postId, payload),

    onSuccess: (reply) => {
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId, 'replies'],
      });

      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId],
      });
      if (reply?.moderation_status === 'pending') {
        toast.info('Your reply is waiting for review', {
          description: 'A moderator will check it before other members can see it.',
          duration: 8000,
        });
        return;
      }
      toast.success('Reply Posted', {
        description: 'Your contribution has been added to the discussion.',
      });
    },

    onError: (err) => {
      handleError(err, 'Failed to post reply. Please try again.');
    },
  });
}

// Like a reply 
export function useLikeReply(communityId: string, postId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

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

    onError: (err, _replyId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ['community', communityId, 'posts', postId, 'replies'],
          context.previous
        );
      }
      handleError(err, 'Could not like reply. Please try again.');
    },

    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId, 'replies'],
      });
    },
  });
}

// Unlike a reply
export function useUnlikeReply(communityId: string, postId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (replyId: string) =>
      communityService.unlikeReply(communityId, replyId),

    onMutate: async (replyId) => {
      const key = ['community', communityId, 'posts', postId, 'replies'];
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData(key);

      queryClient.setQueryData<any[]>(key, (old = []) =>
        old.map(reply =>
          reply.comment_id === replyId
            ? { ...reply, likes_count: Math.max(0, reply.likes_count - 1) }
            : reply
        )
      );

      return { previous };
    },

    onError: (err, _replyId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          ['community', communityId, 'posts', postId, 'replies'],
          context.previous
        );
      }
      handleError(err, 'Could not unlike reply. Please try again.');
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
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (payload: ReportPayload) =>
      communityService.reportContent(communityId, payload),

    onSuccess: () => {
      toast.success('Report sent', {
        description: 'Thank you. A moderator will review it.',
      });
    },

    onError: (err) => {
      handleError(err, 'Could not submit report. Please try again.');
    },
  });
}

// Delete a post
export function useDeletePost(communityId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (postId: string) =>
      communityService.deletePost(communityId, postId),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['community'] });
      toast.success('Post Deleted', {
        description: 'Your post has been successfully deleted.',
      });
    },

    onError: (err) => {
      handleError(err, 'Failed to delete post. Please try again.');
    },
  });
}

// Delete a reply
export function useDeleteReply(communityId: string, postId: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (replyId: string) =>
      communityService.deleteReply(communityId, replyId),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId, 'replies'],
      });
      queryClient.invalidateQueries({
        queryKey: ['community', communityId, 'posts', postId],
      });
      toast.success('Reply Deleted', {
        description: 'Your reply has been successfully deleted.',
      });
    },

    onError: (err) => {
      handleError(err, 'Failed to delete reply. Please try again.');
    },
  });
}