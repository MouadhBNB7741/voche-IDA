import { useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { X, Plus } from 'lucide-react';

interface InterestSelectorProps {
    selectedInterests: string[];
    onChange: (interests: string[]) => void;
    isEditing: boolean;
}

const predefinedInterests = [
    'HIV/AIDS',
    'Tuberculosis',
    'Malaria',
    'Vaccines',
    'Antimicrobial Resistance',
    'Cancer',
    'Diabetes',
    'Cardiovascular',
    'Mental Health',
    'Nutrition',
    'Neurology',
    'Dermatology',
    'Pediatrics',
    'Infectious Diseases',
    'Rare Diseases',
    'Geriatrics',
    'Autoimmune Diseases',
    'Gastroenterology',
    'Respiratory Health',
    'Ophthalmology',
    'Genomics'
];

export function InterestSelector({ selectedInterests, onChange, isEditing }: InterestSelectorProps) {
    const [customInterest, setCustomInterest] = useState('');

    const toggleInterest = (interest: string) => {
        if (!isEditing) return;

        if (selectedInterests.includes(interest)) {
            onChange(selectedInterests.filter(i => i !== interest));
        } else {
            onChange([...selectedInterests, interest]);
        }
    };

    const addCustomInterest = () => {
        if (customInterest.trim() && !selectedInterests.includes(customInterest.trim())) {
            onChange([...selectedInterests, customInterest.trim()]);
            setCustomInterest('');
        }
    };

    return (
        <div className="space-y-4">
            <Label className="text-base font-semibold">Disease Interests</Label>
            <p className="text-sm text-muted-foreground">Select areas of health you are interested in following.</p>

            <div className="flex flex-wrap gap-2 mb-4">
                {selectedInterests.map((interest) => (
                    <Badge
                        key={interest}
                        variant="default"
                        className={`pl-3 pr-2 py-1 text-sm ${isEditing ? 'cursor-pointer hover:bg-destructive hover:text-destructive-foreground' : ''}`}
                        onClick={() => isEditing && toggleInterest(interest)}
                    >
                        {interest}
                        {isEditing && <X size={14} className="ml-1" />}
                    </Badge>
                ))}
            </div>

            {isEditing && (
                <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                    <div className="space-y-2">
                        <Label>Add from list</Label>
                        <div className="flex flex-wrap gap-2">
                            {predefinedInterests.filter(i => !selectedInterests.includes(i)).map((interest) => (
                                <Badge
                                    key={interest}
                                    variant="outline"
                                    className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                                    onClick={() => toggleInterest(interest)}
                                >
                                    <Plus size={12} className="mr-1" />
                                    {interest}
                                </Badge>
                            ))}
                        </div>
                    </div>

                    <div className="flex items-end gap-2">
                        <div className="flex-1 space-y-2">
                            <Label htmlFor="custom-interest">Add custom interest</Label>
                            <Input
                                id="custom-interest"
                                placeholder="e.g. Rare Diseases"
                                value={customInterest}
                                onChange={(e) => setCustomInterest(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomInterest())}
                            />
                        </div>
                        <Button type="button" size="icon" onClick={addCustomInterest} disabled={!customInterest.trim()}>
                            <Plus size={18} />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
