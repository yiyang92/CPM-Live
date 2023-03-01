import torch
from typing import Dict


def pad(orig_items, key, padding_value=0, padding_side="left"):
    items = []
    if isinstance(orig_items[0][key], list):
        assert isinstance(orig_items[0][key][0], torch.Tensor)
        for it in orig_items:
            for tr in it[key]:
                items.append({key: tr})
    else:
        assert isinstance(orig_items[0][key], torch.Tensor)
        items = orig_items

    batch_size = len(items)
    shape = items[0][key].shape
    dim = len(shape)
    assert dim <= 3
    max_length = max(item[key].shape[-1] for item in items)
    min_length = min(item[key].shape[-1] for item in items)
    dtype = items[0][key].dtype

    if dim == 1:
        return torch.cat([item[key] for item in items], dim=0)
    elif dim == 2:
        if max_length == min_length:
            return torch.cat([item[key] for item in items], dim=0)
        tensor = torch.zeros((batch_size, max_length), dtype=dtype) + padding_value
    else:
        tensor = torch.zeros((batch_size, max_length, shape[-1]), dtype=dtype) + padding_value

    for i, item in enumerate(items):
        if dim == 2:
            if padding_side == "left":
                tensor[i, -len(item[key][0]) :] = item[key][0].clone()
            else:
                tensor[i, : len(item[key][0])] = item[key][0].clone()
        elif dim == 3:
            if padding_side == "left":
                tensor[i, -len(item[key][0]) :, :] = item[key][0].clone()
            else:
                tensor[i, : len(item[key][0]), :] = item[key][0].clone()

    return tensor


def cat_prompt(padded_inputs: Dict[str, torch.Tensor], prompt_length: int, task_id: int = 2):
    input_ids = padded_inputs["input"]
    batch, dtype, device = input_ids.size(0), input_ids.dtype, input_ids.device
    padded_inputs["input"] = torch.cat(
        (
            torch.arange(
                prompt_length * task_id, 
                prompt_length * (task_id + 1), 
                dtype=dtype, 
                device=device
            ).repeat(batch, 1),
            input_ids,
        ),
        dim=1,
    )
    for k in ["context", "position", "span"]:
        if k == "context":
            cat_part = torch.ones(batch, prompt_length, dtype=dtype, device=device)
        else:
            cat_part = torch.zeros(batch, prompt_length, dtype=dtype, device=device)
        
        padded_inputs[k] = torch.cat(
            (cat_part, padded_inputs[k]), 
            dim=1,
        )
    return padded_inputs
