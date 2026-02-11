/**
 * Driver projection data structure
 */
export interface Driver {
  id: string;
  name: string;
  salary: number;
  projectedPoints: number;
  position: number;
  value: number; // projectedPoints / salary
}

/**
 * Optimized lineup driver entry
 */
export interface LineupDriver {
  driverId: string;
  name: string;
  salary: number;
  projectedPoints: number;
  position: number;
}

/**
 * Complete optimized lineup
 */
export interface OptimizedLineup {
  drivers: LineupDriver[];
  totalSalary: number;
  totalProjectedPoints: number;
  averageValue: number;
}

/**
 * API request to optimize lineup
 */
export interface OptimizeRequest {
  drivers: {
    id: string;
    name: string;
    salary: number;
    projectedPoints: number;
    position: number;
  }[];
}

/**
 * API response from optimize endpoint
 */
export interface OptimizeResponse {
  lineup: OptimizedLineup;
  status: string;
  message?: string;
}
