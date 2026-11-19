import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import userService from '../services/userService';
import { compressImage } from '../utils/imageUtils';

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
const MAX_SIZE = 2 * 1024 * 1024;

/**
 * Upload and delete the logged-in user's profile photo.
 */
export function useAvatarUpload() {
  const queryClient = useQueryClient();
  const [isAvatarLoading, setIsAvatarLoading] = useState(false);

  const handleAvatarUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error('Invalid format', { description: 'Allowed formats: PNG, JPEG, JPG, WEBP.' });
      return;
    }
    if (file.size > MAX_SIZE) {
      toast.error('File too large', { description: 'File size must be less than 2MB.' });
      return;
    }

    try {
      setIsAvatarLoading(true);
      let finalFile = file;
      try {
        finalFile = await compressImage(file);
      } catch (err) {
        console.error('Silent compression failure:', err);
      }
      const response = await userService.uploadAvatar(finalFile);
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      toast.success('Profile Photo Updated', {
        description: response.message || 'Your new profile photo has been uploaded successfully.',
      });
    } catch (error: any) {
      toast.error('Upload Failed', {
        description: error?.message || 'Could not upload avatar. Please try again.',
      });
    } finally {
      setIsAvatarLoading(false);
    }
  };

  const handleAvatarDelete = async () => {
    try {
      const response = await userService.deleteAvatar();
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      toast.success('Profile Photo Deleted', {
        description: response.message || 'Your profile photo has been deleted.',
      });
    } catch (error: any) {
      toast.error('Delete Failed', {
        description: error?.message || 'Could not delete avatar. Please try again.',
      });
    }
  };

  return { isAvatarLoading, handleAvatarUpload, handleAvatarDelete };
}

export default useAvatarUpload;
