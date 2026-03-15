
import { PageHeader } from '../components/ui/PageHeader';

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  BookOpen,
  Video,
  FileText,
  Download,
  Star,
  Clock,
  Globe,
  Search,
  Filter,
  Play,
  Award,
  TrendingUp
} from 'lucide-react';
import { mockResources } from '../data/mockData';
import { Input } from '../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const resourceTypes = [
  { id: 'all', name: 'All Resources', icon: BookOpen, color: 'bg-primary' },
  { id: 'video', name: 'Videos', icon: Video, color: 'bg-red-500' },
  { id: 'document', name: 'Documents', icon: FileText, color: 'bg-blue-500' },
  { id: 'toolkit', name: 'Toolkits', icon: Download, color: 'bg-green-500' },
  { id: 'course', name: 'Courses', icon: Award, color: 'bg-purple-500' }
];

const categories = ['All', 'Education', 'Professional Development', 'Public Health', 'Advocacy'];

import { useData } from '../contexts/DataContext';

 
export default function ResourceLibrary() {

   const navigate = useNavigate();
  const { state } = useData();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortBy, setSortBy] = useState('popular');

  // Filter resources
  const filteredResources = state.resources.filter(resource => {
    const matchesSearch = resource.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      resource.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === 'all' || resource.type === selectedType;
    const matchesCategory = selectedCategory === 'All' || resource.category === selectedCategory;

    return matchesSearch && matchesType && matchesCategory;
  });

  const getTypeIcon = (type: string) => {
    const typeConfig = resourceTypes.find(t => t.id === type);
    return typeConfig ? typeConfig.icon : FileText;
  };

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        size={12}
        className={i < Math.floor(rating) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}
      />
    ));
  };
  
  return (

  <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
    <PageHeader
    title="Educational Hub & Resources"
    description="Access comprehensive educational materials, toolkits, and training resources."
    variant="green" 
    action={
          <div className="flex gap-4 text-sm font-medium bg-white/10 backdrop-blur-md p-4 rounded-xl shadow-inner text-white">
            <div className="flex flex-col items-center gap-1">
              <BookOpen size={20} />
              <span>500+ Items</span>
            </div>
            <div className="w-px bg-white/20 h-full"></div>
            <div className="flex flex-col items-center gap-1">
              <Globe size={20} />
              <span>25 Langs</span>
            </div>
            <div className="w-px bg-white/20 h-full"></div>
            <div className="flex flex-col items-center gap-1">
              <Award size={20} />
              <span>Certified</span>
            </div>
          </div>
        }
    
    
    />

      {/* Resource Types */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {resourceTypes.map((type) => {
          const Icon = type.icon;
          return (
            <Card
              key={type.id}
              className={`p-4 cursor-pointer transition-all duration-200 ${selectedType === type.id
                ? 'bg-accent text-accent-foreground border-accent shadow-md scale-105 ring-2 ring-accent ring-offset-2 ring-offset-background'
                : 'hover:shadow-md hover:bg-muted/50'
                }`}
              onClick={() => setSelectedType(type.id)}
            >
              <div className={`w-10 h-10 ${type.color} rounded-lg flex items-center justify-center mb-3 text-white shadow-sm`}>
                <Icon size={20} />
              </div>
              <h3 className="font-semibold text-sm">{type.name}</h3>
            </Card>
          );
        })}
      </div>

      {/* Search and Filters */}
      <Card className="p-6 border-border/60 shadow-sm">
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search resources by title, topic, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-11"
            />
          </div>

          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Category</label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(category => (
                    <SelectItem key={category} value={category}>
                      {category}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5 block">Sort By</label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="popular">Most Popular</SelectItem>
                  <SelectItem value="rating">Highest Rated</SelectItem>
                  <SelectItem value="recent">Most Recent</SelectItem>
                  <SelectItem value="downloads">Most Downloaded</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button variant="outline" className="gap-2 h-10 border-dashed">
                <Filter size={16} />
                Advanced Filters
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Featured Resources */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <div className="bg-accent/10 p-2 rounded-lg"><TrendingUp className="text-accent" size={20} /></div>
          <h2 className="text-xl font-bold">Featured & Trending</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {state.resources.slice(0, 3).map((resource) => {
            const TypeIcon = getTypeIcon(resource.type);
            return (
              <Card key={resource.id} className="p-6 bg-gradient-to-br from-card to-accent/5 border-accent/20 hover:shadow-lg transition-all hover:border-accent/40 group">
                <div className="flex items-start justify-between mb-4">
                  <div className="bg-white dark:bg-accent/20 text-accent p-2.5 rounded-xl shadow-sm">
                    <TypeIcon size={24} />
                  </div>
                  <Badge variant="secondary" className="bg-accent text-accent-foreground hover:bg-accent/90">
                    Featured
                  </Badge>
                </div>
                <h3 className="font-bold text-lg mb-2 group-hover:text-accent transition-colors line-clamp-2">{resource.title}</h3>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{resource.description}</p>

                <div className="flex items-center justify-between text-xs font-medium text-muted-foreground mb-5 bg-background/50 p-2 rounded-lg">
                  <span className="capitalize">{resource.type}</span>
                  <div className="flex items-center gap-1">
                    {renderStars(resource.rating)}
                    <span className="ml-1 text-foreground">({resource.rating})</span>
                  </div>
                </div>

                <Button size="sm" className="w-full bg-accent hover:bg-accent/90 text-white shadow-md group-hover:scale-[1.02] transition-transform" onClick={() => navigate(`/resources/${resource.id}`)}>
                  Access Resource
                </Button>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Resources Grid */}
      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-bold text-foreground">All Resources</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredResources.map((resource) => {
            const TypeIcon = getTypeIcon(resource.type);
            return (
              <Card
                key={resource.id}
                className="p-5 hover:shadow-xl transition-all duration-300 cursor-pointer border-transparent hover:border-border/80 group flex flex-col h-full bg-card"
                onClick={() => navigate(`/resources/${resource.id}`)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="bg-muted p-2.5 rounded-xl group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                    <TypeIcon size={20} className="text-muted-foreground group-hover:text-primary" />
                  </div>
                  <Badge variant="outline" className="text-xs bg-muted/30">
                    {resource.category}
                  </Badge>
                </div>

                <h3 className="font-bold mb-2 line-clamp-2 group-hover:text-primary transition-colors">{resource.title}</h3>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-3 flex-grow">
                  {resource.description}
                </p>

                <div className="space-y-3 mb-5 pt-3 border-t border-dashed">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <Globe size={12} />
                      {resource.language}
                    </span>
                    {resource.duration && (
                      <span className="flex items-center gap-1.5">
                        <Clock size={12} />
                        {resource.duration}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      {renderStars(resource.rating)}
                      <span className="text-xs text-muted-foreground ml-1">
                        ({resource.rating})
                      </span>
                    </div>
                    {resource.downloads && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground font-medium bg-muted px-2 py-0.5 rounded-full">
                        <Download size={10} />
                        {resource.downloads.toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-2.5 mt-auto">
                  {resource.type === 'video' ? (
                    <Button size="sm" className="flex-1 gap-2 shadow-sm" onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/resources/${resource.id}`);
                    }}>
                      <Play size={14} />
                      Watch
                    </Button>
                  ) : resource.type === 'course' ? (
                    <Button size="sm" className="flex-1 gap-2 shadow-sm" onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/resources/${resource.id}`);
                    }}>
                      <Award size={14} />
                      Start
                    </Button>
                  ) : (
                    <Button size="sm" className="flex-1 gap-2 shadow-sm" onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/resources/${resource.id}`);
                    }}>
                      <Download size={14} />
                      Get
                    </Button>
                  )}
                  <Button size="sm" variant="secondary" className="px-3" onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/resources/${resource.id}`);
                  }}>
                    Details
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {filteredResources.length === 0 && (
        <Card className="p-16 text-center">
          <BookOpen size={64} className="mx-auto mb-4 text-muted-foreground opacity-20" />
          <h3 className="text-lg font-bold mb-2">No resources found</h3>
          <p className="text-sm text-muted-foreground">
            Try adjusting your search criteria or filters.
          </p>
        </Card>
      )}

      {/* Learning Paths */}
      <Card className="p-8 bg-card border border-border/60 shadow-sm">
        <div className="flex items-center gap-4 mb-6">
          <div className="bg-secondary/10 text-secondary p-3 rounded-xl shadow-sm">
            <Award size={24} />
          </div>
          <div>
            <h3 className="font-bold text-lg text-foreground">Structured Learning Paths</h3>
            <p className="text-sm text-muted-foreground">
              Follow curated sequences of resources for comprehensive learning
            </p>
          </div>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { title: "Clinical Trial Participation", modules: 4, duration: "6 hours" },
            { title: "Healthcare Advocacy 101", modules: 6, duration: "8 hours" },
            { title: "Understanding Infectious Diseases", modules: 5, duration: "10 hours" }
          ].map((path, i) => (
            <Button key={i} variant="outline" className="h-auto p-5 text-left bg-background hover:bg-secondary/5 hover:border-secondary/50 group whitespace-normal transition-all">
              <div>
                <div className="font-bold mb-1 group-hover:text-secondary transition-colors text-foreground">{path.title}</div>
                <div className="text-xs text-muted-foreground font-medium flex items-center gap-2">
                  <span className="bg-secondary/10 text-secondary px-2 py-0.5 rounded text-[10px] uppercase tracking-wide">Path</span>
                  {path.modules} modules • {path.duration}
                </div>
              </div>
            </Button>
          ))}
        </div>
      </Card>

  </div>
);
}