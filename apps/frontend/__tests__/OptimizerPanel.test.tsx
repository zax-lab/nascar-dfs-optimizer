import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { OptimizerPanel } from '../src/components/OptimizerPanel';

describe('OptimizerPanel', () => {
  const mockDrivers = [
    {
      id: '1',
      name: 'Kyle Larson',
      salary: 10500,
      projectedPoints: 55.5,
      position: 1,
      value: 0.0052857,
    },
    {
      id: '2',
      name: 'Chase Elliott',
      salary: 9800,
      projectedPoints: 48.2,
      position: 2,
      value: 0.0049184,
    },
  ];

  const mockOnOptimize = jest.fn();

  const mockOptimizedLineup = {
    drivers: [
      {
        driverId: '1',
        name: 'Kyle Larson',
        salary: 10500,
        projectedPoints: 55.5,
        position: 1,
      },
      {
        driverId: '2',
        name: 'Chase Elliott',
        salary: 9800,
        projectedPoints: 48.2,
        position: 2,
      },
    ],
    totalSalary: 20300,
    totalProjectedPoints: 103.7,
    averageValue: 0.005107,
  };

  it('renders optimizer panel with correct title', () => {
    render(
      <OptimizerPanel
        selectedDrivers={[]}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByText('Lineup Optimizer')).toBeInTheDocument();
  });

  it('displays selected drivers count and total salary', () => {
    render(
      <OptimizerPanel
        selectedDrivers={mockDrivers}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByText('Selected Drivers: 2')).toBeInTheDocument();
    expect(screen.getByText('Total Salary: $20,300')).toBeInTheDocument();
  });

  it('disables optimize button when no drivers selected', () => {
    render(
      <OptimizerPanel
        selectedDrivers={[]}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={false}
        error={null}
      />
    );

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('calls onOptimize when button is clicked', () => {
    render(
      <OptimizerPanel
        selectedDrivers={mockDrivers}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={false}
        error={null}
      />
    );

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(mockOnOptimize).toHaveBeenCalledWith(mockDrivers);
  });

  it('shows loading state', () => {
    render(
      <OptimizerPanel
        selectedDrivers={mockDrivers}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={true}
        error={null}
      />
    );

    expect(screen.getByText('Optimizing...')).toBeInTheDocument();
  });

  it('displays error message when provided', () => {
    render(
      <OptimizerPanel
        selectedDrivers={[]}
        onOptimize={mockOnOptimize}
        optimizedLineup={null}
        isLoading={false}
        error="Optimization failed"
      />
    );

    expect(screen.getByText('Optimization failed')).toBeInTheDocument();
  });

  it('displays optimized lineup when provided', () => {
    render(
      <OptimizerPanel
        selectedDrivers={mockDrivers}
        onOptimize={mockOnOptimize}
        optimizedLineup={mockOptimizedLineup}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByText('Optimized Lineup')).toBeInTheDocument();
    expect(screen.getByText('Total Salary: $20,300')).toBeInTheDocument();
    expect(screen.getByText('Total Projected Points: 103.7')).toBeInTheDocument();
    expect(screen.getByText('Average Value: 0.0051')).toBeInTheDocument();
    expect(screen.getByText('Drivers: 2')).toBeInTheDocument();
  });

  it('displays lineup driver table', () => {
    render(
      <OptimizerPanel
        selectedDrivers={mockDrivers}
        onOptimize={mockOnOptimize}
        optimizedLineup={mockOptimizedLineup}
        isLoading={false}
        error={null}
      />
    );

    expect(screen.getByText('Kyle Larson')).toBeInTheDocument();
    expect(screen.getByText('Chase Elliott')).toBeInTheDocument();
    expect(screen.getByText('$10,500')).toBeInTheDocument();
    expect(screen.getByText('55.5')).toBeInTheDocument();
  });
});
