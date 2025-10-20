import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import Dashboard from '../components/Dashboard/Dashboard';
import Experiments from '../components/Experiments/Experiments';
import ExperimentDetail from '../components/Experiments/ExperimentDetail';
import TrialDetail from '../components/Trials/TrialDetail';


function App() {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const navigation = [
        { name: 'Dashboard', href: '/', icon: ' ' },
        { name: 'Experiments', href: '/experiments', icon: ' ' },
    ];

    return (
        <div className="flex h-screen">
            {/* Sidebar */}
            <div className={`${sidebarOpen ? 'w-64' : 'w-16'} transition-all duration-300 bg-white shadow-lg`}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center justify-between h-16 px-4 border-b">
                        {sidebarOpen && (
                            <h1 className="text-lg font-bold text-gray-800">LLM Observatory</h1>
                        )}
                        <button
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            className="p-2 rounded hover:bg-gray-100"
                        >
                            {sidebarOpen ? '◀' : '▶'}
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href;
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={`flex items-center gap-3 px-3 py-2 mb-2 rounded-lg transition-colors ${isActive
                                        ? 'bg-primary-50 text-primary-700'
                                        : 'hover:bg-gray-100 text-gray-700'
                                        }`}
                                >
                                    <span className="text-xl">{item.icon}</span>
                                    {sidebarOpen && <span className="font-medium">{item.name}</span>}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Footer */}
                    <div className="p-4 border-t">
                        {sidebarOpen && (
                            <div className="text-sm text-gray-500">
                                <p>Version 0.1.0</p>
                                <p className="mt-1">© 2025 LLM Observatory</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/experiments" element={<Experiments />} />
                    <Route path="/experiments/:id" element={<ExperimentDetail />} />
                    <Route path="/trials/:id" element={<TrialDetail />} />
                </Routes>
            </div>
        </div>
    );
}

export default App;