"""
TinyLlama fine-tuning module for NASCAR projection model.

This module provides model and tokenizer setup for TinyLlama, training loop
configuration, and loss computation with optional structural penalty for
axiomatic constraints (kernel veto).
"""

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
    Trainer,
    TrainingArguments,
)

from nascar_dataset import NASCARDataset


@dataclass
class TrainingConfig:
    """
    Configuration for TinyLlama fine-tuning.

    Attributes:
        model_name_or_path: HuggingFace model identifier or local path
        output_dir: Directory to save trained model
        num_train_epochs: Number of training epochs
        per_device_train_batch_size: Batch size per device for training
        per_device_eval_batch_size: Batch size per device for evaluation
        gradient_accumulation_steps: Number of gradient accumulation steps
        learning_rate: Learning rate for optimizer
        warmup_steps: Number of warmup steps
        logging_steps: Number of steps between logging
        save_steps: Number of steps between model checkpoints
        eval_steps: Number of steps between evaluations
        max_length: Maximum sequence length
        structural_penalty_weight: Weight for structural penalty (kernel veto)
        use_structural_penalty: Whether to apply structural penalty
    """

    model_name_or_path: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    output_dir: str = "./output/tinyllama-nascar"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 1
    learning_rate: float = 5e-5
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 500
    max_length: int = 512
    structural_penalty_weight: float = 0.1
    use_structural_penalty: bool = False


class StructuralLoss(nn.Module):
    """
    Structural loss for enforcing axiomatic constraints (kernel veto).

    This loss penalizes outputs that violate axiomatic constraints by
    masking invalid outputs and applying a penalty.
    """

    def __init__(self, weight: float = 0.1) -> None:
        """
        Initialize the structural loss.

        Args:
            weight: Weight for the structural penalty
        """
        super().__init__()
        self.weight = weight

    def forward(
        self,
        logits: torch.Tensor,
        labels: torch.Tensor,
        valid_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute the structural loss.

        Args:
            logits: Model output logits [batch_size, seq_len, vocab_size]
            labels: Target labels [batch_size, seq_len]
            valid_mask: Optional mask for valid outputs [batch_size, seq_len]

        Returns:
            Structural loss tensor
        """
        if valid_mask is None:
            return torch.tensor(0.0, device=logits.device, dtype=logits.dtype)

        # Penalize predictions for invalid positions
        probs = torch.softmax(logits, dim=-1)
        invalid_loss = torch.sum(probs * (1 - valid_mask.unsqueeze(-1)), dim=-1)
        invalid_loss = torch.mean(invalid_loss)

        return self.weight * invalid_loss


class AxiomaticTrainer(Trainer):
    """
    Custom HuggingFace Trainer with structural loss support.

    This trainer extends the standard HF Trainer to include structural
    penalty for axiomatic constraints.
    """

    def __init__(
        self,
        model: PreTrainedModel,
        args: TrainingArguments,
        train_dataset: Optional[NASCARDataset] = None,
        eval_dataset: Optional[NASCARDataset] = None,
        structural_loss: Optional[StructuralLoss] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the AxiomaticTrainer.

        Args:
            model: Pre-trained model
            args: Training arguments
            train_dataset: Training dataset
            eval_dataset: Evaluation dataset
            structural_loss: Optional structural loss module
            **kwargs: Additional arguments for Trainer
        """
        super().__init__(model=model, args=args, train_dataset=train_dataset, eval_dataset=eval_dataset, **kwargs)
        self.structural_loss = structural_loss

    def compute_loss(
        self,
        model: PreTrainedModel,
        inputs: Dict[str, torch.Tensor],
        return_outputs: bool = False,
    ) -> Union[torch.Tensor, tuple[torch.Tensor, Any]]:
        """
        Compute the total loss including structural penalty.

        Args:
            model: The model
            inputs: Input batch
            return_outputs: Whether to return model outputs

        Returns:
            Loss tensor, or tuple of (loss, outputs) if return_outputs=True
        """
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits

        # Standard cross-entropy loss
        loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))

        # Add structural penalty if enabled
        if self.structural_loss is not None:
            # Create valid mask (all positions are valid by default)
            valid_mask = torch.ones_like(shift_labels, dtype=torch.float)
            valid_mask[shift_labels == -100] = 0.0

            structural_penalty = self.structural_loss(shift_logits, shift_labels, valid_mask)
            loss = loss + structural_penalty

        return (loss, outputs) if return_outputs else loss


