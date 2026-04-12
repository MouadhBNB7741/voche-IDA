import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useData } from "../../contexts/DataContext";

import { PageHeader } from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";

<<<<<<< HEAD
import { mockTrials } from "../../data/mockData";

=======
>>>>>>> origin/main
import { toast } from "sonner";

import {
  Search,
  Filter,
  MapPin,
  Calendar,
  Building,
  FileText,
  ChevronRight,
  Heart,
  FlaskConical,
  Clock
} from "lucide-react";

export default function Trials() {
  const navigate = useNavigate();
  const { state, actions } = useData();

<<<<<<< HEAD
  const savedTrials = state.savedTrials;
=======
  const trials = state.trials || [];
  const savedTrials = state.savedTrials || [];
>>>>>>> origin/main

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDisease, setSelectedDisease] = useState("all");
  const [selectedPhase, setSelectedPhase] = useState("all");

<<<<<<< HEAD
  const diseases = ["all", ...Array.from(new Set(mockTrials.map((t) => t.disease)))];
  const phases = ["all", ...Array.from(new Set(mockTrials.map((t) => t.phase)))];
=======
  const diseases = ["all", ...Array.from(new Set(trials.map((t) => t.disease_area).filter(Boolean)))];
  const phases = ["all", ...Array.from(new Set(trials.map((t) => t.phase).filter(Boolean)))];
>>>>>>> origin/main

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

