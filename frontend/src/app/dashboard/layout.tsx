import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <Topbar />
      <main className="dashboard-content">
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
