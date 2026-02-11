import type { Driver, OptimizedLineup } from '../types';

interface OptimizerPanelProps {
  selectedDrivers: Driver[];
  onOptimize: (drivers: Driver[]) => void;
  optimizedLineup: OptimizedLineup | null;
  isLoading: boolean;
  error: string | null;
}

export function OptimizerPanel({
  selectedDrivers,
  onOptimize,
  optimizedLineup,
  isLoading,
  error,
}: OptimizerPanelProps): JSX.Element {
  const handleOptimize = (): void => {
    if (selectedDrivers.length > 0) {
      onOptimize(selectedDrivers);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Lineup Optimizer</h2>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">
          Selected Drivers: {selectedDrivers.length}
        </p>
        <p className="text-sm text-gray-600 mb-4">
          Total Salary: ${selectedDrivers.reduce((sum, d) => sum + d.salary, 0).toLocaleString()}
        </p>
        <button
          onClick={handleOptimize}
          disabled={selectedDrivers.length === 0 || isLoading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Optimizing...' : 'Optimize Lineup'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {optimizedLineup && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Optimized Lineup</h3>
          <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Total Salary:</span>{' '}
                ${optimizedLineup.totalSalary.toLocaleString()}
              </div>
              <div>
                <span className="font-medium">Total Projected Points:</span>{' '}
                {optimizedLineup.totalProjectedPoints.toFixed(1)}
              </div>
              <div>
                <span className="font-medium">Average Value:</span>{' '}
                {optimizedLineup.averageValue.toFixed(4)}
              </div>
              <div>
                <span className="font-medium">Drivers:</span> {optimizedLineup.drivers.length}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Position
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Driver
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Salary
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Projected Pts
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {optimizedLineup.drivers.map((driver) => (
                  <tr key={driver.driverId}>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                      {driver.position}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {driver.name}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      ${driver.salary.toLocaleString()}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {driver.projectedPoints.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
