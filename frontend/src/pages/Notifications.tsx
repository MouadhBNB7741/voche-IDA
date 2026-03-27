import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
    Bell,
    Check,
    Trash2,
    MessageSquare,
    FlaskConical,
    Calendar,
    Info,
    Clock,
    XCircle
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { toast } from 'sonner';
import { useData } from '../contexts/DataContext';

export default function Notifications() {
    const navigate = useNavigate();
    const { state, actions } = useData();
    const [filter, setFilter] = useState<'all' | 'unread'>('all');

    const notifications = state.notifications;
    const unreadCount = notifications.filter(n => !n.read).length;

    const filteredNotifications = notifications.filter(n => {
        if (filter === 'unread') return !n.read;
        return true;
    });

    const handleMarkAllRead = () => {
        actions.markAllRead();
        toast.success("All notifications marked as read");
    };

    const handleMarkAsRead = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        actions.markRead(id);
    };

    const handleDelete = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        actions.deleteNotification(id);
        toast.success("Notification removed");
    };

    const handleClearAll = () => {
        actions.clearNotifications();
        toast.success("All notifications cleared");
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'trial': return FlaskConical;
            case 'community': return MessageSquare;
            case 'event': return Calendar;
            case 'system': return Info;
            default: return Bell;
        }
    };

    const getColor = (type: string) => {
        switch (type) {
            case 'trial': return 'bg-primary-color/10 text-primary-color';
            case 'community': return 'bg-secondary-color/10 text-secondary-color';
            case 'event': return 'bg-accent-color/10 text-accent-color';
            case 'system': return 'bg-muted-color text-muted-foreground';
            default: return 'bg-muted-color text-muted-foreground';
        }
    };

    return (
        <div className="container mx-auto p-4 md:p-8 max-w-4xl space-y-6 animate-in fade-in duration-500">
            <PageHeader
                title="Notifications"
                description="Stay updated with your latest alerts, messages, and reminders."
                badgeText={`${unreadCount} Unread`}
                variant="green"
                action={
                    <div className="hidden md:block">
                        <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
                            <Bell size={32} className="text-white" />
                        </div>
                    </div>
                }
            />

            <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-muted/30 p-4 rounded-xl border border-muted/50">
                <div className="flex gap-2">
                    <Button
                        variant={filter === 'all' ? 'default' : 'outline'}
                        onClick={() => setFilter('all')}
                        size="sm"
                        className="rounded-full shadow-sm"
                    >
                        All Notifications
                    </Button>
                    <Button
                        variant={filter === 'unread' ? 'default' : 'outline'}
                        onClick={() => setFilter('unread')}
                        size="sm"
                        className="rounded-full shadow-sm"
                    >
                        Unread
                        {unreadCount > 0 && (
                            <Badge className="ml-2 bg-white text-primary-color hover:bg-white">{unreadCount}</Badge>
                        )}
                    </Button>
                </div>

                <div className="flex gap-2">
                    {notifications.some(n => !n.read) && (
                        <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="text-primary-color hover:bg-primary-color/5 hover:text-primary-color">
                            <Check size={16} className="mr-2" /> Mark all read
                        </Button>
                    )}
                    {notifications.length > 0 && (
                        <Button variant="ghost" size="sm" onClick={handleClearAll} className="text-destructive-color hover:bg-destructive/5 hover:text-destructive-color">
                            <Trash2 size={16} className="mr-2" /> Clear all
                        </Button>
                    )}
                </div>
            </div>

            <div className="space-y-3">
                {filteredNotifications.length === 0 ? (
                    <Card className="p-16 text-center border-dashed bg-muted/20">
                        <Bell className="mx-auto mb-4 text-muted-foreground/30" size={48} />
                        <h3 className="text-lg font-bold mb-2">No notifications found</h3>
                        <p className="text-muted-foreground">
                            {filter === 'unread' ? "You're all caught up!" : "You have no notifications yet."}
                        </p>
                        {filter === 'unread' && notifications.length > 0 && (
                            <Button variant="link" onClick={() => setFilter('all')} className="mt-2">
                                View all history
                            </Button>
                        )}
                    </Card>
                ) : (
                    filteredNotifications.map((notification) => {
                        const Icon = getIcon(notification.type);
                        const colorClass = getColor(notification.type);

                        return (
                            <Card
                                key={notification.id}
                                className={`p-4 transition-all duration-200 cursor-pointer border hover:border-primary/40 hover:shadow-md group relative overflow-hidden ${!notification.read
                                    ? 'bg-primary-color/5 border-primary-color/20 dark:bg-primary-color/10'
                                    : 'bg-card border-border/60 hover:bg-muted/30'
                                    }`}
                                onClick={() => {
                                    if (!notification.read) actions.markRead(notification.id);
                                    if (notification.link) navigate(notification.link);
                                }}
                            >
                                {!notification.read && (
                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>
                                )}

                                <div className="flex gap-4 items-start">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${colorClass}`}>
                                        <Icon size={20} />
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-start gap-2 mb-1">
                                            <h4 className={`font-semibold text-sm ${!notification.read ? 'text-foreground' : 'text-muted-foreground'}`}>
                                                {notification.title}
                                            </h4>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Clock size={10} /> {notification.time}
                                                </span>
                                                {!notification.read && (
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        className="h-6 w-6 rounded-full text-muted-foreground hover:bg-primary-color/10 hover:text-primary-color"
                                                        title="Mark as read"
                                                        onClick={(e) => handleMarkAsRead(notification.id, e)}
                                                    >
                                                        <div className="w-2 h-2 bg-primary rounded-full"></div>
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                        <p className={`text-sm ${!notification.read ? 'text-foreground/90' : 'text-muted-foreground'} pr-8 line-clamp-2`}>
                                            {notification.message}
                                        </p>
                                    </div>

                                    <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity absolute right-4 top-1/2 -translate-y-1/2 bg-popover shadow-md border border-border rounded-lg p-1 z-10">
                                        <Button
                                            size="icon"
                                            variant="ghost"
                                            className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive rounded-md"
                                            onClick={(e) => handleDelete(notification.id, e)}
                                            title="Delete"
                                        >
                                            <Trash2 size={16} />
                                        </Button>
                                    </div>
                                </div>
                            </Card>
                        );
                    })
                )}
            </div>
        </div>
    );
}