
import { PageHeader } from '../components/ui/PageHeader';
import { Bot } from 'lucide-react';

export default function Assistant() {
  
  return (

  <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
    <PageHeader
    title="VOCE AI Assistant"
    description="Your intelligent companion for navigating health research and clinical trials."
    variant="green"
    action= {
    <div className="hidden md:block">
        <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
        <Bot size={32} className="text-white" />
        </div>
    </div>
    } />
  </div>
);
}