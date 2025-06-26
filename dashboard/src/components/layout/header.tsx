"use client"

interface HeaderProps {
  title: string
  subtitle?: string
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="flex h-20 items-center border-b bg-card px-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
    </header>
  )
} 