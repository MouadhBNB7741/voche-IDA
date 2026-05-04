import { apiClient } from '../lib/apiClient';
import { COMMUNITY } from '../lib/api';
import type { Community, ForumPost, Comment } from '../types/db';


export interface CreatePostPayload {
  title: string;
  content: string;
  post_type: string;
  tags: string[];
}

export interface CreateReplyPayload {
  content: string;
  parent_comment_id?: string;
}

export interface ReportPayload {
  target_type: 'post' | 'comment' | 'user';
  target_id: string;
  reason: string;
  description?: string;
}


export const communityService = {
  // Communities
  async getCommunities(): Promise<Community[]> {
    const response = await apiClient.get(COMMUNITY.LIST);
    return response.data?.data ?? response.data;
  },

  async getCommunityById(id: string): Promise<Community> {
    const response = await apiClient.get(COMMUNITY.GET(id));
    return response.data?.data ?? response.data;
  },

  // Posts
  async getFeed(): Promise<ForumPost[]> {
    const response = await apiClient.get(COMMUNITY.FEED);
    return response.data?.data ?? response.data;
  },

  async getPosts(communityId: string): Promise<ForumPost[]> {
    const response = await apiClient.get(COMMUNITY.POSTS(communityId));
    return response.data?.data ?? response.data;
  },

  async getPostById(communityId: string, postId: string): Promise<ForumPost> {
    const response = await apiClient.get(
      COMMUNITY.POST_DETAILS(communityId, postId),
    );
    return response.data?.data ?? response.data;
  },

  async createPost(
    communityId: string,
    payload: CreatePostPayload,
  ): Promise<ForumPost> {
    const response = await apiClient.post(
      COMMUNITY.POSTS(communityId),
      payload,
    );
    return response.data;
  },

  async likePost(communityId: string, postId: string): Promise<void> {
    await apiClient.post(COMMUNITY.LIKE_POST(communityId, postId));
  },

  // Replies
  async getReplies(communityId: string, postId: string): Promise<Comment[]> {
    const response = await apiClient.get(
      COMMUNITY.REPLIES(communityId, postId),
    );
    return response.data;
  },

  async createReply(
    communityId: string,
    postId: string,
    payload: CreateReplyPayload,
  ): Promise<Comment> {
    const response = await apiClient.post(
      COMMUNITY.REPLIES(communityId, postId),
      payload,
    );
    return response.data;
  },

  async likeReply(communityId: string, replyId: string): Promise<void> {
    await apiClient.post(COMMUNITY.LIKE_REPLY(communityId, replyId));
  },

  // Reports
  async reportContent(
    communityId: string,
    payload: ReportPayload,
  ): Promise<void> {
    await apiClient.post(COMMUNITY.REPORT(communityId), payload);
  },
};