
import { PageHeader } from '../components/ui/PageHeader';

export default function Home() {
  
  return (

  <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
    <PageHeader
    title="Welcome to VOCE"
    description="Advancing health equity through accessible clinical research for everyone."
    variant="green" />
  </div>
);
}