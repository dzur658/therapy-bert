import json
import os

import torch
from torch import nn
from torchcrf import CRF
from transformers import AutoConfig, AutoModel

from safetensors.torch import save_file, load_file


class ModernBERT_CRF(nn.Module):
    def __init__(
        self,
        num_labels,
        label2id,
        id2label=None,
        model_name=None,
        backbone_config=None,
        dropout=0.1,
    ):
        super().__init__()

        if model_name is None and backbone_config is None:
            raise ValueError("Provide either model_name or backbone_config.")

        self.num_labels = num_labels
        self.label2id = dict(label2id)
        self.id2label = (
            {int(key): value for key, value in id2label.items()}
            if id2label is not None
            else {value: key for key, value in label2id.items()}
        )
        self.model_name = model_name
        self.dropout_prob = dropout

        if backbone_config is not None:
            self.bert = AutoModel.from_config(backbone_config)
        else:
            self.bert = AutoModel.from_pretrained(model_name)

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)
        self.crf = CRF(num_labels, batch_first=True)

        # Mathematically disincentivize breaking IOB rules
        with torch.no_grad():
            for i in range(num_labels):
                tag = self.id2label[i]
                # Rule 1: Sequences cannot START with an I- tag
                if tag.startswith("I-"):
                    self.crf.start_transitions.data[i] = -10000.0
                    
                # Rule 2: I- tags can only follow B- or I- of the same entity
                for j in range(num_labels):
                    next_tag = self.id2label[j]
                    if next_tag.startswith("I-"):
                        entity_type = next_tag[2:]
                        valid_prev = [f"B-{entity_type}", f"I-{entity_type}"]
                        if tag not in valid_prev:
                            self.crf.transitions.data[i, j] = -10000.0

    def forward(self, input_ids, attention_mask, labels=None, **kwargs):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)

        sequence_output = self.dropout(outputs.last_hidden_state)
        emissions = self.classifier(sequence_output)

        mask = attention_mask.bool()

        if labels is None:
            predictions = self.crf.decode(emissions, mask=mask)
            return {"logits": emissions, "predictions": predictions}

        safe_labels = labels.masked_fill(labels == -100, 0).long()
        loss = -self.crf(emissions, safe_labels, mask=mask, reduction="mean")

        return {"loss": loss, "logits": emissions}

    @torch.no_grad()
    def decode(self, input_ids, attention_mask):
        outputs = self.forward(input_ids=input_ids, attention_mask=attention_mask)
        return outputs["predictions"]

    def save_checkpoint(self, save_dir):
        os.makedirs(save_dir, exist_ok=True)

        backbone_dir = os.path.join(save_dir, "backbone")
        os.makedirs(backbone_dir, exist_ok=True)
        self.bert.config.save_pretrained(backbone_dir)

        save_file(self.state_dict(), os.path.join(save_dir, "model.safetensors"))

        metadata = {
            "num_labels": self.num_labels,
            "label2id": self.label2id,
            "id2label": self.id2label,
            "model_name": self.model_name,
            "dropout": self.dropout_prob,
        }

        with open(os.path.join(save_dir, "model_meta.json"), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

    @classmethod
    def from_checkpoint(cls, save_dir, map_location=None):
        with open(os.path.join(save_dir, "model_meta.json"), "r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        backbone_config = AutoConfig.from_pretrained(os.path.join(save_dir, "backbone"))

        model = cls(
            num_labels=metadata["num_labels"],
            label2id=metadata["label2id"],
            id2label=metadata["id2label"],
            model_name=metadata.get("model_name"),
            backbone_config=backbone_config,
            dropout=metadata.get("dropout", 0.1),
        )

        state_dict = load_file(
            os.path.join(save_dir, "model.safetensors"),
            device=str(map_location) if map_location is not None else "cpu",
        )
        model.load_state_dict(state_dict)
        return model