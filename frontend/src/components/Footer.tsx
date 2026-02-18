
export default function Footer() {
  return (
    <footer className="border-t border-border bg-background py-8">
      <div className="container px-4 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md gradient-primary flex items-center justify-center">
            </div>
            <span className="font-semibold text-sm text-foreground">VOCE Platform</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} Platform. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}