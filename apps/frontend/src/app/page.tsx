'use client';

import { useState, useEffect } from 'react';
import { ProjectionTable } from '../components/ProjectionTable';
import { OptimizerPanel } from '../components/OptimizerPanel';
import type { Driver, OptimizedLineup, OptimizeRequest, OptimizeResponse } from '../types';

export default function Home(): JSX.Element {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [selectedDriverIds, setSelectedDriverIds] = useState<Set<string>>(new Set());
  const [optimizedLineup, setOptimizedLineup] = useState<OptimizedLineup | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch mock driver projections
  useEffect(() => {
    const fetchDrivers = async (): Promise<void> => {
      try {
        const response = await fetch('/data/mockDrivers.json');
        const data = await response.json();
        
        // Calculate value for each driver
        const driversWithValue = data.map((driver: Driver) => ({
          ...driver,
          value: driver.salary > 0 ? driver.projectedPoints / driver.salary : 0,
        }));
        
        setDrivers(driversWithValue);
      } catch (err) {
        console.error('Failed to fetch drivers:', err);
        setError('Failed to load driver projections');
      }
    };

    fetchDrivers();
  }, []);

  const handleDriverSelect = (driverId: string): void => {
    setSelectedDriverIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(driverId)) {
        newSet.delete(driverId);
      } else {
        newSet.add(driverId);
      }
      return newSet;
    });
  };

  const handleOptimize = async (selectedDrivers: Driver[]): Promise<void> => {
    setIsLoading(true);
    setError(null);
    setOptimizedLineup(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const requestBody: OptimizeRequest = {
        drivers: selectedDrivers.map((driver) => ({
          id: driver.id,
          name: driver.name,
          salary: driver.salary,
          projectedPoints: driver.projectedPoints,
          position: driver.position,
        })),
      };

      const response = await fetch(`${apiUrl}/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: OptimizeResponse = await response.json();
      setOptimizedLineup(data.lineup);
    } catch (err) {
      console.error('Optimization failed:', err);
      setError(
        err instanceof Error
          ? `Optimization failed: ${err.message}`
          : 'Optimization failed'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const selectedDrivers = drivers.filter((driver) =>
    selectedDriverIds.has(driver.id)
  );

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          NASCAR DFS Lineup Optimizer
        </h2>
        <p className="text-gray-600">
          Select drivers from the projections table and optimize your lineup using the
          Axiomatic engine.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <ProjectionTable
            drivers={drivers}
            onDriverSelect={handleDriverSelect}
            selectedDriverIds={selectedDriverIds}
          />
        </div>

        <div className="lg:col-span-1">
          <OptimizerPanel
            selectedDrivers={selectedDrivers}
            onOptimize={handleOptimize}
            optimizedLineup={optimizedLineup}
            isLoading={isLoading}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}
