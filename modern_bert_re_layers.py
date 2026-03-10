import torch
from torch import nn
from torch.nn import CrossEntropyLoss
from transformers import AutoModel, AutoConfig

import os
import json
from safetensors.torch import save_file, load_file

class ModernBERT_Entity_Pooling_RE(nn.Module):
    def __init__(self, 
                 model_name, 
                 num_labels, 
                 tokenizer,
                 label2id=None,
                 id2label=None,
                 backbone_config=None,):
        super().__init__()
        
        self.num_labels = num_labels
        self.model_name = model_name
        self.label2id = dict(label2id or {})
        self.id2label = (
            {int(k): v for k, v in id2label.items()}
            if id2label is not None
            else {}
        )

        if backbone_config is not None:
            self.bert = AutoModel.from_config(backbone_config)
        else:
            self.bert = AutoModel.from_pretrained(model_name,
                                                reference_compile=False,       # 1. Kills the broken ModernBERT compile paths that stall MPS
                                                attn_implementation="sdpa",    # 2. Forces PyTorch's native Scaled Dot Product Attention (avoids worst-case Math fallback)
                                                torch_dtype=torch.bfloat16)

        # CRITICAL: Resize embedding matrix for the 4 new special tokens
        self.bert.resize_token_embeddings(len(tokenizer))
        
        # Save token IDs so we can hunt them down in the tensor during the forward pass
        self.e1_token_id = tokenizer.convert_tokens_to_ids("[E1]")
        self.e2_token_id = tokenizer.convert_tokens_to_ids("[E2]")
        
        self.dropout = nn.Dropout(0.1)
        # We concatenate E1 (1024) + E2 (1024) = 2048 input dimensions
        self.classifier = nn.Linear(self.bert.config.hidden_size * 2, num_labels)

    def forward(self, input_ids, attention_mask, labels=None, **kwargs):
        # 1. Get the base contextual embeddings
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state # Shape: [Batch, Seq_Len, 1024]
        
        # 2. Vectorized hunting for [E1] and [E2] markers (No CPU Syncs!)
        # Cast boolean to int, argmax finds the index of the '1'
        e1_mask = input_ids == self.e1_token_id
        e2_mask = input_ids == self.e2_token_id

        has_e1 = e1_mask.any(dim=-1)
        has_e2 = e2_mask.any(dim=-1)

        if not torch.all(has_e1 & has_e2):
            raise ValueError("All examples must contain both [E1] and [E2] tokens.")
        
        e1_indices = e1_mask.int().argmax(dim=-1)  # Shape: [Batch]
        e2_indices = e2_mask.int().argmax(dim=-1)  # Shape
        
        # Create a batch index array: [0, 1, 2, ..., batch_size-1]
        batch_indices = torch.arange(input_ids.size(0), device=input_ids.device)
        
        # Instantly extract the 1024-dim vectors for the whole batch
        e1_states = sequence_output[batch_indices, e1_indices]
        e2_states = sequence_output[batch_indices, e2_indices]
        
        # 3. CONCATENATE (The magic move)
        # Shape becomes: [Batch, 2048]
        pooled_output = torch.cat([e1_states, e2_states], dim=-1)
        pooled_output = self.dropout(pooled_output)
        
        # 4. Classify
        logits = self.classifier(pooled_output)
        
        loss = None
        if labels is not None:
            loss_fct = CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
            
        return {"loss": loss, "logits": logits} if loss is not None else {"logits": logits}
    
    def save_checkpoint(self, save_dir):
        os.makedirs(save_dir, exist_ok=True)

        backbone_dir = os.path.join(save_dir, "backbone")
        os.makedirs(backbone_dir, exist_ok=True)
        self.bert.config.save_pretrained(backbone_dir)

        save_file(self.state_dict(), os.path.join(save_dir, "model.safetensors"))

        metadata = {
            "num_labels": self.num_labels,
            "model_name": self.model_name,
            "label2id": self.label2id,
            "id2label": self.id2label,
        }
        with open(os.path.join(save_dir, "model_meta.json"), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

    @classmethod
    def from_checkpoint(cls, save_dir, tokenizer, map_location="cpu"):
        with open(os.path.join(save_dir, "model_meta.json"), "r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        backbone_config = AutoConfig.from_pretrained(os.path.join(save_dir, "backbone"))

        model = cls(
            model_name=metadata.get("model_name"),
            num_labels=metadata["num_labels"],
            tokenizer=tokenizer,
            label2id=metadata.get("label2id"),
            id2label=metadata.get("id2label"),
            backbone_config=backbone_config,
        )

        state_dict = load_file(
            os.path.join(save_dir, "model.safetensors"),
            device=str(map_location),
        )
        model.load_state_dict(state_dict)
        return model