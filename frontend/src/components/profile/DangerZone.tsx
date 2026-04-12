import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

export function DangerZone() {
    const handleDeactivate = () => {
        toast.error("Mock: Account deactivation initiated", {
            description: "You will be logged out. (Functionality is mocked)"
        });
    };

    const handleDelete = () => {
        toast.error("Mock: Account deletion initiated", {
            description: "Your data would be permanently removed. (Functionality is mocked)"
        });
    };

    return (
        <Card className="p-6 border-destructive/20 bg-destructive/5">
            <div className="flex items-center gap-2 mb-4 text-destructive">
                <AlertTriangle size={20} />
                <h3 className="text-lg font-semibold">Danger Zone</h3>
            </div>

            <div className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-background rounded-lg border border-destructive/10">
                    <div>
                        <div className="font-medium">Deactivate Account</div>
                        <div className="text-sm text-muted-foreground">
                            Temporarily disable your account. You can reactivate it anytime.
                        </div>
                    </div>
                    <Button variant="outline" className="border-destructive/30 hover:bg-destructive/90 text-destructive" onClick={handleDeactivate}>
                        Deactivate
                    </Button>
                </div>

                <div className="flex items-center justify-between p-4 bg-background rounded-lg border border-destructive/10">
                    <div>
                        <div className="font-medium text-destructive">Delete Account</div>
                        <div className="text-sm text-muted-foreground">
                            Permanently delete your account and all associated data. This cannot be undone.
                        </div>
                    </div>
                    <Button variant="destructive" onClick={handleDelete}>
                        Delete Account
                    </Button>
                </div>
            </div>
        </Card>
    );
<<<<<<< HEAD
}
=======
}
>>>>>>> origin/main
