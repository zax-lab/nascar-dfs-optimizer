"""
Tests for the projection model module.

This module contains unit tests for the ProjectionModel class and related
functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch

from nascar_dataset import create_synthetic_dataset, NASCARDataset
from projection_model import ProjectionModel, ProjectionModelCache, get_projection, get_projection_cached
from tinyllama_finetune import TrainingConfig, load_model_and_tokenizer, StructuralLoss


class TestStructuralLoss:
    """Test cases for the StructuralLoss class."""

    def test_structural_loss_init(self) -> None:
        """Test initializing StructuralLoss."""
        loss_fn = StructuralLoss(weight=0.5)
        assert loss_fn.weight == 0.5

    def test_structural_loss_no_mask(self) -> None:
        """Test StructuralLoss with no valid mask."""
        loss_fn = StructuralLoss(weight=0.1)

        logits = torch.randn(2, 10, 100)
        labels = torch.randint(0, 100, (2, 10))

        loss = loss_fn(logits, labels, valid_mask=None)

        assert loss.item() == 0.0

    def test_structural_loss_with_mask(self) -> None:
        """Test StructuralLoss with a valid mask."""
        loss_fn = StructuralLoss(weight=0.1)

        logits = torch.randn(2, 10, 100)
        labels = torch.randint(0, 100, (2, 10))
        valid_mask = torch.ones(2, 10)

        loss = loss_fn(logits, labels, valid_mask)

        # Loss should be positive
        assert loss.item() >= 0.0


class TestTrainingConfig:
    """Test cases for the TrainingConfig class."""

    def test_training_config_defaults(self) -> None:
        """Test TrainingConfig with default values."""
        config = TrainingConfig()

        assert config.model_name_or_path == "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        assert config.num_train_epochs == 3
        assert config.learning_rate == 5e-5
        assert config.use_structural_penalty is False

    def test_training_config_custom(self) -> None:
        """Test TrainingConfig with custom values."""
        config = TrainingConfig(
            num_train_epochs=5,
            learning_rate=1e-4,
            use_structural_penalty=True,
            structural_penalty_weight=0.5,
        )

        assert config.num_train_epochs == 5
        assert config.learning_rate == 1e-4
        assert config.use_structural_penalty is True
        assert config.structural_penalty_weight == 0.5


class TestProjectionModel:
    """Test cases for the ProjectionModel class."""

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_projection_model_init(self, mock_tokenizer, mock_model) -> None:
        """Test initializing ProjectionModel."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>")
        mock_model.return_value = MagicMock()

        model = ProjectionModel(model_path="dummy_path", device="cpu")

        assert model.model_path == "dummy_path"
        assert model.device == "cpu"

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_format_prompt(self, mock_tokenizer, mock_model) -> None:
        """Test formatting a prompt for the model."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>")
        mock_model.return_value = MagicMock()

        model = ProjectionModel(model_path="dummy_path", device="cpu")

        prompt = model._format_prompt(
            driver="Kyle Larson",
            track="Daytona",
            logic_phase={"track_type": "Superspeedway"},
            ontology_phase={"driver_rating": 95.0},
            narrative_phase={"recent_finish": 1},
        )

        assert "Driver: Kyle Larson" in prompt
        assert "Track: Daytona" in prompt
        assert "Logic Phase:" in prompt
        assert "Ontology Phase:" in prompt
        assert "Narrative Phase:" in prompt
        assert "Projected Points:" in prompt

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_format_phase(self, mock_tokenizer, mock_model) -> None:
        """Test formatting a phase dictionary."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>")
        mock_model.return_value = MagicMock()

        model = ProjectionModel(model_path="dummy_path", device="cpu")

        phase_str = model._format_phase({"key1": "value1", "key2": "value2"})

        assert "key1: value1" in phase_str
        assert "key2: value2" in phase_str

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_parse_projection_number(self, mock_tokenizer, mock_model) -> None:
        """Test parsing projection from numeric output."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>")
        mock_model.return_value = MagicMock()

        model = ProjectionModel(model_path="dummy_path", device="cpu")

        # Test with "Projected Points: 123.45" format
        projection = model._parse_projection("Projected Points: 123.45")
        assert projection == 123.45

        # Test with just a number
        projection = model._parse_projection("99.5")
        assert projection == 99.5

    @patch("projection_model.AutoModelForCausalLM.from_pretrained")
    @patch("projection_model.AutoTokenizer.from_pretrained")
    def test_parse_projection_invalid(self, mock_tokenizer, mock_model) -> None:
        """Test parsing projection from invalid output."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>")
        mock_model.return_value = MagicMock()

        model = ProjectionModel(model_path="dummy_path", device="cpu")

        # Test with no number
        projection = model._parse_projection("no number here")
        assert projection == 0.0


