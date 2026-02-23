
import { PageHeader } from '../components/ui/PageHeader';
import { Bot } from 'lucide-react';

export default function Assistant() {
  
  return (

  <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
    <PageHeader
    title="VOCE AI Assistant"
    description="Your intelligent companion for navigating health research and clinical trials."
    variant="green" />
  </div>
);
}