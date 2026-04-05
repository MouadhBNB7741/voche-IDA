import { cva } from "class-variance-authority"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary-color text-primary-foreground hover:bg-primary-color/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-secondary hover:text-primary-color",
        secondary:
          "bg-secondary-color text-secondary-foreground hover:bg-secondary-color/80",
        ghost:
          "hover:bg-secondary-color hover:text-primary-color",
        link:
          "text-primary-color underline-offset-4 hover:underline",
        // Use on coloured hero banners — white background with primary-coloured text.
        hero:
          /*"bg-white text-primary hover:bg-white/90 shadow-lg*/
          "bg-white-600 text-green hover:bg-white/700 shadow-lg",
        // Solid green background with white text — for primary CTAs outside hero banners.
        green:
          "bg-green-600 text-white hover:bg-green-700 shadow-sm",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)