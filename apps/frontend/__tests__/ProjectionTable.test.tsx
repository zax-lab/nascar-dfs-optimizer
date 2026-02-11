import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectionTable } from '../src/components/ProjectionTable';

describe('ProjectionTable', () => {
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

  const mockOnDriverSelect = jest.fn();

  it('renders driver table with correct headers', () => {
    render(
      <ProjectionTable
        drivers={mockDrivers}
        onDriverSelect={mockOnDriverSelect}
        selectedDriverIds={new Set()}
      />
    );

    expect(screen.getByText('Driver Projections')).toBeInTheDocument();
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('Driver')).toBeInTheDocument();
    expect(screen.getByText('Salary')).toBeInTheDocument();
    expect(screen.getByText('Projected Pts')).toBeInTheDocument();
    expect(screen.getByText('Value (Pts/$)')).toBeInTheDocument();
  });

  it('renders driver data correctly', () => {
    render(
      <ProjectionTable
        drivers={mockDrivers}
        onDriverSelect={mockOnDriverSelect}
        selectedDriverIds={new Set()}
      />
    );

    expect(screen.getByText('Kyle Larson')).toBeInTheDocument();
    expect(screen.getByText('Chase Elliott')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('$10,500')).toBeInTheDocument();
    expect(screen.getByText('55.5')).toBeInTheDocument();
  });

  it('calls onDriverSelect when checkbox is clicked', () => {
    render(
      <ProjectionTable
        drivers={mockDrivers}
        onDriverSelect={mockOnDriverSelect}
        selectedDriverIds={new Set()}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(2);

    fireEvent.click(checkboxes[0]);
    expect(mockOnDriverSelect).toHaveBeenCalledWith('1');
  });

  it('highlights selected drivers', () => {
    render(
      <ProjectionTable
        drivers={mockDrivers}
        onDriverSelect={mockOnDriverSelect}
        selectedDriverIds={new Set(['1'])}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).not.toBeChecked();
  });
});
