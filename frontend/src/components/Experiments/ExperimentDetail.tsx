import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiService from '../../services/api';
import AccuracyCurve from '../Visualizations/AccuracyCurve';
import { format } from 'date-fns';

export default function ExperimentDetail() {
    const { id } = useParams<{ id: string }>();
    const experimentId = parseInt(id || '0');

    const { data: experiment } = useQuery({
        queryKey: ['experiment', experimentId],
        queryFn: () => apiService.getExperiment(experimentId),
        enabled: !!experimentId,
    });

    const { data: trialsData } = useQuery({
        queryKey: ['experiment-trials', experimentId],
        queryFn: () => apiService.getExperimentTrials(experimentId),
        enabled: !!experimentId,
    });

    const { data: accuracyData } = useQuery({
        queryKey: ['accuracy-curve', experimentId],
        queryFn: () => apiService.getAccuracyCurve(experimentId),
        enabled: !!experimentId,
    });

    const StatusBadge = ({ status }: { status: string }) => {
        const colors: Record<string, string> = {
            pending: 'bg-yellow-100 text-yellow-800',
            running: 'bg-blue-100 text-blue-800',
            finished: 'bg-green-100 text-green-800',
            failed: 'bg-red-100 text-red-800',
        };

        return (
            <span className={`px-2 py-1 text-xs rounded-full ${colors[status]}`}>
                {status}
            </span>
        );
    };

    if (!experiment || !trialsData) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Breadcrumb */}
            <nav className="mb-4">
                <ol className="flex items-center space-x-2">
                    <li>
                        <Link to="/experiments" className="text-primary-600 hover:text-primary-800">
                            Experiments
                        </Link>
                    </li>
                    <li className="text-gray-400">/</li>
                    <li className="text-gray-700 font-medium">{experiment.name}</li>
                </ol>
            </nav>

            {/* Header */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{experiment.name}</h1>
                        <p className="text-gray-600 mt-1">Project: {experiment.project_id}</p>
                        <p className="text-sm text-gray-500 mt-2">
                            Created: {format(new Date(experiment.created_at), 'PPP')}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-3xl font-bold text-primary-600">
                            ${experiment.total_cost?.toFixed(2) || '0.00'}
                        </p>
                        <p className="text-sm text-gray-500">Total Cost</p>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t">
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.total_trials || 0}
                        </p>
                        <p className="text-sm text-gray-500">Total Trials</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.total_runs || 0}
                        </p>
                        <p className="text-sm text-gray-500">Total Runs</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.avg_accuracy
                                ? `${(experiment.avg_accuracy * 100).toFixed(1)}%`
                                : '-'}
                        </p>
                        <p className="text-sm text-gray-500">Avg Accuracy</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {trialsData.trials.filter(t => t.status === 'finished').length}
                        </p>
                        <p className="text-sm text-gray-500">Completed Trials</p>
                    </div>
                </div>
            </div>

            {/* Accuracy Curve */}
            {accuracyData && accuracyData.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Accuracy Curve</h2>
                    <AccuracyCurve data={accuracyData} />
                </div>
            )}

            {/* Trials Table */}
            <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">Trials</h2>
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Trial ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Accuracy
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Duration
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Runs
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Cost
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Created
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {trialsData.trials.map((trial) => (
                            <tr key={trial.id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                    #{trial.id}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <StatusBadge status={trial.status} />
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    {trial.accuracy ? `${(trial.accuracy * 100).toFixed(1)}%` : '-'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    {trial.duration_seconds ? `${trial.duration_seconds}s` : '-'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    {trial.total_runs || 0}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    ${trial.total_cost?.toFixed(2) || '0.00'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {format(new Date(trial.created_at), 'MMM d, HH:mm')}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}