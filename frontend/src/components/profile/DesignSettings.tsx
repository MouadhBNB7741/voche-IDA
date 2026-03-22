
import { useTheme } from '../../contexts/ThemeContext';
import { Card } from '../ui/card';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Palette, Type, Check, RefreshCw } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { hexToHSL, HSLToHex } from '../../utils/themeUtils';
import { toast } from 'sonner';

const PRESETS = [
    {
        name: "Forest Green",
        colors: { primary: '142 70% 35%', secondary: '170 50% 30%', accent: '80 60% 45%' }
    },
    {
        name: "Classic Blue",
        colors: { primary: '215 100% 35%', secondary: '175 80% 30%', accent: '25 100% 55%' }
    },
    {
        name: "Sunset Orange",
        colors: { primary: '25 90% 50%', secondary: '260 50% 40%', accent: '45 100% 50%' }
    },
    {
        name: "Royal Purple",
        colors: { primary: '265 80% 40%', secondary: '280 50% 30%', accent: '35 100% 50%' }
    },
];

const FONTS = ['Poppins', 'Inter', 'Roboto', 'Lato', 'Montserrat'];

export function DesignSettings() {
    const { colors, font, updateColor, updateFont, resetTheme } = useTheme();

    const handleColorChange = (key: 'primary' | 'secondary' | 'accent', hex: string) => {
        updateColor(key, hexToHSL(hex));
    };

    const applyPreset = (presetColors: typeof PRESETS[0]['colors']) => {
        Object.entries(presetColors).forEach(([key, value]) => {
            updateColor(key as any, value);
        });
        toast.success('Theme Preset Applied');
    };

    const handleReset = () => {
        resetTheme();
        toast.info('Theme Reset to Default');
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-center bg-card p-4 rounded-xl border shadow-sm">
                <div>
                    <h2 className="text-lg font-bold flex items-center gap-2">
                        <Palette className="text-primary" size={20} />
                        Design & Appearance
                    </h2>
                    <p className="text-sm text-muted-foreground">Customize the look and feel of the platform.</p>
                </div>
                <Button variant="outline" size="sm" onClick={handleReset} className="gap-2">
                    <RefreshCw size={16} />
                    Reset Defaults
                </Button>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
                {/* Color Settings */}
                <Card className="p-6 border-border/60 shadow-sm space-y-6">
                    <div>
                        <h3 className="text-lg font-semibold mb-2">Color Palette</h3>
                        <p className="text-sm text-muted-foreground mb-4">Choose a preset or customize individual colors.</p>

                        {/* Presets */}
                        <div className="grid grid-cols-2 gap-3 mb-6">
                            {PRESETS.map((preset) => (
                                <button
                                    key={preset.name}
                                    onClick={() => applyPreset(preset.colors)}
                                    className="flex items-center gap-3 p-3 rounded-lg border hover:border-primary/50 transition-all bg-muted/20 hover:bg-muted/40 text-left group"
                                >
                                    <div className="flex -space-x-2">
                                        <div className="w-6 h-6 rounded-full border border-white shadow-sm" style={{ backgroundColor: `hsl(${preset.colors.primary})` }} />
                                        <div className="w-6 h-6 rounded-full border border-white shadow-sm" style={{ backgroundColor: `hsl(${preset.colors.secondary})` }} />
                                        <div className="w-6 h-6 rounded-full border border-white shadow-sm" style={{ backgroundColor: `hsl(${preset.colors.accent})` }} />
                                    </div>
                                    <span className="text-sm font-medium">{preset.name}</span>
                                </button>
                            ))}
                        </div>

                        {/* Custom Colors */}
                        <div className="space-y-4 pt-4 border-t">
                            <div className="grid grid-cols-[1fr,auto] gap-4 items-center">
                                <div>
                                    <Label>Primary Color</Label>
                                    <p className="text-xs text-muted-foreground">Main brand color, buttons, links.</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono uppercase text-muted-foreground">{HSLToHex(colors.primary)}</span>
                                    <div className="relative w-10 h-10 rounded-full overflow-hidden border shadow-sm cursor-pointer hover:scale-105 transition-transform">
                                        <input
                                            type="color"
                                            value={HSLToHex(colors.primary)}
                                            onChange={(e) => handleColorChange('primary', e.target.value)}
                                            className="absolute inset-0 w-[150%] h-[150%] -top-[25%] -left-[25%] p-0 border-0 cursor-pointer"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-[1fr,auto] gap-4 items-center">
                                <div>
                                    <Label>Secondary Color</Label>
                                    <p className="text-xs text-muted-foreground">Accents, gradients, decorative elements.</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono uppercase text-muted-foreground">{HSLToHex(colors.secondary)}</span>
                                    <div className="relative w-10 h-10 rounded-full overflow-hidden border shadow-sm cursor-pointer hover:scale-105 transition-transform">
                                        <input
                                            type="color"
                                            value={HSLToHex(colors.secondary)}
                                            onChange={(e) => handleColorChange('secondary', e.target.value)}
                                            className="absolute inset-0 w-[150%] h-[150%] -top-[25%] -left-[25%] p-0 border-0 cursor-pointer"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-[1fr,auto] gap-4 items-center">
                                <div>
                                    <Label>Accent Color</Label>
                                    <p className="text-xs text-muted-foreground">Highlights, calls to action.</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono uppercase text-muted-foreground">{HSLToHex(colors.accent)}</span>
                                    <div className="relative w-10 h-10 rounded-full overflow-hidden border shadow-sm cursor-pointer hover:scale-105 transition-transform">
                                        <input
                                            type="color"
                                            value={HSLToHex(colors.accent)}
                                            onChange={(e) => handleColorChange('accent', e.target.value)}
                                            className="absolute inset-0 w-[150%] h-[150%] -top-[25%] -left-[25%] p-0 border-0 cursor-pointer"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Typography Settings */}
                <Card className="p-6 border-border/60 shadow-sm h-fit">
                    <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                        <Type size={18} className="text-primary" />
                        Typography
                    </h3>
                    <p className="text-sm text-muted-foreground mb-6">Select the font family for the interface.</p>

                    <div className="space-y-4">
                        <Label>Font Family</Label>
                        <Select value={font} onValueChange={updateFont}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select Font" />
                            </SelectTrigger>
                            <SelectContent>
                                {FONTS.map(f => (
                                    <SelectItem key={f} value={f} style={{ fontFamily: f }}>
                                        {f}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>

                        <div className="mt-8 p-4 bg-muted/30 rounded-lg border border-border/50">
                            <p className="text-xs text-muted-foreground mb-2 text-center uppercase tracking-wider">Preview</p>
                            <div className="space-y-2 text-center">
                                <h4 className="text-2xl font-bold text-primary">Heading Text</h4>
                                <p className="text-base">The quick brown fox jumps over the lazy dog.</p>
                                <p className="text-sm text-muted-foreground">1234567890 !@#$%^&*()</p>
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}