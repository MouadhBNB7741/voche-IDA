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

import { useTrials } from "../../hooks/useTrials";
import { useSaveTrial } from "../../hooks/useSaveTrial";

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
  Clock,
} from "lucide-react";

const DISEASE_OPTIONS = [
  "all", "HIV", "Cancer", "Diabetes",
  "Cardiovascular", "Alzheimer's", "Lung Cancer", "Breast Cancer",
];

const PHASE_OPTIONS = [
  "all", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Post-Market",
];

export default function Trials() {
  const navigate = useNavigate();
  const { state } = useData();
  const { toggleSave, isSaved } = useSaveTrial();
  const savedTrials = state.savedTrials;

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDisease, setSelectedDisease] = useState("all");
  const [selectedPhase, setSelectedPhase] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const {
    data: trials = [],
    isLoading,
    error,
  } = useTrials({
    search: searchQuery,
    disease: selectedDisease,
    phase: selectedPhase,
  });

  const totalPages = Math.ceil(trials.length / itemsPerPage);
  const paginatedTrials = trials.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );

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
        badgeText={`${trials.length} Active Trials`}
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
              placeholder="Search trials by disease, title, or location..."
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
                {DISEASE_OPTIONS.map((disease) => (
                  <SelectItem key={disease} value={disease}>
                    {disease === "all" ? "All Diseases" : disease}
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
                {PHASE_OPTIONS.map((phase) => (
                  <SelectItem key={phase} value={phase}>
                    {phase === "all" ? "All Phases" : phase}
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
          { label: "Total Trials", value: trials.length, color: "text-[hsl(var(--primary))]" },
          { label: "Disease Areas", value: DISEASE_OPTIONS.length - 1, color: "text-[hsl(var(--teal))]" },
          { label: "Countries", value: 12, color: "text-[hsl(var(--lime))]" },
          { label: "Saved Trials", value: savedTrials.length, color: "text-[hsl(var(--blue))]" },
        ].map((stat, i) => (
          <Card key={i} className="p-5 text-center rounded-xl border-0">
            <div className={`text-3xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
            <div className="text-xs uppercase text-muted-foreground tracking-wide mt-1">{stat.label}</div>
          </Card>
        ))}
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-6 border-0">
              <div className="animate-pulse space-y-4">
                <div className="flex gap-2">
                  <div className="h-5 w-20 bg-muted rounded-full" />
                  <div className="h-5 w-16 bg-muted rounded-full" />
                  <div className="h-5 w-24 bg-muted rounded-full" />
                </div>
                <div className="h-6 w-3/4 bg-muted rounded" />
                <div className="h-4 w-full bg-muted rounded" />
                <div className="h-4 w-2/3 bg-muted rounded" />
                <div className="grid md:grid-cols-2 gap-4 pt-2">
                  <div className="space-y-3">
                    <div className="h-10 bg-muted rounded-lg" />
                    <div className="h-10 bg-muted rounded-lg" />
                  </div>
                  <div className="space-y-3">
                    <div className="h-10 bg-muted rounded-lg" />
                    <div className="h-10 bg-muted rounded-lg" />
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-16 text-center border-0">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText size={30} className="text-red-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Failed to load trials</h3>
          <p className="text-muted-foreground text-sm">Something went wrong. Please try again.</p>
          <Button variant="outline" className="mt-6 border-0" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {paginatedTrials.map((trial) => (
            <Card
              key={trial.trial_id} 
              className="group p-6 hover:shadow-xl transition-all duration-300 cursor-pointer border-transparent hover:border-primary/20"
              onClick={() => navigate(`/trials/${trial.trial_id}`)} 
            >
              <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                <div className="flex-1 space-y-4">
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="default" className="bg-primary/90 hover:bg-primary">
                        {trial.disease_area} 
                      </Badge>
                      <Badge variant="outline" className="border-primary/20 text-primary">
                        {trial.phase}
                      </Badge>
                      <Badge variant="secondary" className="bg-secondary/10 text-secondary hover:bg-secondary/20">
                        {trial.status} {/* ← was Enrolling: enrollment/maxEnrollment */}
                      </Badge>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => { e.stopPropagation(); toggleSave(trial.trial_id); }} 
                      className="rounded-full hover:bg-muted"
                    >
                      <Heart
                        size={20}
                        className={`transition-colors duration-300 ${
                          isSaved(trial.trial_id) 
                            ? "fill-red-500 text-red-500"
                            : "text-muted-foreground group-hover:text-red-500"
                        }`}
                      />
                    </Button>
                  </div>

                  <div>
                    <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">
                      {trial.title}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed">
                      {trial.summary || "No description available."} 
                    </p>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 pt-2">
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                        <Building size={16} className="text-primary-color" />
                        <div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase block">Sponsor</span>
                          <span className="font-medium">{trial.sponsor || "N/A"}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                        <MapPin size={16} className="text-primary-color" />
                        <div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase block">Location</span>
                          <span className="font-medium">
                            {trial.countries?.[0] || "Not specified"} 
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                        <Calendar size={16} className="text-primary-color" />
                        <div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase block">Started</span>
                          <span className="font-medium">
                            {trial.start_date 
                              ? new Date(trial.start_date).toLocaleDateString()
                              : "TBD"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-sm p-2 rounded-lg bg-muted/30">
                        <Clock size={16} className="text-primary-color" />
                        <div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase block">Est. Completion</span>
                          <span className="font-medium">
                            {trial.estimated_completion 
                              ? new Date(trial.estimated_completion).toLocaleDateString()
                              : "TBD"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Eligibility criteria */}
                  {trial.eligibility_criteria && ( 
                    <div className="bg-muted/10 rounded-xl p-4 border border-dashed border-border">
                      <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                        <FileText size={14} /> Key Eligibility
                      </h4>
                      <p className="text-sm text-muted-foreground line-clamp-3">
                        {trial.eligibility_criteria}
                      </p>
                    </div>
                  )}
                </div>

                <div className="lg:w-56 space-y-3 lg:border-l lg:pl-6 lg:border-border/50">
                  <Button
                    className="w-full gap-2 shadow-md"
                    style={{ backgroundColor: "hsl(var(--primary))", color: "white" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/trials/${trial.trial_id}`);
                    }}
                  >
                    View Details
                    <ChevronRight size={16} />
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full gap-2 border-primary/20 text-primary hover:bg-primary/60"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/trials/${trial.trial_id}`);
                    }}
                  >
                    <FileText size={16} />
                    Eligibility Quiz
                  </Button>
                  <div className="text-center pt-2">
                    <div className="text-[10px] uppercase font-bold text-muted-foreground">
                      Enrollment
                    </div>
                    <div className="text-xs font-medium text-primary mt-1">
                      {trial.enrollment} enrolled 
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !error && trials.length > itemsPerPage && (
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

      {/* Empty state */}
      {!isLoading && !error && trials.length === 0 && (
        <Card className="p-16 text-center border-0">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText size={30} className="opacity-50" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No trials found</h3>
          <p className="text-muted-foreground text-sm">Try adjusting your search or filters.</p>
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
}