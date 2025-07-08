"use client"

interface HeaderProps {
  title: string
  subtitle?: string
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="flex h-16 sm:h-20 items-center border-b bg-card px-4 sm:px-6">
      <div className="flex flex-col gap-1 ml-14 lg:ml-0">
        <h1 className="text-lg sm:text-xl font-semibold line-clamp-1">{title}</h1>
        {subtitle && (
          <p className="text-xs sm:text-sm text-muted-foreground line-clamp-1">{subtitle}</p>
        )}
      </div>
    </header>
  )
} 