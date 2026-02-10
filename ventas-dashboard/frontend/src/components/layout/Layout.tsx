import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, MobileMenuButton } from './Sidebar';
import { Header } from './Header';
import { TooltipProvider } from '../ui/tooltip';

export function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <TooltipProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar
          mobileOpen={mobileMenuOpen}
          onMobileClose={() => setMobileMenuOpen(false)}
        />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header>
            <MobileMenuButton onClick={() => setMobileMenuOpen(true)} />
          </Header>
          <main className="flex-1 overflow-auto p-3 md:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
