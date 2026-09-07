"""向量嵌入生成工具。

本模块提供用于演示的确定性伪向量嵌入。
请将 `generate_embedding` 函数替换为真实的向量嵌入模型
（例如 OpenAI text-embedding-3-small、Ollama 或本地的 Sentence-Transformers 模型）。
"""

import hashlib

import numpy as np

EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small 的维度


def generate_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """根据文本生成确定性的伪向量嵌入。

    使用 SHA-256 哈希作为随机数生成器的种子，为相同输入生成稳定的
    向量。这并不是一个有意义的向量嵌入——在生产环境中请替换为
    真实的模型。

    >>> v = generate_embedding("hello world")
    >>> len(v)
    1536
    >>> v2 = generate_embedding("hello world")
    >>> v == v2
    True
    """
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    # 归一化为单位长度（用于余弦距离）
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()
