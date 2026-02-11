"""
Projection model module for NASCAR DFS point projections.

This module provides inference helpers for generating driver point projections
using the fine-tuned TinyLlama model. It exposes a thin wrapper for the
Backend Engineer to call.
"""

import os
from typing import Any, Dict, Optional, Union

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizer


class ProjectionModel:
    """
    Inference wrapper for NASCAR DFS point projections.

    This class provides a simple interface for generating driver point
    projections using a fine-tuned TinyLlama model.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
    ) -> None:
        """
        Initialize the ProjectionModel.

        Args:
            model_path: Path to the fine-tuned model. If None, uses
                       TINYLLAMA_CHECKPOINT environment variable.
            device: Device to run inference on ("auto", "cpu", "cuda", "mps")
        """
        if model_path is None:
            model_path = os.getenv("TINYLLAMA_CHECKPOINT", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

        self.model_path = model_path
        self.device = self._get_device(device)

        print(f"Loading projection model from: {model_path}")

        self.tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model: PreTrainedModel = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() or self.device == "mps" else torch.float32,
        )
        self.model = self.model.to(self.device)
        self.model.eval()

        print(f"Projection model loaded on device: {self.device}")

    def _get_device(self, device: str) -> str:
        """
        Determine the appropriate device for inference.

        Args:
            device: Device specification

        Returns:
            Device string
        """
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device

    def _format_prompt(
        self,
        driver: str,
        track: str,
        logic_phase: Dict[str, Any],
        ontology_phase: Dict[str, Any],
        narrative_phase: Dict[str, Any],
    ) -> str:
        """
        Format input features into a prompt for the model.

        Args:
            driver: Driver name or identifier
            track: Track name or identifier
            logic_phase: Logic phase features
            ontology_phase: Ontology phase features
            narrative_phase: Narrative phase features

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Driver: {driver}",
            f"Track: {track}",
            "",
            "Logic Phase:",
            self._format_phase(logic_phase),
            "",
            "Ontology Phase:",
            self._format_phase(ontology_phase),
            "",
            "Narrative Phase:",
            self._format_phase(narrative_phase),
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

    def _parse_projection(self, output_text: str) -> float:
        """
        Parse the model output to extract the projected points.

        Args:
            output_text: Raw model output text

        Returns:
            Projected points as a float
        """
        # Try to extract a numeric value from the output
        import re

        # Look for patterns like "Projected Points: 123.45" or just numbers
        patterns = [
            r"Projected Points:\s*([+-]?\d+\.?\d*)",
            r"([+-]?\d+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output_text)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue

        # If no number found, return a default value
        print(f"Warning: Could not parse projection from output: {output_text}")
        return 0.0

    def predict(
        self,
        driver: str,
        track: str,
        logic_phase: Dict[str, Any],
        ontology_phase: Dict[str, Any],
        narrative_phase: Dict[str, Any],
        max_new_tokens: int = 32,
        temperature: float = 0.7,
        do_sample: bool = False,
    ) -> float:
        """
        Generate a point projection for a driver at a track.

        Args:
            driver: Driver name or identifier
            track: Track name or identifier
            logic_phase: Logic phase features (e.g., track type, weather)
            ontology_phase: Ontology phase features (e.g., driver stats, car info)
            narrative_phase: Narrative phase features (e.g., recent performance)
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            do_sample: Whether to use sampling (vs. greedy decoding)

        Returns:
            Projected points as a float
        """
        prompt = self._format_prompt(driver, track, logic_phase, ontology_phase, narrative_phase)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the generated portion
        generated_text = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)

        projected_points = self._parse_projection(generated_text)

        return projected_points

    def predict_batch(
        self,
        samples: list[Dict[str, Any]],
        max_new_tokens: int = 32,
        temperature: float = 0.7,
        do_sample: bool = False,
    ) -> list[float]:
        """
        Generate point projections for a batch of samples.

        Args:
            samples: List of sample dictionaries, each containing driver, track,
                    logic_phase, ontology_phase, and narrative_phase
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            do_sample: Whether to use sampling (vs. greedy decoding)

        Returns:
            List of projected points
        """
        projections = []

        for sample in samples:
            projection = self.predict(
                driver=sample["driver"],
                track=sample["track"],
                logic_phase=sample["logic_phase"],
                ontology_phase=sample["ontology_phase"],
                narrative_phase=sample["narrative_phase"],
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=do_sample,
            )
            projections.append(projection)

        return projections