class TestProjectionModelCache:
    """Test cases for the ProjectionModelCache class."""

    @patch("projection_model.ProjectionModel")
    def test_get_model_creates_instance(self, mock_projection_model) -> None:
        """Test that get_model creates a new instance on first call."""
        mock_instance = MagicMock()
        mock_projection_model.return_value = mock_instance

        model = ProjectionModelCache.get_model(model_path="dummy_path")

        assert model == mock_instance
        mock_projection_model.assert_called_once_with(model_path="dummy_path")

    @patch("projection_model.ProjectionModel")
    def test_get_model_reuses_instance(self, mock_projection_model) -> None:
        """Test that get_model reuses the cached instance."""
        mock_instance = MagicMock()
        mock_projection_model.return_value = mock_instance

        model1 = ProjectionModelCache.get_model(model_path="dummy_path")
        model2 = ProjectionModelCache.get_model()

        assert model1 == model2
        # Should only create the instance once
        mock_projection_model.assert_called_once()

    @patch("projection_model.ProjectionModel")
    def test_get_model_different_path(self, mock_projection_model) -> None:
        """Test that get_model creates a new instance for different paths."""
        mock_instance1 = MagicMock()
        mock_instance2 = MagicMock()
        mock_projection_model.side_effect = [mock_instance1, mock_instance2]

        model1 = ProjectionModelCache.get_model(model_path="path1")
        model2 = ProjectionModelCache.get_model(model_path="path2")

        assert model1 == mock_instance1
        assert model2 == mock_instance2
        assert mock_projection_model.call_count == 2

    def test_reset_cache(self) -> None:
        """Test resetting the cache."""
        ProjectionModelCache.reset()

        assert ProjectionModelCache._instance is None
        assert ProjectionModelCache._model_path is None


class TestGetProjection:
    """Test cases for the get_projection wrapper function."""

    @patch("projection_model.ProjectionModel")
    def test_get_projection(self, mock_projection_model) -> None:
        """Test the get_projection wrapper function."""
        mock_instance = MagicMock()
        mock_instance.predict.return_value = 150.5
        mock_projection_model.return_value = mock_instance

        projection = get_projection(
            driver="Kyle Larson",
            track="Daytona",
            logic_phase={"track_type": "Superspeedway"},
            ontology_phase={"driver_rating": 95.0},
            narrative_phase={"recent_finish": 1},
            model_path="dummy_path",
        )

        assert projection == 150.5
        mock_instance.predict.assert_called_once()

    @patch("projection_model.ProjectionModelCache")
    def test_get_projection_cached(self, mock_cache) -> None:
        """Test the get_projection_cached wrapper function."""
        mock_instance = MagicMock()
        mock_instance.predict.return_value = 150.5
        mock_cache.get_model.return_value = mock_instance

        projection = get_projection_cached(
            driver="Kyle Larson",
            track="Daytona",
            logic_phase={"track_type": "Superspeedway"},
            ontology_phase={"driver_rating": 95.0},
            narrative_phase={"recent_finish": 1},
            model_path="dummy_path",
        )

        assert projection == 150.5
        mock_cache.get_model.assert_called_once_with(model_path="dummy_path")


class TestDatasetAndTraining:
    """Integration tests for dataset and training setup."""

    def test_create_and_load_tiny_dataset(self) -> None:
        """Test creating and loading a tiny dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "tiny_data.jsonl"

            # Create tiny dataset
            create_synthetic_dataset(output_path, num_samples=3, seed=42)

            # Load dataset
            dataset = NASCARDataset(data_path=output_path)

            assert len(dataset) == 3

            # Verify samples can be accessed
            sample = dataset[0]
            assert "driver" in sample
            assert "track" in sample
            assert "projected_points" in sample

    def test_dataset_split_tiny(self) -> None:
        """Test splitting a tiny dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "tiny_data.jsonl"

            create_synthetic_dataset(output_path, num_samples=10, seed=42)

            dataset = NASCARDataset(data_path=output_path)

            train_dataset, val_dataset = dataset.split(train_ratio=0.7, seed=42)

            assert len(train_dataset) == 7
            assert len(val_dataset) == 3

    @patch("tinyllama_finetune.AutoModelForCausalLM.from_pretrained")
    @patch("tinyllama_finetune.AutoTokenizer.from_pretrained")
    def test_load_model_and_tokenizer(self, mock_tokenizer, mock_model) -> None:
        """Test loading model and tokenizer."""
        mock_tokenizer.return_value = MagicMock(pad_token="<pad>", eos_token="</s>")
        mock_model.return_value = MagicMock(device="cpu")

        model, tokenizer = load_model_and_tokenizer(model_name_or_path="dummy_path", device_map="cpu")

        assert model is not None
        assert tokenizer is not None
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()

    @patch("tinyllama_finetune.AutoModelForCausalLM.from_pretrained")
    @patch("tinyllama_finetune.AutoTokenizer.from_pretrained")
    def test_load_model_and_tokenizer_env_var(self, mock_tokenizer, mock_model, monkeypatch) -> None:
        """Test loading model and tokenizer using environment variable."""
        monkeypatch.setenv("TINYLLAMA_CHECKPOINT", "env_path")

        mock_tokenizer.return_value = MagicMock(pad_token="<pad>", eos_token="</s>")
        mock_model.return_value = MagicMock(device="cpu")

        model, tokenizer = load_model_and_tokenizer(model_name_or_path=None, device_map="cpu")

        assert model is not None
        assert tokenizer is not None
        mock_tokenizer.assert_called_once_with("env_path", trust_remote_code=True)
        mock_model.assert_called_once()
