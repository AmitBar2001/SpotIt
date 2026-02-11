import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

export function Navbar() {
  const navItems = [
    { name: "Browse", href: "/browse" },
    { name: "Play", href: "/" },
    { name: "Daily", href: "/daily" },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="flex h-16 w-full items-center justify-center px-4">
        <div className="flex w-full max-w-md items-center justify-around text-xl font-medium sm:max-w-none sm:justify-center sm:space-x-12 sm:text-lg">
          {navItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  "transition-colors hover:text-primary py-4 px-2 border-b-2 border-transparent",
                  isActive
                    ? "text-primary border-primary font-bold"
                    : "text-muted-foreground",
                )
              }
            >
              {item.name}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
