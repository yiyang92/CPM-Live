# coding=utf-8
# Copyright 2022 The OpenBMB team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import torch
from ..native_layers import Encoder, Embedding, SegmentPositionEmbedding
from .ant import CPMAntConfig


class CPMAntPlusTorch(torch.nn.Module):
    def __init__(self, config: CPMAntConfig):
        super().__init__()

        self.encoder = Encoder(
            num_layers=config.num_layers,
            dim_model=config.dim_model,
            dim_ff=config.dim_ff,
            num_heads=config.num_heads,
            dim_head=config.dim_head,
            dtype=config.dtype,
            eps=config.eps,
            dropout_p=config.dropout_p,
            mask_modules=config.mask_modules,
        )

        self.segment_embedding = Embedding(
            vocab_size=config.segment_types,
            embedding_size=config.dim_model,
            dtype=config.dtype,
            init_std=0.02,
        )

        self.input_embedding = Embedding(
            vocab_size=config.vocab_size
            + config.prompt_length * config.prompt_types,
            embedding_size=config.dim_model,
            dtype=config.dtype,
            init_std=0.02,
        )

        self.position_bias = SegmentPositionEmbedding(
            num_heads=config.num_heads,
            num_segments=config.segment_types,
            num_buckets=config.position_bias_num_buckets,
            max_distance=config.position_bias_max_distance,
            bidirectional=True,
            dtype=config.dtype,
        )

        self.prompt_length = config.prompt_length

    def forward(
        self,
        input: torch.Tensor,  # (batch, seqlen)
        length: torch.Tensor,  # (batch)
        context: torch.Tensor,  # (batch, seqlen)
        position: torch.Tensor,  # (batch, seqlen)
        segment: torch.Tensor,  # (batch, seqlen)
        span: torch.Tensor,  # (batch, seqlen)
    ):
        batch = input.size(0)
        seqlen = input.size(1)

        hidden_states = self.input_embedding(input)
        segment_states = self.segment_embedding(segment)
        hidden_states = hidden_states + segment_states

        with torch.no_grad():
            device = input.device
            directional_mask_2d = torch.arange(
                seqlen, device=device
            ) <= torch.arange(seqlen, device=device).view(-1, 1)
            attention_mask = context[:, None, :] | (
                context[:, :, None].logical_not()
                & directional_mask_2d.view(1, seqlen, seqlen)
            )
            attention_mask = attention_mask & (
                span[:, None, :] == span[:, :, None]
            )
            mask_1d = (
                torch.arange(seqlen, device=device)[None, :].repeat(batch, 1)
                < length[:, None]
            )
            attention_mask = (
                mask_1d.view(batch, seqlen, 1)
                & mask_1d.view(batch, 1, seqlen)
                & attention_mask
            )

        position_bias = self.position_bias(position, position, segment, segment)
        hidden_states = self.encoder(
            hidden_states, attention_mask, position_bias
        )

        logits = self.input_embedding.projection(hidden_states)
        return logits, hidden_states

    def inference(
        self,
        input: torch.Tensor,  # (batch, seqlen)
        length: torch.Tensor,  # (batch)
        context: torch.Tensor,  # (batch, seqlen)
        position: torch.Tensor,  # (batch, seqlen)
        segment: torch.Tensor,  # (batch, seqlen)
        span: torch.Tensor,  # (batch, seqlen)
        past_key_values=None,  # num_layers * 2 * (batch, num_heads, seqlen, dim_head)
    ):
        batch = input.size(0)

        if past_key_values is None:
            past_length = 0
            past_key_values = tuple([None] * self.encoder.num_layers)

            hidden_states = self.input_embedding(input)
            segment_states = self.segment_embedding(segment)
            hidden_states = hidden_states + segment_states

        else:
            past_length = past_key_values[0][0].size(-2)
            segment_states = self.segment_embedding(segment)
            hidden_states = (
                self.input_embedding(input) + segment_states[:, -1:, :]
            )

        seqlen = past_length + input.size(1)

        with torch.no_grad():
            device = input.device
            directional_mask_2d = torch.arange(
                seqlen, device=device
            ) <= torch.arange(seqlen, device=device).view(-1, 1)
            attention_mask = context[:, None, :] | (
                context[:, :, None].logical_not()
                & directional_mask_2d.view(1, seqlen, seqlen)
            )
            attention_mask = attention_mask & (
                span[:, None, :] == span[:, :, None]
            )
            # mask for left paddding
            mask_1d = (
                torch.tensor(list(range(seqlen))[::-1], device=device)[
                    None, :
                ].repeat(batch, 1)
                < length[:, None]
            )
            attention_mask = (
                mask_1d.view(batch, seqlen, 1)
                & mask_1d.view(batch, 1, seqlen)
                & attention_mask
            )

        position_bias = self.position_bias(position, position, segment, segment)

        attention_mask = attention_mask[:, past_length:, :]
        position_bias = position_bias[:, :, past_length:, :]

        hidden_states, present_key_values = self.encoder(
            hidden_states, attention_mask, position_bias, True, past_key_values
        )
        logits = self.input_embedding.projection(hidden_states)
        return logits, hidden_states, present_key_values
