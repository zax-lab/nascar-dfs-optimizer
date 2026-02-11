"""
NASCAR Dataset module for loading and preparing JSONL samples.

This module provides the NASCARDataset class for handling training data
with support for logic, ontology, and narrative phases.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import torch
from torch.utils.data import Dataset


@dataclass
class NASCARSample:
    """
    Represents a single NASCAR training sample.

    Attributes:
        driver: Driver identifier or name
        track: Track identifier or name
        logic_phase: Logic phase features (e.g., track type, weather conditions)
        ontology_phase: Ontology phase features (e.g., driver stats, car info)
        narrative_phase: Narrative phase features (e.g., recent performance, storylines)
        projected_points: Target projected points value
        metadata: Additional metadata about the sample
    """

    driver: str
    track: str
    logic_phase: Dict[str, Any]
    ontology_phase: Dict[str, Any]
    narrative_phase: Dict[str, Any]
    projected_points: float
    metadata: Optional[Dict[str, Any]] = None


class NASCARDataset(Dataset):
    """
    PyTorch Dataset for loading and preparing NASCAR JSONL samples.

    This dataset loads samples from a JSONL file where each line contains
    a JSON object with driver, track, phase features, and projected points.
    """

    def __init__(
        self,
        data_path: Union[str, Path],
        tokenizer: Optional[Any] = None,
        max_length: int = 512,
        phase_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initialize the NASCARDataset.

        Args:
            data_path: Path to the JSONL file containing training samples
            tokenizer: Optional tokenizer for encoding text features
            max_length: Maximum sequence length for tokenization
            phase_weights: Optional weights for different phases (logic, ontology, narrative)
        """
        self.data_path = Path(data_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.phase_weights = phase_weights or {"logic": 1.0, "ontology": 1.0, "narrative": 1.0}

        self.samples: List[NASCARSample] = []
        self._load_samples()

    def _load_samples(self) -> None:
        """Load samples from the JSONL file."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    sample = self._parse_sample(data)
                    self.samples.append(sample)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num}: {e}")
                except (KeyError, ValueError) as e:
                    print(f"Warning: Invalid sample at line {line_num}: {e}")

        print(f"Loaded {len(self.samples)} samples from {self.data_path}")

    def _parse_sample(self, data: Dict[str, Any]) -> NASCARSample:
        """
        Parse a raw JSON dict into a NASCARSample.

        Args:
            data: Raw JSON dictionary

        Returns:
            Parsed NASCARSample

        Raises:
            KeyError: If required fields are missing
            ValueError: If data types are invalid
        """
        required_fields = ["driver", "track", "logic_phase", "ontology_phase", "narrative_phase", "projected_points"]
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Missing required field: {field}")

        if not isinstance(data["projected_points"], (int, float)):
            raise ValueError(f"projected_points must be numeric, got {type(data['projected_points'])}")

        return NASCARSample(
            driver=str(data["driver"]),
            track=str(data["track"]),
            logic_phase=dict(data["logic_phase"]),
            ontology_phase=dict(data["ontology_phase"]),
            narrative_phase=dict(data["narrative_phase"]),
            projected_points=float(data["projected_points"]),
            metadata=data.get("metadata"),
        )

    def _format_prompt(self, sample: NASCARSample) -> str:
        """
        Format a sample into a text prompt for the model.

        Args:
            sample: The NASCAR sample to format

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Driver: {sample.driver}",
            f"Track: {sample.track}",
            "",
            "Logic Phase:",
            self._format_phase(sample.logic_phase),
            "",
            "Ontology Phase:",
            self._format_phase(sample.ontology_phase),
            "",
            "Narrative Phase:",
            self._format_phase(sample.narrative_phase),
            "",
            "Projected Points:",
        ]

        return "\n".join(prompt_parts)

    def _format_phase(self, phase: Dict[str, Any]) -> str:
        """
        Format a phase dictionary into a string.

        Args:
            phase: Phase dictionary

        Returns:
            Formatted string representation
        """
        items = [f"  {key}: {value}" for key, value in phase.items()]
        return "\n".join(items)

    def __len__(self) -> int:
        """Return the number of samples in the dataset."""
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        Get a sample from the dataset.

        Args:
            idx: Index of the sample

        Returns:
            Dictionary containing the sample data
        """
        if idx < 0 or idx >= len(self.samples):
            raise IndexError(f"Index {idx} out of range for dataset of size {len(self.samples)}")

        sample = self.samples[idx]

        if self.tokenizer is not None:
            prompt = self._format_prompt(sample)
            target = str(sample.projected_points)

            # Tokenize prompt
            encoded_prompt = self.tokenizer(
                prompt,
                max_length=self.max_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )

            # Tokenize target
            encoded_target = self.tokenizer(
                target,
                max_length=32,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )

            return {
                "input_ids": encoded_prompt["input_ids"].squeeze(0),
                "attention_mask": encoded_prompt["attention_mask"].squeeze(0),
                "labels": encoded_target["input_ids"].squeeze(0),
                "target_attention_mask": encoded_target["attention_mask"].squeeze(0),
                "driver": sample.driver,
                "track": sample.track,
                "projected_points": sample.projected_points,
            }
        else:
            return {
                "driver": sample.driver,
                "track": sample.track,
                "logic_phase": sample.logic_phase,
                "ontology_phase": sample.ontology_phase,
                "narrative_phase": sample.narrative_phase,
                "projected_points": sample.projected_points,
                "metadata": sample.metadata,
            }

    def get_sample(self, idx: int) -> NASCARSample:
        """
        Get the raw NASCARSample at the given index.

        Args:
            idx: Index of the sample

        Returns:
            The raw NASCARSample
        """
        return self.samples[idx]

    def split(self, train_ratio: float = 0.8, seed: Optional[int] = None) -> tuple["NASCARDataset", "NASCARDataset"]:
        """
        Split the dataset into train and validation sets.

        Args:
            train_ratio: Ratio of data to use for training
            seed: Optional random seed for reproducibility

        Returns:
            Tuple of (train_dataset, val_dataset)
        """
        if seed is not None:
            import random

            random.seed(seed)

        indices = list(range(len(self)))
        import random

        random.shuffle(indices)

        split_idx = int(len(indices) * train_ratio)
        train_indices = indices[:split_idx]
        val_indices = indices[split_idx:]

        train_dataset = NASCARDataset(
            data_path=self.data_path,
            tokenizer=self.tokenizer,
            max_length=self.max_length,
            phase_weights=self.phase_weights,
        )
        train_dataset.samples = [self.samples[i] for i in train_indices]

        val_dataset = NASCARDataset(
            data_path=self.data_path,
            tokenizer=self.tokenizer,
            max_length=self.max_length,
            phase_weights=self.phase_weights,
        )
        val_dataset.samples = [self.samples[i] for i in val_indices]

        return train_dataset, val_dataset


def create_synthetic_dataset(
    output_path: Union[str, Path],
    num_samples: int = 100,
    seed: Optional[int] = None,
) -> None:
    """
    Create a synthetic NASCAR dataset for testing.

    Args:
        output_path: Path where the JSONL file will be saved
        num_samples: Number of synthetic samples to generate
        seed: Optional random seed for reproducibility
    """
    import random

    if seed is not None:
        random.seed(seed)

    drivers = [
        "Kyle Larson",
        "Chase Elliott",
        "Ross Chastain",
        "William Byron",
        "Martin Truex Jr.",
        "Denny Hamlin",
        "Joey Logano",
        "Ryan Blaney",
    ]

    tracks = [
        "Daytona",
        "Talladega",
        "Bristol",
        "Charlotte",
        "Indianapolis",
        "Watkins Glen",
        "Phoenix",
        "Martinsville",
    ]

    track_types = ["Superspeedway", "Short Track", "Intermediate", "Road Course"]

    with open(output_path, "w", encoding="utf-8") as f:
        for _ in range(num_samples):
            sample = {
                "driver": random.choice(drivers),
                "track": random.choice(tracks),
                "logic_phase": {
                    "track_type": random.choice(track_types),
                    "weather_condition": random.choice(["Sunny", "Cloudy", "Rain"]),
                    "temperature": round(random.uniform(60, 90), 1),
                },
                "ontology_phase": {
                    "car_number": random.randint(1, 99),
                    "team": f"Team {random.randint(1, 10)}",
                    "manufacturer": random.choice(["Chevrolet", "Ford", "Toyota"]),
                    "driver_rating": round(random.uniform(70, 100), 1),
                },
                "narrative_phase": {
                    "recent_finish": random.randint(1, 40),
                    "avg_finish_last_5": round(random.uniform(1, 40), 1),
                    "wins_this_season": random.randint(0, 5),
                    "momentum": random.choice(["High", "Medium", "Low"]),
                },
                "projected_points": round(random.uniform(0, 200), 2),
                "metadata": {
                    "race_date": "2024-01-01",
                    "session_id": f"synthetic_{random.randint(1000, 9999)}",
                },
            }
            f.write(json.dumps(sample) + "\n")

    print(f"Created synthetic dataset with {num_samples} samples at {output_path}")
