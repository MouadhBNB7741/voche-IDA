import type { ReactNode } from "react";
import { ShieldCheck, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

interface PageHeaderProps {
    title: string;
    description: string;
    badgeText?: string;
    action?: ReactNode;
    variant?: 'green' | 'orange';
    className?: string;
}

export function PageHeader({
    title,
    description,
    badgeText,
    action,
    variant = 'green',
    className
}: PageHeaderProps) {

    const isGreen = variant === 'green';

    return (
        <div className={cn(
            "relative overflow-hidden rounded-3xl text-white shadow-2xl mb-8 animate-in fade-in slide-in-from-top-4 duration-700",
            isGreen ? "bg-green-600" : "bg-orange-600",
            className
        )}>
            {/* Dynamic Background Gradients */}
            <div className={cn(
                "absolute inset-0 mix-blend-multiply opacity-50",
                isGreen
                    ? "bg-gradient-to-r from-secondary/50 via-primary to-primary"
                    : "bg-gradient-to-r from-orange-600/80 via-accent to-amber-400/50"
            )} />

            {/* Decorative Blur Orbs */}
            <div className={cn(
                "absolute -right-20 -top-20 w-96 h-96 rounded-full blur-3xl opacity-50",
                isGreen ? "bg-accent/20" : "bg-primary/20"
            )} />

            <div className="relative z-10 p-8 md:p-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                <div className="space-y-3 max-w-3xl">
                    {badgeText && (
                        <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider mb-2">
                            {isGreen ? <ShieldCheck size={14} /> : <Sparkles size={14} />}
                            {badgeText}
                        </div>
                    )}
                    <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white">{title}</h1>
                    <p className="text-white/90 text-lg leading-relaxed">
                        {description}
                    </p>
                </div>

                {action && (
                    <div className="flex-shrink-0">
                        {action}
                    </div>
                )}
            </div>
        </div>
    );
}