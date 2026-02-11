import type { Driver } from '../types';

interface ProjectionTableProps {
  drivers: Driver[];
  onDriverSelect: (driverId: string) => void;
  selectedDriverIds: Set<string>;
}

export function ProjectionTable({
  drivers,
  onDriverSelect,
  selectedDriverIds,
}: ProjectionTableProps): JSX.Element {
  const calculateValue = (salary: number, projectedPoints: number): number => {
    return salary > 0 ? projectedPoints / salary : 0;
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <h2 className="text-xl font-semibold p-4 bg-gray-100 border-b">Driver Projections</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Select
              </th>
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
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Value (Pts/$)
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {drivers.map((driver) => (
              <tr
                key={driver.id}
                className={`hover:bg-gray-50 cursor-pointer ${
                  selectedDriverIds.has(driver.id) ? 'bg-blue-50' : ''
                }`}
                onClick={() => onDriverSelect(driver.id)}
              >
                <td className="px-4 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={selectedDriverIds.has(driver.id)}
                    onChange={() => onDriverSelect(driver.id)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </td>
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
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {calculateValue(driver.salary, driver.projectedPoints).toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
