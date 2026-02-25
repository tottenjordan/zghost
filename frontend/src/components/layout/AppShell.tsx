import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { SessionBreadcrumb } from './SessionBreadcrumb';
import { Sidebar } from './Sidebar';

export function AppShell() {
  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-50">
      <Header />
      <SessionBreadcrumb />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-zinc-950 p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
