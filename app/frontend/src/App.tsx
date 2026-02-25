import { CyberConsoleDashboard } from './components/CyberConsoleDashboard';
import { Toaster } from 'sonner';

const App = () => {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <CyberConsoleDashboard />
      <Toaster richColors position="bottom-right" />
    </div>
  );
};

export default App;
