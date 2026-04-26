import { useState } from 'react';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { AlertTriangle, Loader2, Calendar } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../contexts/AuthContext';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '../ui/dialog';
import { useQueryClient } from '@tanstack/react-query';
import userService from '../../services/userService';

export function DangerZone() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [isDeleting, setIsDeleting] = useState(false);
    const [confirmText, setConfirmText] = useState('');
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    const handleDelete = async () => {
        if (confirmText !== 'DELETE') {
            toast.error("Validation failed", {
                description: "Please type DELETE exactly to confirm."
            });
            return;
        }

        try {
            setIsDeleting(true);
            const response = await userService.deleteAccount();
            toast.success("Account deletion scheduled", {
                description: response.message || "Your account has been scheduled for deletion in 7 days."
            });
            await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
            setIsDialogOpen(false);
            setConfirmText('');
        } catch (error: any) {
            toast.error("Failed to schedule account deletion", {
                description: error.response?.data?.detail || "Please try again later."
            });
        } finally {
            setIsDeleting(false);
        }
    };

    const isScheduled = !!user?.deletion_scheduled_at;

    return (
        <Card className="p-6 border-red-600/30 shadow-lg relative overflow-hidden mb-8">
            <div className="absolute top-0 right-0 left-0 h-1 bg-red-600/50"></div>
            <div className="flex items-center gap-2 mb-4 text-red-600">
                <AlertTriangle size={20} className="animate-pulse" />
                <h3 className="text-lg font-bold tracking-tight">System Danger Zone</h3>
            </div>

            <div className="space-y-6">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between p-5 bg-background rounded-xl border-2 border-red-600/20 shadow-inner gap-4">
                    <div>
                        <div className="font-bold text-red-600 text-base">Delete My Account</div>
                        <div className="text-sm text-muted-foreground mt-1 max-w-xl">
                            {isScheduled ? (
                                <span className="flex items-center gap-1.5 text-orange-500 font-semibold animate-pulse">
                                    <Calendar size={16} />
                                    Account deletion has been scheduled. Re-logging cancels it.
                                </span>
                            ) : (
                                "Your account will be scheduled for permanent deletion in 1 week. You can log back in at any time to annul this schedule safely."
                            )}
                        </div>
                    </div>
                    
                    {isScheduled ? (
                        <Button 
                            variant="outline" 
                            className="font-semibold border-amber-600/50 text-amber-600 bg-amber-600/10 hover:bg-amber-600/20"
                            disabled
                        >
                            Deletion Scheduled
                        </Button>
                    ) : (
                        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                            <DialogTrigger asChild>
                                <Button 
                                    variant="destructive" 
                                    className="font-semibold bg-red-600 hover:bg-red-700 text-white shadow-md shadow-red-600/20 cursor-pointer"
                                >
                                    Delete My Account
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[425px] border-red-600/30 bg-background/95 backdrop-blur-md">
                                <DialogHeader>
                                    <DialogTitle className="flex items-center gap-2 text-red-600 font-bold">
                                        <AlertTriangle size={18} />
                                        Confirm Account Deletion
                                    </DialogTitle>
                                    <DialogDescription className="text-muted-foreground mt-2">
                                        This action will queue your account for deletion. All profile data will be permanently cleared after 7 days.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="py-4 space-y-3">
                                    <Label htmlFor="confirmDelete" className="text-sm font-semibold">
                                        To confirm, type <span className="font-black text-red-600 select-all">DELETE</span> below:
                                    </Label>
                                    <Input
                                        id="confirmDelete"
                                        placeholder="DELETE"
                                        value={confirmText}
                                        onChange={(e) => setConfirmText(e.target.value)}
                                        className="bg-muted/30 border-red-600/20 focus-visible:ring-red-600 mt-2"
                                        autoComplete="off"
                                    />
                                </div>
                                <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2">
                                    <Button
                                        className='cursor-pointer w-full sm:w-auto'
                                        variant="outline"
                                        onClick={() => {
                                            setIsDialogOpen(false);
                                            setConfirmText('');
                                        }}
                                        disabled={isDeleting}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="destructive"
                                        onClick={handleDelete}
                                        disabled={confirmText !== 'DELETE' || isDeleting}
                                        className="bg-red-600 hover:bg-red-700 font-bold cursor-pointer w-full sm:w-auto"
                                    >
                                        {isDeleting ? (
                                            <>
                                                <Loader2 size={16} className="animate-spin mr-2" />
                                                Scheduling...
                                            </>
                                        ) : (
                                            'Confirm Deletion'
                                        )}
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    )}
                </div>
            </div>
        </Card>
    );
}
