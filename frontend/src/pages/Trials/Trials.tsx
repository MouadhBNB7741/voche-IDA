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

import { mockTrials } from "../../data/mockData";

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
} from "lucide-react";

export default function Trials() {
  const navigate = useNavigate();
  const { state, actions } = useData();

  const savedTrials = state.savedTrials;

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDisease, setSelectedDisease] = useState("all");
  const [selectedPhase, setSelectedPhase] = useState("all");

  const diseases = ["all", ...Array.from(new Set(mockTrials.map((t) => t.disease)))];
  const phases = ["all", ...Array.from(new Set(mockTrials.map((t) => t.phase)))];

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const filteredTrials = mockTrials.filter((trial) => {
    const matchesSearch =
      trial.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.location.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDisease =
      selectedDisease === "all" || trial.disease === selectedDisease;

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
                {diseases.map((disease) => (
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
                {phases.map((phase) => (
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
          { label: "Total Trials", value: mockTrials.length },
          { label: "Disease Areas", value: diseases.length - 1 },
          { label: "Countries", value: 12 },
          { label: "Saved Trials", value: savedTrials.length },
        ].map((stat, i) => (
          <Card key={i} className="p-5 text-center rounded-xl border-0">
            <div className="text-3xl font-bold text-primary">{stat.value}</div>
            <div className="text-xs uppercase text-muted-foreground tracking-wide mt-1">
              {stat.label}
            </div>
          </Card>
        ))}

      </div>

      {/* Trials */}

      <div className="space-y-4">

        {paginatedTrials.map((trial) => (
          <Card
            key={trial.id}
            onClick={() => navigate(`/trials/${trial.id}`)}
            className="group p-6 rounded-2xl border-0 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 cursor-pointer bg-background/70 backdrop-blur-sm"
          >
            <div className="flex flex-col lg:flex-row gap-6">

              <div className="flex-1 space-y-4">

                <div className="flex justify-between">

                  <div className="flex flex-wrap gap-2">

                    <Badge className="bg-emerald-100 text-emerald-700">
                      {trial.disease}
                    </Badge>

                    <Badge variant="outline">
                      {trial.phase}
                    </Badge>

                    <Badge className="bg-blue-100 text-blue-700">
                      {trial.enrollment}/{trial.maxEnrollment} enrolled
                    </Badge>

                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => toggleSavedTrial(trial.id, e)}
                  >
                    <Heart
                      size={20}
                      className={
                        savedTrials.includes(trial.id)
                          ? "fill-red-500 text-red-500"
                          : "text-muted-foreground"
                      }
                    />
                  </Button>

                </div>

                <div>
                  <h3 className="text-xl font-semibold group-hover:text-primary transition-colors">
                    {trial.title}
                  </h3>

                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {trial.description}
                  </p>
                </div>

                <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">

                  <div className="flex items-center gap-2">
                    <Building size={16} />
                    {trial.sponsor}
                  </div>

                  <div className="flex items-center gap-2">
                    <MapPin size={16} />
                    {trial.location}
                  </div>

                  <div className="flex items-center gap-2">
                    <Calendar size={16} />
                    {new Date(trial.startDate).toLocaleDateString()}
                  </div>

                </div>

                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">
                    Enrollment Progress
                  </div>

                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full"
                      style={{
                        width: `${(trial.enrollment / trial.maxEnrollment) * 100}%`,
                      }}
                    />
                  </div>
                </div>

              </div>

              <div className="lg:w-52 flex flex-col gap-3">

                <Button
                  className="w-full"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/trials/${trial.id}`);
                  }}
                >
                  View Details
                  <ChevronRight size={16} />
                </Button>

                <Button
                  variant="outline"
                  className="w-full border-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/trials/${trial.id}`);
                  }}
                >
                  <FileText size={16} />
                  Eligibility Quiz
                </Button>

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
}