
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../contexts/DataContext';

import { PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

import { mockTrials } from '../data/mockData';

import { toast } from 'sonner';

import {
  Search,
  Filter,
  MapPin,
  Calendar,
  Building,
  FileText,
  ChevronRight,
  Heart,
  Clock,
  FlaskConical
} from 'lucide-react';

export default function Trials() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDisease, setSelectedDisease] = useState('all');
  const [selectedPhase, setSelectedPhase] = useState('all');
  const { state, actions } = useData();
  const savedTrials = state.savedTrials;

  const diseases = ['all', ...Array.from(new Set(mockTrials.map(t => t.disease)))];
  const phases = ['all', ...Array.from(new Set(mockTrials.map(t => t.phase)))];

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const filteredTrials = mockTrials.filter(trial => {
    const matchesSearch =
      trial.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.location.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDisease =
      selectedDisease === 'all' || trial.disease === selectedDisease;

    const matchesPhase =
      selectedPhase === 'all' || trial.phase === selectedPhase;

    return matchesSearch && matchesDisease && matchesPhase;
  });

  const totalPages = Math.ceil(filteredTrials.length / itemsPerPage);
  const paginatedTrials = filteredTrials.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handlePageChange = (newPage: number) => {
    if (newPage > 0 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const toggleSavedTrial = (trialId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const isSaved = savedTrials.includes(trialId);

    if (isSaved) {
      actions.unsaveTrial(trialId);
      toast("Trial Removed", {
        description: "Removed from your saved trials list.",
      });
    } else {
      actions.saveTrial(trialId);
      toast("Trial Saved", {
        description: "Added to your saved trials list.",
      });
    }
  };

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title="Clinical Trial Navigator"
        description="Discover clinical trials that match your profile and interests."
        badgeText={`${filteredTrials.length} Active Trials`}
        variant="green"
        action={
          <div className="hidden md:block">
            <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
              <FlaskConical size={32} className="text-white" />
            </div>
          </div>
        }
      />

        {/* Search and Filters */}
      <Card className="p-6 shadow-sm border-border/60">
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search trials by disease, location, or keywords..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              className="pl-10 h-11"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Disease Area</label>
              <Select value={selectedDisease} onValueChange={(v) => { setSelectedDisease(v); setCurrentPage(1); }}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="All Diseases" />
                </SelectTrigger>
                <SelectContent>
                  {diseases.map(disease => (
                    <SelectItem key={disease} value={disease}>
                      {disease === 'all' ? 'All Diseases' : disease}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Trial Phase</label>
              <Select value={selectedPhase} onValueChange={(v) => { setSelectedPhase(v); setCurrentPage(1); }}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="All Phases" />
                </SelectTrigger>
                <SelectContent>
                  {phases.map(phase => (
                    <SelectItem key={phase} value={phase}>
                      {phase === 'all' ? 'All Phases' : phase}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button variant="outline" className="gap-2 h-10 border-dashed">
                <Filter size={16} />
                More Filters
              </Button>
            </div>
          </div>
        </div>
      </Card>

       <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Trials', value: mockTrials.length, color: 'text-primary' },
          { label: 'Disease Areas', value: diseases.length - 1, color: 'text-secondary' },
          { label: 'Countries', value: '12', color: 'text-accent' },
          { label: 'Saved Trials', value: savedTrials.length, color: 'text-info' }
        ].map((stat, i) => (
          <Card key={i} className="p-4 text-center hover:shadow-md transition-all">
            <div className={`text-3xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{stat.label}</div>
          </Card>
        ))}
      </div>

      {/* Results */}
      <div className="space-y-4">
        {paginatedTrials.map((trial) => (
          <Card
            key={trial.id}
            className="group p-6 hover:shadow-xl transition-all duration-300 cursor-pointer border-transparent hover:border-primary/20"
            onClick={() => navigate(`/trials/${trial.id}`)}
          >
            <div className="flex flex-col lg:flex-row lg:items-start gap-6">
              <div className="flex-1 space-y-4">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="default" className="bg-primary/90 hover:bg-primary">{trial.disease}</Badge>
                    <Badge variant="outline" className="border-primary/20 text-primary">{trial.phase}</Badge>
                    <Badge variant="secondary" className="bg-secondary/10 text-secondary hover:bg-secondary/20">
                      Enrolling: {trial.enrollment}/{trial.maxEnrollment}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => toggleSavedTrial(trial.id, e)}
                    className="rounded-full hover:bg-muted"
                  >
                    <Heart
                      size={20}
                      className={`transition-colors duration-300 ${savedTrials.includes(trial.id)
                        ? 'fill-red-500 text-red-500' // Red when saved
                        : 'text-muted-foreground group-hover:text-red-500' // Gray/Contrast when not, hover red
                        }`}
                    />
                  </Button>
                </div>

                <div>
                  <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">{trial.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {trial.description}
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4 pt-2">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Building size={16} className="text-primary" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Sponsor</span>
                        <span className="font-medium">{trial.sponsor}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <MapPin size={16} className="text-primary" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Location</span>
                        <span className="font-medium">{trial.location}</span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Calendar size={16} className="text-primary" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Started</span>
                        <span className="font-medium">{new Date(trial.startDate).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Clock size={16} className="text-primary" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Est. Completion</span>
                        <span className="font-medium">{new Date(trial.estimatedCompletion).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-muted/10 rounded-xl p-4 border border-dashed border-border">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    <FileText size={14} /> Key Eligibility
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {trial.eligibility.slice(0, 3).map((criteria, index) => (
                      <Badge key={index} variant="outline" className="text-xs bg-background">
                        {criteria}
                      </Badge>
                    ))}
                    {trial.eligibility.length > 3 && (
                      <Badge variant="outline" className="text-xs text-muted-foreground">
                        +{trial.eligibility.length - 3} more
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:w-56 space-y-3 lg:border-l lg:pl-6 lg:border-border/50">
                <Button className="w-full gap-2 shadow-md group-hover:bg-primary group-hover:text-primary-foreground transition-all" onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/trials/${trial.id}`);
                }}>
                  View Details
                  <ChevronRight size={16} />
                </Button>
                <Button variant="outline" className="w-full gap-2 border-primary/20 text-primary hover:bg-primary/60" onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/trials/${trial.id}`);
                }}>
                  <FileText size={16} />
                  Eligibility Quiz
                </Button>
                <div className="text-center pt-2">
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">Primary Contact</div>
                  <div className="text-xs font-medium text-primary mt-1 break-words">{trial.contact.split(' - ')[0]}</div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filteredTrials.length > itemsPerPage && (
        <div className="flex justify-center items-center gap-4 py-8">
          <Button
            variant="outline"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <span className="text-sm font-medium">Page {currentPage} of {totalPages}</span>
          <Button
            variant="outline"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}

      {filteredTrials.length === 0 && (
        <Card className="p-16 text-center border-dashed">
          <div className="text-muted-foreground">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText size={32} className="opacity-50" />
            </div>
            <h3 className="text-xl font-bold mb-2 text-foreground">No trials found</h3>
            <p className="text-sm max-w-sm mx-auto">Try adjusting your search criteria or filters to find more opportunities.</p>
            <Button variant="outline" className="mt-6" onClick={() => {
              setSearchQuery('');
              setSelectedDisease('all');
              setSelectedPhase('all');
            }}>Clear Filters</Button>
          </div>
        </Card>
      )}

     
    </div>

    
  );
}