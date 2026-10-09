import { FileText, LayoutDashboard, MessageSquare, Settings } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { Separator } from '@/components/ui/separator'
import { cn } from 'cn'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/documents', label: 'Documents', icon: FileText, end: false },
  { to: '/chat', label: 'Chat', icon: MessageSquare, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
]

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1 px-3">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
            )
          }
        >
          <item.icon className="size-4" aria-hidden="true" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2 px-6 py-5">
      <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-semibold">
        CR
      </span>
      <div className="flex flex-col">
        <span className="text-sm font-semibold tracking-tight">College RAG</span>
        <span className="text-xs text-muted-foreground">Study workspace</span>
      </div>
    </div>
  )
}

export function AppShell() {
  return (
    <div className="flex h-screen bg-background">
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-card md:flex">
        <Brand />
        <Separator />
        <div className="flex-1 py-4">
          <NavLinks />
        </div>
        <div className="px-6 py-4 text-xs text-muted-foreground">
          Answers from your documents only.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-4 py-3 md:hidden">
          <span className="text-sm font-semibold">College RAG</span>
        </header>
        <div className="flex gap-1 overflow-x-auto border-b px-3 py-2 md:hidden">
          <NavLinks />
        </div>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
