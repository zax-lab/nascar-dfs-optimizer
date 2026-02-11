"""
Tests for the NASCAR dataset module.

This module contains unit tests for the NASCARDataset class and related
functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from nascar_dataset import NASCARDataset, NASCARSample, create_synthetic_dataset


class TestNASCARDataset:
    """Test cases for the NASCARDataset class."""

    def test_create_synthetic_dataset(self) -> None:
        """Test creating a synthetic dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=10, seed=42)

            assert output_path.exists()

            # Verify the file contains the expected number of samples
            with open(output_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                assert len(lines) == 10

    def test_load_synthetic_dataset(self) -> None:
        """Test loading a synthetic dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            # Create synthetic dataset
            create_synthetic_dataset(output_path, num_samples=10, seed=42)

            # Load the dataset
            dataset = NASCARDataset(data_path=output_path)

            assert len(dataset) == 10

    def test_dataset_getitem_without_tokenizer(self) -> None:
        """Test getting items from the dataset without a tokenizer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=5, seed=42)

            dataset = NASCARDataset(data_path=output_path)

            sample = dataset[0]

            # Verify sample structure
            assert "driver" in sample
            assert "track" in sample
            assert "logic_phase" in sample
            assert "ontology_phase" in sample
            assert "narrative_phase" in sample
            assert "projected_points" in sample
            assert isinstance(sample["projected_points"], float)

    def test_dataset_get_sample(self) -> None:
        """Test getting a raw NASCARSample from the dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=5, seed=42)

            dataset = NASCARDataset(data_path=output_path)

            sample = dataset.get_sample(0)

            assert isinstance(sample, NASCARSample)
            assert isinstance(sample.driver, str)
            assert isinstance(sample.track, str)
            assert isinstance(sample.logic_phase, dict)
            assert isinstance(sample.ontology_phase, dict)
            assert isinstance(sample.narrative_phase, dict)
            assert isinstance(sample.projected_points, float)

    def test_dataset_split(self) -> None:
        """Test splitting the dataset into train and validation sets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=20, seed=42)

            dataset = NASCARDataset(data_path=output_path)

            train_dataset, val_dataset = dataset.split(train_ratio=0.8, seed=42)

            assert len(train_dataset) == 16
            assert len(val_dataset) == 4

    def test_dataset_with_custom_sample(self) -> None:
        """Test loading a dataset with custom samples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "custom_data.jsonl"

            custom_sample = {
                "driver": "Test Driver",
                "track": "Test Track",
                "logic_phase": {"track_type": "Superspeedway", "weather": "Sunny"},
                "ontology_phase": {"car_number": 1, "driver_rating": 95.0},
                "narrative_phase": {"recent_finish": 1, "momentum": "High"},
                "projected_points": 150.5,
                "metadata": {"test": True},
            }

            with open(output_path, "w") as f:
                f.write(json.dumps(custom_sample) + "\n")

            dataset = NASCARDataset(data_path=output_path)

            assert len(dataset) == 1
            sample = dataset[0]
            assert sample["driver"] == "Test Driver"
            assert sample["track"] == "Test Track"
            assert sample["projected_points"] == 150.5

    def test_dataset_invalid_json(self) -> None:
        """Test that invalid JSON lines are skipped with a warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "invalid_data.jsonl"

            valid_sample = {
                "driver": "Valid Driver",
                "track": "Valid Track",
                "logic_phase": {},
                "ontology_phase": {},
                "narrative_phase": {},
                "projected_points": 100.0,
            }

            with open(output_path, "w") as f:
                f.write(json.dumps(valid_sample) + "\n")
                f.write("invalid json line\n")
                f.write(json.dumps(valid_sample) + "\n")

            dataset = NASCARDataset(data_path=output_path)

            # Should load only the valid samples
            assert len(dataset) == 2

    def test_dataset_missing_required_field(self) -> None:
        """Test that samples with missing required fields are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "missing_field_data.jsonl"

            valid_sample = {
                "driver": "Valid Driver",
                "track": "Valid Track",
                "logic_phase": {},
                "ontology_phase": {},
                "narrative_phase": {},
                "projected_points": 100.0,
            }

            invalid_sample = {
                "driver": "Invalid Driver",
                "track": "Invalid Track",
                # Missing logic_phase
                "ontology_phase": {},
                "narrative_phase": {},
                "projected_points": 100.0,
            }

            with open(output_path, "w") as f:
                f.write(json.dumps(valid_sample) + "\n")
                f.write(json.dumps(invalid_sample) + "\n")

            dataset = NASCARDataset(data_path=output_path)

            # Should load only the valid sample
            assert len(dataset) == 1

    def test_dataset_invalid_projected_points(self) -> None:
        """Test that samples with invalid projected_points are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "invalid_points_data.jsonl"

            valid_sample = {
                "driver": "Valid Driver",
                "track": "Valid Track",
                "logic_phase": {},
                "ontology_phase": {},
                "narrative_phase": {},
                "projected_points": 100.0,
            }

            invalid_sample = {
                "driver": "Invalid Driver",
                "track": "Invalid Track",
                "logic_phase": {},
                "ontology_phase": {},
                "narrative_phase": {},
                "projected_points": "not a number",
            }

            with open(output_path, "w") as f:
                f.write(json.dumps(valid_sample) + "\n")
                f.write(json.dumps(invalid_sample) + "\n")

            dataset = NASCARDataset(data_path=output_path)

            # Should load only the valid sample
            assert len(dataset) == 1

    def test_dataset_index_error(self) -> None:
        """Test that accessing an invalid index raises IndexError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "synthetic_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=5, seed=42)

            dataset = NASCARDataset(data_path=output_path)

            with pytest.raises(IndexError):
                _ = dataset[10]

            with pytest.raises(IndexError):
                _ = dataset[-1]

    def test_dataset_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError):
            NASCARDataset(data_path="non_existent_file.jsonl")