def load_model_and_tokenizer(
    model_name_or_path: Optional[str] = None,
    device_map: str = "auto",
) -> tuple[PreTrainedModel, PreTrainedTokenizer]:
    """
    Load the TinyLlama model and tokenizer.

    Args:
        model_name_or_path: HuggingFace model identifier or local path.
                           If None, uses TINYLLAMA_CHECKPOINT env var.
        device_map: Device mapping strategy

    Returns:
        Tuple of (model, tokenizer)
    """
    if model_name_or_path is None:
        model_name_or_path = os.getenv("TINYLLAMA_CHECKPOINT", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    print(f"Loading model from: {model_name_or_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        trust_remote_code=True,
        device_map=device_map,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )

    print(f"Model loaded successfully on device: {model.device}")

    return model, tokenizer


def create_trainer(
    config: TrainingConfig,
    train_dataset: NASCARDataset,
    eval_dataset: Optional[NASCARDataset] = None,
) -> AxiomaticTrainer:
    """
    Create a configured AxiomaticTrainer.

    Args:
        config: Training configuration
        train_dataset: Training dataset
        eval_dataset: Optional evaluation dataset

    Returns:
        Configured AxiomaticTrainer instance
    """
    # Load model and tokenizer
    model, tokenizer = load_model_and_tokenizer(config.model_name_or_path)

    # Configure dataset with tokenizer
    train_dataset.tokenizer = tokenizer
    train_dataset.max_length = config.max_length

    if eval_dataset is not None:
        eval_dataset.tokenizer = tokenizer
        eval_dataset.max_length = config.max_length

    # Create structural loss if enabled
    structural_loss = None
    if config.use_structural_penalty:
        structural_loss = StructuralLoss(weight=config.structural_penalty_weight)

    # Create training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=config.warmup_steps,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        eval_steps=config.eval_steps,
        evaluation_strategy="steps" if eval_dataset is not None else "no",
        save_strategy="steps",
        load_best_model_at_end=True if eval_dataset is not None else False,
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=0,
        remove_unused_columns=False,
    )

    # Create trainer
    trainer = AxiomaticTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        structural_loss=structural_loss,
        tokenizer=tokenizer,
    )

    return trainer


def train_model(
    config: TrainingConfig,
    train_dataset: NASCARDataset,
    eval_dataset: Optional[NASCARDataset] = None,
) -> AxiomaticTrainer:
    """
    Train the TinyLlama model on NASCAR data.

    Args:
        config: Training configuration
        train_dataset: Training dataset
        eval_dataset: Optional evaluation dataset

    Returns:
        Trained AxiomaticTrainer instance
    """
    trainer = create_trainer(config, train_dataset, eval_dataset)

    print("Starting training...")
    trainer.train()

    print("Training completed. Saving model...")
    trainer.save_model(config.output_dir)
    trainer.tokenizer.save_pretrained(config.output_dir)

    return trainer


def custom_training_loop(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    train_dataset: NASCARDataset,
    eval_dataset: Optional[NASCARDataset] = None,
    num_epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 5e-5,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    structural_loss: Optional[StructuralLoss] = None,
) -> PreTrainedModel:
    """
    Custom training loop for fine-tuning TinyLlama.

    This provides an alternative to the HuggingFace Trainer with more
    explicit control over the training process.

    Args:
        model: Pre-trained model
        tokenizer: Tokenizer
        train_dataset: Training dataset
        eval_dataset: Optional evaluation dataset
        num_epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        device: Device to train on
        structural_loss: Optional structural loss module

    Returns:
        Trained model
    """
    model = model.to(device)
    model.train()

    # Configure dataset
    train_dataset.tokenizer = tokenizer
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    # Setup optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    # Loss function
    loss_fct = nn.CrossEntropyLoss(ignore_index=-100)

    print(f"Starting custom training loop on {device}...")

    for epoch in range(num_epochs):
        total_loss = 0.0
        num_batches = 0

        for batch_idx, batch in enumerate(train_dataloader):
            # Move batch to device
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            # Forward pass
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits

            # Compute loss
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))

            # Add structural penalty if enabled
            if structural_loss is not None:
                valid_mask = torch.ones_like(shift_labels, dtype=torch.float)
                valid_mask[shift_labels == -100] = 0.0
                penalty = structural_loss(shift_logits, shift_labels, valid_mask)
                loss = loss + penalty

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            num_batches += 1

            if (batch_idx + 1) % 10 == 0:
                avg_loss = total_loss / num_batches
                print(f"Epoch {epoch + 1}/{num_epochs}, Batch {batch_idx + 1}, Loss: {avg_loss:.4f}")

        avg_epoch_loss = total_loss / num_batches
        print(f"Epoch {epoch + 1}/{num_epochs} completed. Average loss: {avg_epoch_loss:.4f}")

    model.eval()
    print("Training completed.")

    return model