<<<<<<< HEAD
  const filteredTrials = mockTrials.filter((trial) => {
    const matchesSearch =
      trial.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.location.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDisease =
      selectedDisease === "all" || trial.disease === selectedDisease;
=======
  const filteredTrials = trials.filter((trial) => {
    const matchesSearch =
      trial.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (trial.summary?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (trial.sponsor.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesDisease =
      selectedDisease === "all" || trial.disease_area === selectedDisease;
>>>>>>> origin/main

    const matchesPhase =
      selectedPhase === "all" || trial.phase === selectedPhase;

    return matchesSearch && matchesDisease && matchesPhase;
  });

  const totalPages = Math.ceil(filteredTrials.length / itemsPerPage);

  const paginatedTrials = filteredTrials.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const toggleSavedTrial = (trialId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    const isSaved = savedTrials.includes(trialId);

    if (isSaved) {
      actions.unsaveTrial(trialId);
<<<<<<< HEAD
      toast("Trial Removed", {
=======
      toast.success("Trial Removed", {
>>>>>>> origin/main
        description: "Removed from your saved trials list.",
      });
    } else {
      actions.saveTrial(trialId);
<<<<<<< HEAD
      toast("Trial Saved", {
=======
      toast.success("Trial Saved", {
>>>>>>> origin/main
        description: "Added to your saved trials list.",
      });
    }
  };

  const handlePageChange = (page: number) => {
    if (page > 0 && page <= totalPages) {
      setCurrentPage(page);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-8 animate-in fade-in slide-in-from-bottom-3 duration-500">

      <PageHeader
        title="Clinical Trial Navigator"
        description="Discover clinical trials that match your profile."
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

      {/* Search + Filters */}

      <Card className="p-6 border-0 shadow-sm bg-background/60 backdrop-blur-sm">
        <div className="space-y-5">

          <div className="relative">
            <Search className="absolute left-4 top-3.5 h-4 w-4 text-muted-foreground" />
            <Input
<<<<<<< HEAD
              placeholder="Search trials by disease, title, or location..."
=======
              placeholder="Search trials by disease, title, or sponsor..."
>>>>>>> origin/main
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-10 h-12 bg-muted border-0"
            />
          </div>

          <div className="grid md:grid-cols-3 gap-4">

            <Select
              value={selectedDisease}
              onValueChange={(v) => {
                setSelectedDisease(v);
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="h-11 bg-muted border-0">
                <SelectValue placeholder="Disease Area" />
              </SelectTrigger>
              <SelectContent>
                {diseases.map((disease) => (
<<<<<<< HEAD
                  <SelectItem key={disease} value={disease}>
                    {disease === "all" ? "All Diseases" : disease}
=======
                  <SelectItem key={`disease-${disease}`} value={disease as string}>
                    {disease === "all" ? "All Diseases" : (disease as string)}
>>>>>>> origin/main
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={selectedPhase}
              onValueChange={(v) => {
                setSelectedPhase(v);
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="h-11 bg-muted border-0">
                <SelectValue placeholder="Trial Phase" />
              </SelectTrigger>
              <SelectContent>
                {phases.map((phase) => (
<<<<<<< HEAD
                  <SelectItem key={phase} value={phase}>
                    {phase === "all" ? "All Phases" : phase}
=======
                  <SelectItem key={`phase-${phase}`} value={phase as string}>
                    {phase === "all" ? "All Phases" : (phase as string)}
>>>>>>> origin/main
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant="outline" className="h-11 flex gap-2 border-0">
              <Filter size={16} />
              More Filters
            </Button>

          </div>
        </div>
      </Card>

      {/* Stats */}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        {[
<<<<<<< HEAD
          { label: "Total Trials",  value: mockTrials.length,    color: 'text-[hsl(var(--primary))]' },
          { label: "Disease Areas", value: diseases.length - 1,  color: 'text-[hsl(var(--teal))]'    },
          { label: "Countries",     value: 12,                   color: 'text-[hsl(var(--lime))]'    },
=======
          { label: "Total Trials",  value: trials.length,    color: 'text-[hsl(var(--primary))]' },
          { label: "Disease Areas", value: Math.max(0, diseases.length - 1),  color: 'text-[hsl(var(--teal))]'    },
          { label: "Countries",     value: 0,                   color: 'text-[hsl(var(--lime))]'    },
>>>>>>> origin/main
          { label: "Saved Trials",  value: savedTrials.length,   color: 'text-[hsl(var(--blue))]'    },
        ].map((stat, i) => (
          <Card key={i} className="p-5 text-center rounded-xl border-0">
            <div className={`text-3xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
            <div className="text-xs uppercase text-muted-foreground tracking-wide mt-1">
              {stat.label}
            </div>
          </Card>
        ))}

      </div>

<<<<<<< HEAD
      {/* Trials */}
      <div className="space-y-4">
        {paginatedTrials.map((trial) => (
          <Card
            key={trial.id}
            className="group p-6 hover:shadow-xl transition-all duration-300 cursor-pointer border-transparent hover:border-primary/20"
            onClick={() => navigate(`/trials/${trial.id}`)}
=======
      <div className="space-y-4">
        {paginatedTrials.map((trial, index) => (
          <Card
            key={`trial-nav-item-${trial.trial_id || index}`}
            className="group p-6 hover:shadow-xl transition-all duration-300 cursor-pointer border-transparent hover:border-primary/20"
            onClick={() => navigate(`/trials/${trial.trial_id}`)}
>>>>>>> origin/main
          >
            <div className="flex flex-col lg:flex-row lg:items-start gap-6">
              <div className="flex-1 space-y-4">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
<<<<<<< HEAD
                    <Badge variant="default" className="bg-primary/90 hover:bg-primary">{trial.disease}</Badge>
                    <Badge variant="outline" className="border-primary/20 text-primary">{trial.phase}</Badge>
                    <Badge variant="secondary" className="bg-secondary/10 text-secondary hover:bg-secondary/20">
                      Enrolling: {trial.enrollment}/{trial.maxEnrollment}
=======
                    <Badge variant="default" className="bg-primary/90 hover:bg-primary">{trial.disease_area}</Badge>
                    <Badge variant="outline" className="border-primary/20 text-primary">{trial.phase}</Badge>
                    <Badge variant="secondary" className="bg-secondary/10 text-secondary hover:bg-secondary/20">
                      Enrolled: {trial.enrollment}/{trial.max_enrollment || 'N/A'}
>>>>>>> origin/main
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
<<<<<<< HEAD
                    onClick={(e) => toggleSavedTrial(trial.id, e)}
=======
                    onClick={(e) => toggleSavedTrial(trial.trial_id, e)}
>>>>>>> origin/main
                    className="rounded-full hover:bg-muted"
                  >
                    <Heart
                      size={20}
<<<<<<< HEAD
                      className={`transition-colors duration-300 ${savedTrials.includes(trial.id)
=======
                      className={`transition-colors duration-300 ${savedTrials.includes(trial.trial_id)
>>>>>>> origin/main
                        ? 'fill-red-500 text-red-500' // Red when saved
                        : 'text-muted-foreground group-hover:text-red-500' // Gray/Contrast when not, hover red
                        }`}
                    />
                  </Button>
                </div>

                <div>
                  <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">{trial.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">
<<<<<<< HEAD
                    {trial.description}
=======
                    {trial.summary}
>>>>>>> origin/main
                  </p>
                </div>

                <div className="grid md:grid-cols-2 gap-4 pt-2">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Building size={16} className="text-primary-color" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Sponsor</span>
                        <span className="font-medium">{trial.sponsor}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <MapPin size={16} className="text-primary-color" />
                      <div>
<<<<<<< HEAD
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Location</span>
                        <span className="font-medium">{trial.location}</span>
=======
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Primary Site</span>
                        <span className="font-medium">{trial.countries?.[0] || 'International'}</span>
>>>>>>> origin/main
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Calendar size={16} className="text-primary-color" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Started</span>
<<<<<<< HEAD
                        <span className="font-medium">{new Date(trial.startDate).toLocaleDateString()}</span>
=======
                        <span className="font-medium">{trial.start_date ? new Date(trial.start_date).toLocaleDateString() : 'N/A'}</span>
>>>>>>> origin/main
                      </div>
                    </div>
                    <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                      <Clock size={16} className="text-primary-color" />
                      <div>
                        <span className="text-xs font-semibold text-muted-foreground uppercase block">Est. Completion</span>
<<<<<<< HEAD
                        <span className="font-medium">{new Date(trial.estimatedCompletion).toLocaleDateString()}</span>
=======
                        <span className="font-medium">{trial.estimated_completion ? new Date(trial.estimated_completion).toLocaleDateString() : 'N/A'}</span>
>>>>>>> origin/main
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-muted/10 rounded-xl p-4 border border-dashed border-border">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                    <FileText size={14} /> Key Eligibility
                  </h4>
<<<<<<< HEAD
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
=======
                  <div className="text-xs text-muted-foreground">
                    {trial.eligibility_criteria ? (
                       <p className="line-clamp-2">{trial.eligibility_criteria}</p>
                    ) : (
                      "Please contact site for full eligibility details."
>>>>>>> origin/main
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:w-56 space-y-3 lg:border-l lg:pl-6 lg:border-border/50">
                <Button className="w-full gap-2 shadow-md group-hover:bg-primary group-hover:text-primary-foreground transition-all" 
                  style={{ backgroundColor: 'hsl(var(--primary))', color: 'white' }}
                  onClick={(e) => {
                  e.stopPropagation();
<<<<<<< HEAD
                  navigate(`/trials/${trial.id}`);
=======
                  navigate(`/trials/${trial.trial_id}`);
>>>>>>> origin/main
                }}>
                  View Details
                  <ChevronRight size={16} />
                </Button>
                <Button variant="outline" className="w-full gap-2 border-primary/20 text-primary hover:bg-primary/60" onClick={(e) => {
                  e.stopPropagation();
<<<<<<< HEAD
                  navigate(`/trials/${trial.id}`);
=======
                  navigate(`/trials/${trial.trial_id}`);
>>>>>>> origin/main
                }}>
                  <FileText size={16} />
                  Eligibility Quiz
                </Button>
                <div className="text-center pt-2">
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">Primary Contact</div>
<<<<<<< HEAD
                  <div className="text-xs font-medium text-primary mt-1 break-words">{trial.contact.split(' - ')[0]}</div>
=======
                  <div className="text-xs font-medium text-primary mt-1 break-words">{trial.contact || 'contact@voche.com'}</div>
>>>>>>> origin/main
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Pagination */}

      {filteredTrials.length > itemsPerPage && (
        <div className="flex justify-center items-center gap-4 py-8">

          <Button
            variant="outline"
            className="border-0"
            disabled={currentPage === 1}
            onClick={() => handlePageChange(currentPage - 1)}
          >
            Previous
          </Button>

          <span className="text-sm font-medium">
            Page {currentPage} of {totalPages}
          </span>

          <Button
            variant="outline"
            className="border-0"
            disabled={currentPage === totalPages}
            onClick={() => handlePageChange(currentPage + 1)}
          >
            Next
          </Button>

        </div>
      )}

      {/* Empty State */}

      {filteredTrials.length === 0 && (
        <Card className="p-16 text-center border-0">

          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText size={30} className="opacity-50" />
          </div>

          <h3 className="text-xl font-semibold mb-2">
            No trials found
          </h3>

          <p className="text-muted-foreground text-sm">
            Try adjusting your search or filters.
          </p>

          <Button
            variant="outline"
            className="mt-6 border-0"
            onClick={() => {
              setSearchQuery("");
              setSelectedDisease("all");
              setSelectedPhase("all");
            }}
          >
            Clear Filters
          </Button>

        </Card>
      )}

    </div>
  );
<<<<<<< HEAD
}
=======
}
>>>>>>> origin/main