def get_projection(
    driver: str,
    track: str,
    logic_phase: Dict[str, Any],
    ontology_phase: Dict[str, Any],
    narrative_phase: Dict[str, Any],
    model_path: Optional[str] = None,
) -> float:
    """
    Thin wrapper function for Backend Engineer to call.

    This function provides a simple interface for generating driver point
    projections without needing to manage the model lifecycle.

    Args:
        driver: Driver name or identifier
        track: Track name or identifier
        logic_phase: Logic phase features (e.g., track type, weather)
        ontology_phase: Ontology phase features (e.g., driver stats, car info)
        narrative_phase: Narrative phase features (e.g., recent performance)
        model_path: Optional path to the fine-tuned model. If None, uses
                   TINYLLAMA_CHECKPOINT environment variable.

    Returns:
        Projected points as a float

    Example:
        >>> logic_phase = {"track_type": "Superspeedway", "weather": "Sunny"}
        >>> ontology_phase = {"driver_rating": 95.5, "car_number": 5}
        >>> narrative_phase = {"recent_finish": 1, "momentum": "High"}
        >>> points = get_projection("Kyle Larson", "Daytona", logic_phase, ontology_phase, narrative_phase)
        >>> print(f"Projected points: {points}")
    """
    # Create model instance (in production, this should be cached)
    model = ProjectionModel(model_path=model_path)

    # Generate projection
    projection = model.predict(
        driver=driver,
        track=track,
        logic_phase=logic_phase,
        ontology_phase=ontology_phase,
        narrative_phase=narrative_phase,
    )

    return projection


class ProjectionModelCache:
    """
    Singleton cache for the ProjectionModel to avoid repeated loading.

    In production, the model should be loaded once and reused across requests.
    """

    _instance: Optional[ProjectionModel] = None
    _model_path: Optional[str] = None

    @classmethod
    def get_model(cls, model_path: Optional[str] = None) -> ProjectionModel:
        """
        Get or create the cached ProjectionModel instance.

        Args:
            model_path: Optional path to the model

        Returns:
            ProjectionModel instance
        """
        if cls._instance is None or (model_path is not None and cls._model_path != model_path):
            cls._instance = ProjectionModel(model_path=model_path)
            cls._model_path = model_path

        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the cached model instance."""
        cls._instance = None
        cls._model_path = None


def get_projection_cached(
    driver: str,
    track: str,
    logic_phase: Dict[str, Any],
    ontology_phase: Dict[str, Any],
    narrative_phase: Dict[str, Any],
    model_path: Optional[str] = None,
) -> float:
    """
    Thin wrapper function using cached model for better performance.

    This function provides a simple interface for generating driver point
    projections using a cached model instance.

    Args:
        driver: Driver name or identifier
        track: Track name or identifier
        logic_phase: Logic phase features (e.g., track type, weather)
        ontology_phase: Ontology phase features (e.g., driver stats, car info)
        narrative_phase: Narrative phase features (e.g., recent performance)
        model_path: Optional path to the fine-tuned model. If None, uses
                   TINYLLAMA_CHECKPOINT environment variable.

    Returns:
        Projected points as a float
    """
    model = ProjectionModelCache.get_model(model_path=model_path)

    projection = model.predict(
        driver=driver,
        track=track,
        logic_phase=logic_phase,
        ontology_phase=ontology_phase,
        narrative_phase=narrative_phase,
    )

    return projection
