LABS = [
    dict(
        id="lab-attention",
        course="llm",
        title="用 NumPy 手写带 causal mask 的缩放点积注意力",
        level="medium",
        desc='''### 背景
缩放点积注意力是 Transformer、Agent 记忆压缩、检索增强重排和多模态编码器里最常见的基础算子。面试官让你手写它，通常不是为了考矩阵乘法语法，而是想确认你真的理解三件事：为什么要除以 `sqrt(d)`，如何做数值稳定的 softmax，以及自回归生成时 causal mask 和 padding mask 应该怎样共同生效。真实工程里，注意力实现最容易出错的地方是 mask 的广播方向、全被 mask 时出现 NaN、以及增量解码时单个 query 只能看见错误长度的 key。

### 要实现什么
请实现函数 `scaled_dot_product_attention(q, k, v, padding_mask=None)`。`q` 形状为 `(..., Tq, D)`，`k` 形状为 `(..., Tk, D)`，`v` 形状为 `(..., Tk, Dv)`，前面的批量维度必须可以被 NumPy matmul 广播。函数返回 `(output, weights)`，其中 `weights` 形状为 `(..., Tq, Tk)`，`output` 形状为 `(..., Tq, Dv)`。分数为 `q @ k^T / sqrt(D)`。必须使用 causal mask：第 `i` 个 query 的绝对位置按右对齐规则计算为 `Tk - Tq + i`，只能看见 `j <= Tk - Tq + i` 的 key；这样既支持整段训练，也支持 KV cache 场景下 `Tq=1, Tk>1` 的最后一个 token。`padding_mask` 可选，形状可以广播到 `(..., Tk)`，其中 True/1 表示该 key 有效，False/0 表示 padding。causal mask 与 padding mask 同时生效。

### 例子
若 `q=k=[[1,0],[0,1]]`，`v=[[10],[20]]`，第一个位置只能看第一个 value，第二个位置可以看前两个 value。若传入 `padding_mask=[True, False]`，第二个 key 对所有 query 都不可见。

### 约束
只能使用 `numpy`。softmax 必须先减去每行有效分数最大值，避免大 logits 溢出。某个 query 没有任何可见 key 时，该行注意力权重应全为 0，对应输出也应全为 0，不能返回 NaN。''',
        starter='''import numpy as np

def scaled_dot_product_attention(q, k, v, padding_mask=None):
    """返回带 causal mask 和可选 padding mask 的 (output, attention_weights)。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_output_shape_and_first_token_only_attends_to_itself():
    """验证输出形状正确，且 causal mask 让首 token 只能看自己。"""
    q = np.array([[1.0, 0.0], [0.0, 1.0]])
    k = q.copy()
    v = np.array([[10.0, 0.0], [0.0, 20.0]])
    out, weights = scaled_dot_product_attention(q, k, v)
    assert out.shape == (2, 2), f"output shape 错误: {out.shape}"
    assert weights.shape == (2, 2), f"weights shape 错误: {weights.shape}"
    assert np.allclose(weights[0], [1.0, 0.0]), f"首行不应看到未来 token: {weights[0]}"
    assert np.allclose(out[0], v[0]), f"首 token 输出应等于第一个 value: {out[0]}"

def test_padding_mask_blocks_key_for_all_queries():
    """验证 padding_mask 会把无效 key 从所有 query 的 softmax 中移除。"""
    q = np.eye(2, dtype=float)
    k = q.copy()
    v = np.array([[3.0], [100.0]])
    out, weights = scaled_dot_product_attention(q, k, v, padding_mask=np.array([True, False]))
    assert np.allclose(weights[:, 1], 0.0), f"padding key 权重应为 0: {weights}"
    assert np.allclose(out, [[3.0], [3.0]]), f"所有位置都只能聚合第一个 value: {out}"

def test_softmax_is_numerically_stable():
    """验证很大的分数不会让 softmax 溢出或产生 NaN。"""
    q = np.array([[1000.0, 0.0], [1000.0, 0.0]])
    k = np.array([[1000.0, 0.0], [999.0, 0.0]])
    v = np.array([[1.0], [2.0]])
    out, weights = scaled_dot_product_attention(q, k, v)
    assert np.isfinite(weights).all(), f"权重中出现非有限值: {weights}"
    assert np.isfinite(out).all(), f"输出中出现非有限值: {out}"
    assert np.allclose(weights.sum(axis=-1), [1.0, 1.0]), f"每行权重应归一化: {weights}"

def test_right_aligned_causal_mask_supports_single_query_cache_case():
    """验证 Tq=1、Tk>1 时单个 query 可以看见已有前缀的所有 key。"""
    q = np.array([[0.0, 1.0]])
    k = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 2.0]])
    v = np.array([[1.0], [10.0], [100.0]])
    out, weights = scaled_dot_product_attention(q, k, v)
    assert weights.shape == (1, 3)
    assert weights[0, 0] > 0 and weights[0, 1] > 0 and weights[0, 2] > 0, f"单步解码应能看见全部历史 key: {weights}"
    assert out[0, 0] > 10.0, f"应聚合到最后一个高相关 value: {out}"
''',
        hidden='''import numpy as np

def test_all_masked_query_returns_zero_not_nan():
    """验证某行所有 key 都被 mask 时返回全 0 而不是 NaN。"""
    q = np.array([[1.0, 0.0], [0.0, 1.0]])
    k = q.copy()
    v = np.array([[5.0, 6.0], [7.0, 8.0]])
    out, weights = scaled_dot_product_attention(q, k, v, padding_mask=np.array([False, False]))
    assert np.allclose(weights, 0.0), f"全 mask 权重应为 0: {weights}"
    assert np.allclose(out, 0.0), f"全 mask 输出应为 0: {out}"

def test_batch_padding_mask_broadcasts_over_query_axis():
    """验证批量维度下 padding_mask 能正确广播到 query 维度。"""
    q = np.stack([np.eye(2), np.eye(2)]).astype(float)
    k = q.copy()
    v = np.array([[[1.0], [2.0]], [[10.0], [20.0]]])
    mask = np.array([[True, False], [False, True]])
    out, weights = scaled_dot_product_attention(q, k, v, padding_mask=mask)
    assert np.allclose(weights[0, :, 1], 0.0), f"第一批第二个 key 应被屏蔽: {weights[0]}"
    assert np.allclose(out[0], [[1.0], [1.0]]), f"第一批输出错误: {out[0]}"
    assert np.allclose(weights[1, 0], [0.0, 0.0]), f"第二批首 query 没有可见 key: {weights[1,0]}"
    assert np.allclose(out[1, 0], [0.0]), f"第二批首 query 输出应为 0: {out[1,0]}"

def test_future_tokens_have_zero_attention():
    """验证完整序列计算时每一行未来 token 权重都为 0。"""
    q = np.ones((4, 3))
    k = np.ones((4, 3))
    v = np.arange(8, dtype=float).reshape(4, 2)
    _, weights = scaled_dot_product_attention(q, k, v)
    assert np.allclose(np.triu(weights, 1), 0.0), f"未来位置权重必须为 0: {weights}"
''',
        solution='''import numpy as np

def scaled_dot_product_attention(q, k, v, padding_mask=None):
    """返回带 causal mask 和可选 padding mask 的 (output, attention_weights)。"""
    q = np.asarray(q, dtype=float)
    k = np.asarray(k, dtype=float)
    v = np.asarray(v, dtype=float)
    if q.shape[-1] != k.shape[-1]:
        raise ValueError("q 和 k 的最后一维必须相同")
    if k.shape[-2] != v.shape[-2]:
        raise ValueError("k 和 v 的序列长度必须相同")

    tq, tk = q.shape[-2], k.shape[-2]
    scores = np.matmul(q, np.swapaxes(k, -1, -2)) / np.sqrt(q.shape[-1])

    query_pos = np.arange(tk - tq, tk)[:, None]
    key_pos = np.arange(tk)[None, :]
    mask = key_pos <= query_pos
    while mask.ndim < scores.ndim:
        mask = np.expand_dims(mask, axis=0)
    mask = np.broadcast_to(mask, scores.shape).copy()

    if padding_mask is not None:
        pm = np.asarray(padding_mask).astype(bool)
        pm = np.expand_dims(pm, axis=-2)
        mask = mask & np.broadcast_to(pm, scores.shape)

    masked_scores = np.where(mask, scores, -np.inf)
    row_max = np.max(masked_scores, axis=-1, keepdims=True)
    has_any = np.isfinite(row_max)
    shifted = np.where(mask, scores - np.where(has_any, row_max, 0.0), -np.inf)
    exp_scores = np.where(mask, np.exp(shifted), 0.0)
    denom = exp_scores.sum(axis=-1, keepdims=True)
    weights = np.divide(exp_scores, denom, out=np.zeros_like(exp_scores), where=denom > 0)
    output = np.matmul(weights, v)
    return output, weights
''',
        hints=[
            "先写出 `scores = q @ k.T / sqrt(D)`，再单独构造 causal mask 和 padding mask。",
            "softmax 只应在可见位置上做：不可见位置可以临时设为 `-np.inf`，再减每行最大值。",
            "`Tq=1, Tk>1` 时 query 对应最后一个位置；全 mask 行要显式把分母为 0 的结果置 0。",
        ],
        points=["缩放点积注意力公式", "causal mask 与 padding mask 广播", "数值稳定 softmax", "全 mask 边界处理"],
        numpy=True,
    ),
    dict(
        id="lab-mha-kvcache",
        course="llm",
        title="用 NumPy 手写多头注意力和 KV Cache 增量解码",
        level="hard",
        desc='''### 背景
大模型推理慢，最核心的原因之一是每生成一个 token 都要做注意力计算。KV Cache 的价值在于：历史 token 的 key/value 只算一次，后续增量解码只计算当前 token 的 query/key/value，再和缓存里的历史 key/value 做注意力。面试中这道题经常用来区分“会调框架接口”和“理解推理引擎”的候选人，因为它同时考察张量 reshape、多头拆分、causal attention、输出投影以及缓存状态管理。

### 要实现什么
请实现两个函数：`multi_head_attention(x, Wq, Wk, Wv, Wo, num_heads)` 和 `mha_decode_step(x_t, Wq, Wk, Wv, Wo, num_heads, cache=None)`。本题不考虑 batch，`x` 形状为 `(T, D)`，四个权重矩阵形状均为 `(D, D)`。线性层约定为行向量右乘转置：`q = x @ Wq.T`。`num_heads` 必须整除 `D`，每个 head 的维度为 `D / num_heads`。全量函数返回形状 `(T, D)`，使用标准自回归 causal mask。

`mha_decode_step` 接收单个 token `x_t`，形状可以是 `(D,)` 或 `(1, D)`，返回 `(y_t, new_cache)`。`new_cache` 是字典，包含 `"k"` 和 `"v"`，形状均为 `(t, num_heads, head_dim)`。如果传入已有 cache，函数需要追加当前 token 的 k/v，并用当前 q 对缓存中全部 k/v 做注意力，返回当前 token 的输出 `y_t`，形状为 `(D,)`。不要原地修改传入的 cache。

### 例子
用同一组 `x` 和权重先调用一次 `multi_head_attention` 得到全量输出，再从空 cache 开始逐个 token 调用 `mha_decode_step`，把每步的 `y_t` 拼起来，结果应与全量输出逐元素一致。

### 约束
只能使用 `numpy`。softmax 要数值稳定。测试规模很小，但实现应按向量化思路写清楚。维度不合法时应抛出 `ValueError`，而不是静默 reshape 出错误结果。''',
        starter='''import numpy as np

def multi_head_attention(x, Wq, Wk, Wv, Wo, num_heads):
    """返回不带 batch 的 causal multi-head attention 输出，形状为 (T, D)。"""
    raise NotImplementedError

def mha_decode_step(x_t, Wq, Wk, Wv, Wo, num_heads, cache=None):
    """用 KV Cache 解码单个 token，返回 (y_t, new_cache)。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_full_attention_shape_and_causal_first_token():
    """验证全量多头注意力形状正确，首 token 只依赖自己。"""
    x = np.array([[1.0, 0.0], [0.0, 2.0]])
    I = np.eye(2)
    out = multi_head_attention(x, I, I, I, I, num_heads=1)
    assert out.shape == x.shape, f"输出形状错误: {out.shape}"
    assert np.allclose(out[0], x[0]), f"首 token 不能聚合未来 token: {out[0]}"

def test_incremental_decode_matches_full_attention():
    """验证逐 token KV Cache 解码与一次性全量计算完全一致。"""
    x = np.array([[0.2, -0.1, 0.3, 0.5], [0.0, 0.4, -0.2, 0.1], [0.7, -0.3, 0.2, -0.4]])
    Wq = np.array([[1.0, 0.1, 0.0, 0.0], [0.0, 0.9, 0.2, 0.0], [0.0, 0.0, 1.1, 0.1], [0.2, 0.0, 0.0, 0.8]])
    Wk = np.array([[0.8, 0.0, 0.1, 0.0], [0.1, 1.0, 0.0, 0.0], [0.0, 0.2, 0.9, 0.0], [0.0, 0.0, 0.1, 1.0]])
    Wv = np.array([[1.0, 0.0, 0.0, 0.2], [0.0, 0.7, 0.1, 0.0], [0.2, 0.0, 1.0, 0.0], [0.0, 0.1, 0.0, 0.9]])
    Wo = np.array([[0.9, 0.0, 0.1, 0.0], [0.0, 1.0, 0.0, 0.1], [0.0, 0.2, 0.8, 0.0], [0.1, 0.0, 0.0, 1.0]])
    full = multi_head_attention(x, Wq, Wk, Wv, Wo, num_heads=2)
    cache = None
    pieces = []
    for row in x:
        y, cache = mha_decode_step(row, Wq, Wk, Wv, Wo, num_heads=2, cache=cache)
        pieces.append(y)
    inc = np.vstack(pieces)
    assert np.allclose(inc, full, atol=1e-10), f"增量解码应等于全量计算\\ninc={inc}\\nfull={full}"

def test_cache_grows_with_expected_shape():
    """验证 cache 每步增长，且布局是 (time, heads, head_dim)。"""
    x = np.eye(4)
    I = np.eye(4)
    cache = None
    for i in range(3):
        _, cache = mha_decode_step(x[i], I, I, I, I, num_heads=2, cache=cache)
        assert cache["k"].shape == (i + 1, 2, 2), f"k cache shape 错误: {cache['k'].shape}"
        assert cache["v"].shape == (i + 1, 2, 2), f"v cache shape 错误: {cache['v'].shape}"

def test_step_accepts_single_row_matrix():
    """验证单步输入既可以是 (D,) 也可以是 (1, D)。"""
    I = np.eye(2)
    y_vec, _ = mha_decode_step(np.array([1.0, 2.0]), I, I, I, I, 1)
    y_mat, _ = mha_decode_step(np.array([[1.0, 2.0]]), I, I, I, I, 1)
    assert np.allclose(y_vec, y_mat), f"两种 x_t 输入形式应等价: {y_vec} vs {y_mat}"
''',
        hidden='''import numpy as np

def test_decode_step_does_not_mutate_input_cache():
    """验证增量解码不会原地修改调用方传入的 cache。"""
    I = np.eye(2)
    _, cache1 = mha_decode_step(np.array([1.0, 0.0]), I, I, I, I, 1)
    old_k = cache1["k"].copy()
    old_v = cache1["v"].copy()
    _, cache2 = mha_decode_step(np.array([0.0, 1.0]), I, I, I, I, 1, cache1)
    assert np.allclose(cache1["k"], old_k), "传入的 k cache 不应被原地改写"
    assert np.allclose(cache1["v"], old_v), "传入的 v cache 不应被原地改写"
    assert cache2["k"].shape[0] == 2, f"新 cache 应追加到长度 2: {cache2['k'].shape}"

def test_invalid_num_heads_raises_value_error():
    """验证 D 不能被 num_heads 整除时抛出 ValueError。"""
    x = np.ones((2, 3))
    W = np.eye(3)
    try:
        multi_head_attention(x, W, W, W, W, num_heads=2)
    except ValueError:
        return
    assert False, "num_heads 不整除 D 时必须抛出 ValueError"

def test_two_heads_keep_information_separate_before_output_projection():
    """验证多头拆分不会把不同 head 的维度错误混在一起。"""
    x = np.array([[1.0, 0.0, 10.0, 0.0], [0.0, 1.0, 0.0, 20.0]])
    I = np.eye(4)
    out = multi_head_attention(x, I, I, I, I, num_heads=2)
    assert np.allclose(out[0], x[0]), f"首 token 输出错误: {out[0]}"
    assert out[1, 1] > out[1, 0], f"第二个 head 前半部分聚合异常: {out[1]}"
    assert out[1, 3] > out[1, 2], f"第二个 head 后半部分聚合异常: {out[1]}"
''',
        solution='''import numpy as np

def _check_shapes(x, Wq, Wk, Wv, Wo, num_heads):
    x = np.asarray(x, dtype=float)
    D = x.shape[-1]
    if D % num_heads != 0:
        raise ValueError("D 必须能被 num_heads 整除")
    for W in (Wq, Wk, Wv, Wo):
        if np.asarray(W).shape != (D, D):
            raise ValueError("权重矩阵形状必须都是 (D, D)")
    return x, D, D // num_heads

def _split_heads(z, num_heads):
    T, D = z.shape
    return z.reshape(T, num_heads, D // num_heads).transpose(1, 0, 2)

def _softmax(scores):
    scores = scores - np.max(scores, axis=-1, keepdims=True)
    exp_scores = np.exp(scores)
    return exp_scores / exp_scores.sum(axis=-1, keepdims=True)

def multi_head_attention(x, Wq, Wk, Wv, Wo, num_heads):
    """返回不带 batch 的 causal multi-head attention 输出，形状为 (T, D)。"""
    x, D, head_dim = _check_shapes(x, Wq, Wk, Wv, Wo, num_heads)
    Wq, Wk, Wv, Wo = map(lambda a: np.asarray(a, dtype=float), (Wq, Wk, Wv, Wo))
    q = _split_heads(x @ Wq.T, num_heads)
    k = _split_heads(x @ Wk.T, num_heads)
    v = _split_heads(x @ Wv.T, num_heads)
    scores = np.matmul(q, np.swapaxes(k, -1, -2)) / np.sqrt(head_dim)
    T = x.shape[0]
    causal = np.tril(np.ones((T, T), dtype=bool))[None, :, :]
    scores = np.where(causal, scores, -np.inf)
    weights = _softmax(scores)
    context = np.matmul(weights, v).transpose(1, 0, 2).reshape(T, D)
    return context @ Wo.T

def mha_decode_step(x_t, Wq, Wk, Wv, Wo, num_heads, cache=None):
    """用 KV Cache 解码单个 token，返回 (y_t, new_cache)。"""
    x_t = np.asarray(x_t, dtype=float)
    if x_t.ndim == 1:
        x = x_t[None, :]
    elif x_t.ndim == 2 and x_t.shape[0] == 1:
        x = x_t
    else:
        raise ValueError("x_t 形状必须是 (D,) 或 (1, D)")
    x, D, head_dim = _check_shapes(x, Wq, Wk, Wv, Wo, num_heads)
    Wq, Wk, Wv, Wo = map(lambda a: np.asarray(a, dtype=float), (Wq, Wk, Wv, Wo))
    q = (x @ Wq.T).reshape(num_heads, head_dim)
    k_new = (x @ Wk.T).reshape(1, num_heads, head_dim)
    v_new = (x @ Wv.T).reshape(1, num_heads, head_dim)
    if cache is None:
        k_all, v_all = k_new, v_new
    else:
        k_all = np.concatenate([np.asarray(cache["k"], dtype=float), k_new], axis=0)
        v_all = np.concatenate([np.asarray(cache["v"], dtype=float), v_new], axis=0)
    kh = k_all.transpose(1, 0, 2)
    vh = v_all.transpose(1, 0, 2)
    scores = np.einsum("hd,htd->ht", q, kh) / np.sqrt(head_dim)
    weights = _softmax(scores)
    context = np.einsum("ht,htd->hd", weights, vh).reshape(D)
    y = context @ Wo.T
    return y, {"k": k_all.copy(), "v": v_all.copy()}
''',
        hints=[
            "把 `(T, D)` 先投影成 q/k/v，再 reshape 成 `(heads, T, head_dim)` 会更直观。",
            "全量计算需要下三角 causal mask；单步解码不需要未来 mask，因为 cache 中只有历史和当前 token。",
            "cache 最好用 concatenate 生成新数组，避免调用方复用旧 cache 时被你原地改坏。",
        ],
        points=["多头拆分与合并", "causal attention", "KV Cache 状态布局", "全量与增量一致性"],
        numpy=True,
    ),
    dict(
        id="lab-rmsnorm-rope",
        course="llm",
        title="用 NumPy 实现 RMSNorm 与 RoPE 旋转位置编码",
        level="medium",
        desc='''### 背景
现代大模型常用 RMSNorm 替代 LayerNorm，并用 RoPE（旋转位置编码）把位置信息注入 query/key。RMSNorm 只按均方根缩放，不减均值，计算更简单；RoPE 则把偶数维和奇数维组成二维平面，按位置相关角度旋转。面试官让你手写这两个模块，通常想看你是否理解“归一化沿最后一维做”“权重如何广播”“RoPE 为什么能让注意力分数表达相对位置”。这些细节直接影响推理对齐、长上下文扩展和模型移植。

### 要实现什么
请实现 `rms_norm(x, weight, eps=1e-6)` 和 `rope_rotate(x, positions, base=10000.0)`。`rms_norm` 对 `x` 的最后一维计算 `sqrt(mean(x^2) + eps)`，返回 `x / rms * weight`，其中 `weight` 形状为最后一维大小，可广播到 `x`。不要减均值。

`rope_rotate` 接收最后一维为偶数的张量 `x`，把维度 `(0,1)、(2,3) ...` 两两配对。第 `m` 对的频率为 `1 / base ** (2m / dim)`，角度为 `positions * frequency`。`positions` 可以是标量，也可以广播到 `x` 去掉最后一维后的形状；例如 `x` 为 `(batch, seq, dim)` 时，`positions` 可以是 `(seq,)` 或 `(batch, seq)`。返回旋转后的数组，形状不变。若最后一维是奇数，应抛出 `ValueError`。

### 例子
`rms_norm([[3,4]], weight=[1,1], eps=0)` 的分母是 `sqrt((9+16)/2)`。RoPE 对 `[1,0]` 在位置 0 旋转后不变，在位置 1 会变成 `[cos(1), sin(1)]`。

### 约束
只能使用 `numpy`。测试会验证 RoPE 保持每个二维平面的范数，并验证 `dot(rope(q, p1), rope(k, p2))` 在整体平移位置后不变，即只依赖相对位置差。''',
        starter='''import numpy as np

def rms_norm(x, weight, eps=1e-6):
    """沿最后一维做 RMSNorm，不减均值。"""
    raise NotImplementedError

def rope_rotate(x, positions, base=10000.0):
    """对最后一维两两配对应用 RoPE 旋转。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_rms_norm_matches_formula_without_mean_subtraction():
    """验证 RMSNorm 按均方根缩放，且不会减去均值。"""
    x = np.array([[3.0, 4.0]])
    weight = np.array([2.0, 0.5])
    got = rms_norm(x, weight, eps=0.0)
    denom = np.sqrt((9.0 + 16.0) / 2.0)
    expected = x / denom * weight
    assert np.allclose(got, expected), f"RMSNorm 公式错误: {got} vs {expected}"

def test_rope_position_zero_is_identity_for_first_pair():
    """验证位置为 0 时 RoPE 不改变向量。"""
    x = np.array([[1.0, 0.0, 0.0, 2.0]])
    got = rope_rotate(x, positions=np.array([0]))
    assert np.allclose(got, x), f"位置 0 旋转应为恒等变换: {got}"

def test_rope_preserves_pairwise_norms():
    """验证 RoPE 是旋转变换，会保持每个二维平面的范数。"""
    x = np.array([[3.0, 4.0, 5.0, 12.0], [1.0, 2.0, 2.0, 1.0]])
    y = rope_rotate(x, positions=np.array([5, 7]))
    before = np.sqrt((x.reshape(2, 2, 2) ** 2).sum(axis=-1))
    after = np.sqrt((y.reshape(2, 2, 2) ** 2).sum(axis=-1))
    assert np.allclose(after, before), f"旋转后二维范数应不变: {after} vs {before}"

def test_rope_dot_product_depends_only_on_relative_position():
    """验证 q/k 同时平移位置后点积不变，说明只依赖相对位置。"""
    q = np.array([0.3, -0.7, 1.2, 0.4])
    k = np.array([-0.5, 0.9, 0.8, -1.1])
    dot1 = float(rope_rotate(q, 2) @ rope_rotate(k, 9))
    dot2 = float(rope_rotate(q, 12) @ rope_rotate(k, 19))
    assert abs(dot1 - dot2) < 1e-10, f"相对位置相同的点积应一致: {dot1} vs {dot2}"
''',
        hidden='''import numpy as np

def test_rope_supports_batch_positions():
    """验证 positions 可以广播到 batch/seq 维度。"""
    x = np.ones((2, 3, 4))
    positions = np.array([[0, 1, 2], [3, 4, 5]])
    y = rope_rotate(x, positions)
    assert y.shape == x.shape, f"输出形状错误: {y.shape}"
    assert np.allclose(y[0, 0], x[0, 0]), f"位置 0 应保持不变: {y[0,0]}"
    assert not np.allclose(y[1, 2], x[1, 2]), "非零位置通常应发生旋转"

def test_rope_odd_dimension_raises_value_error():
    """验证最后一维为奇数时抛出 ValueError。"""
    try:
        rope_rotate(np.ones((2, 3)), positions=np.array([0, 1]))
    except ValueError:
        return
    assert False, "奇数维 RoPE 必须抛出 ValueError"

def test_rms_norm_zero_vector_is_finite():
    """验证全零向量在 eps 保护下不会产生 NaN。"""
    got = rms_norm(np.zeros((2, 4)), np.ones(4), eps=1e-6)
    assert np.isfinite(got).all(), f"输出应为有限值: {got}"
    assert np.allclose(got, 0.0), f"零向量归一化后仍应为 0: {got}"
''',
        solution='''import numpy as np

def rms_norm(x, weight, eps=1e-6):
    """沿最后一维做 RMSNorm，不减均值。"""
    x = np.asarray(x, dtype=float)
    weight = np.asarray(weight, dtype=float)
    rms = np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps)
    return x / rms * weight

def rope_rotate(x, positions, base=10000.0):
    """对最后一维两两配对应用 RoPE 旋转。"""
    x = np.asarray(x, dtype=float)
    dim = x.shape[-1]
    if dim % 2 != 0:
        raise ValueError("RoPE 要求最后一维为偶数")
    pairs = x.reshape(*x.shape[:-1], dim // 2, 2)
    freqs = 1.0 / (base ** (np.arange(0, dim, 2, dtype=float) / dim))
    pos = np.asarray(positions, dtype=float)
    angles = pos[..., None] * freqs
    cos = np.cos(angles)
    sin = np.sin(angles)
    while cos.ndim < pairs.ndim - 1:
        cos = np.expand_dims(cos, axis=0)
        sin = np.expand_dims(sin, axis=0)
    x0 = pairs[..., 0]
    x1 = pairs[..., 1]
    out0 = x0 * cos - x1 * sin
    out1 = x0 * sin + x1 * cos
    return np.stack([out0, out1], axis=-1).reshape(x.shape)
''',
        hints=[
            "RMSNorm 的统计量是 `mean(x*x)`，不是方差，也不需要减均值。",
            "RoPE 可以先把最后一维 reshape 成 `(..., dim//2, 2)`，再分别计算每对的 cos/sin。",
            "positions 的维度要能广播到 `x.shape[:-1]`；奇数维不能悄悄丢掉最后一维。",
        ],
        points=["RMSNorm 公式", "RoPE 偶奇维旋转", "位置广播", "相对位置点积性质"],
        numpy=True,
    ),
    dict(
        id="lab-lora",
        course="llm",
        title="用 NumPy 实现 LoRA 线性层与权重合并",
        level="medium",
        desc='''### 背景
LoRA 是大模型微调里最常见的参数高效训练方法之一。它冻结原始线性层权重 `W`，只训练低秩矩阵 `A` 和 `B`，把增量写成 `(alpha / r) * B @ A`。这样既能显著减少训练参数量，也能在推理前把增量合并回原权重，减少额外矩阵乘法。面试里手写 LoRA，重点不是记住名字，而是确认你理解矩阵形状、初始化约定、merge 前后数值一致性，以及“只训练低秩参数”到底省了多少参数。

### 要实现什么
请实现四个函数：`lora_init(in_features, out_features, r, rng, scale=0.01)`、`lora_linear(x, W, A, B, alpha=1.0)`、`merge_lora_weights(W, A, B, alpha=1.0)`、`lora_trainable_params(in_features, out_features, r)`。本题采用行向量输入约定：原始线性层输出为 `x @ W.T`，其中 `W` 形状为 `(out_features, in_features)`。LoRA 的 `A` 形状为 `(r, in_features)`，`B` 形状为 `(out_features, r)`，增量输出为 `(alpha / r) * (x @ A.T @ B.T)`。

`lora_init` 需要用传入的 `rng` 生成 `A`，分布为标准正态乘以 `scale`，并把 `B` 初始化为全 0；这保证刚接上 LoRA 时模型输出不变。`merge_lora_weights` 返回新权重 `W + (alpha / r) * (B @ A)`，不要修改原始 `W`。`lora_trainable_params` 返回只训练 `A/B` 时的参数个数 `r * in_features + out_features * r`。`r <= 0` 应抛出 `ValueError`。

### 例子
若 `x` 是 `(batch, in_features)`，`W` 是 `(out_features, in_features)`，则 `lora_linear` 返回 `(batch, out_features)`。把 `W_merged = merge_lora_weights(...)` 后，`x @ W_merged.T` 应与未合并的 `lora_linear` 完全一致。

### 约束
只能使用 `numpy`。测试会检查初始化后增量为 0、merge 前后一致、参数量计算正确，以及函数不会原地改写 `W`。''',
        starter='''import numpy as np

def lora_init(in_features, out_features, r, rng, scale=0.01):
    """初始化 LoRA 的 A/B，其中 A 为随机小值，B 为 0。"""
    raise NotImplementedError

def lora_linear(x, W, A, B, alpha=1.0):
    """计算 x @ W.T + (alpha/r) * x @ A.T @ B.T。"""
    raise NotImplementedError

def merge_lora_weights(W, A, B, alpha=1.0):
    """返回合并 LoRA 增量后的新权重。"""
    raise NotImplementedError

def lora_trainable_params(in_features, out_features, r):
    """返回只训练 LoRA A/B 时的参数量。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_lora_init_shapes_and_zero_delta():
    """验证初始化形状正确，且 B 为 0 时 LoRA 初始不改变输出。"""
    class FakeRng:
        def normal(self, size):
            return np.full(size, 0.5)
    rng = FakeRng()
    A, B = lora_init(3, 2, r=1, rng=rng)
    assert A.shape == (1, 3), f"A shape 错误: {A.shape}"
    assert B.shape == (2, 1), f"B shape 错误: {B.shape}"
    assert np.allclose(B, 0.0), f"B 应初始化为 0: {B}"
    x = np.array([[1.0, 2.0, 3.0]])
    W = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert np.allclose(lora_linear(x, W, A, B), x @ W.T), "B 为 0 时输出应等于原线性层"

def test_lora_linear_matches_manual_formula():
    """验证 LoRA 线性层符合手写矩阵公式。"""
    x = np.array([[1.0, 2.0], [3.0, 4.0]])
    W = np.array([[1.0, -1.0], [0.5, 2.0]])
    A = np.array([[1.0, 0.0], [0.0, 1.0]])
    B = np.array([[2.0, 0.0], [0.0, -1.0]])
    got = lora_linear(x, W, A, B, alpha=4.0)
    expected = x @ W.T + 2.0 * (x @ A.T @ B.T)
    assert np.allclose(got, expected), f"公式错误: {got} vs {expected}"

def test_merge_result_equals_unmerged_result():
    """验证合并后的 W 与未合并 LoRA 前向结果一致。"""
    x = np.array([[0.2, -0.3, 0.5]])
    W = np.array([[1.0, 0.1, 0.0], [0.0, -0.2, 0.3]])
    A = np.array([[0.5, -1.0, 0.2], [0.3, 0.0, -0.4]])
    B = np.array([[0.7, -0.1], [0.2, 0.9]])
    merged = merge_lora_weights(W, A, B, alpha=8.0)
    got = x @ merged.T
    expected = lora_linear(x, W, A, B, alpha=8.0)
    assert np.allclose(got, expected), f"merge 前后输出不一致: {got} vs {expected}"

def test_trainable_param_count():
    """验证只训练 A/B 时的参数量计算。"""
    assert lora_trainable_params(4096, 11008, 8) == 8 * 4096 + 11008 * 8
''',
        hidden='''import numpy as np

def test_merge_does_not_mutate_original_weight():
    """验证 merge_lora_weights 不会原地修改原始 W。"""
    W = np.ones((2, 3))
    A = np.ones((1, 3))
    B = np.ones((2, 1))
    before = W.copy()
    merged = merge_lora_weights(W, A, B, alpha=2.0)
    assert np.allclose(W, before), "原始 W 不应被修改"
    assert not np.shares_memory(merged, W), "merged 应是新数组"

def test_rank_must_be_positive():
    """验证 r <= 0 时抛出 ValueError。"""
    try:
        lora_trainable_params(3, 4, 0)
    except ValueError:
        return
    assert False, "r <= 0 必须抛出 ValueError"

def test_lora_linear_supports_vector_input():
    """验证单个向量输入也能得到一维输出。"""
    x = np.array([1.0, 2.0])
    W = np.eye(2)
    A = np.eye(2)
    B = np.eye(2)
    got = lora_linear(x, W, A, B, alpha=2.0)
    assert got.shape == (2,), f"向量输入应返回向量输出: {got.shape}"
    assert np.allclose(got, 2.0 * x), f"输出错误: {got}"
''',
        solution='''import numpy as np

def _check_rank(r):
    if r <= 0:
        raise ValueError("r 必须为正数")

def lora_init(in_features, out_features, r, rng, scale=0.01):
    """初始化 LoRA 的 A/B，其中 A 为随机小值，B 为 0。"""
    _check_rank(r)
    A = rng.normal(size=(r, in_features)) * scale
    B = np.zeros((out_features, r), dtype=float)
    return A, B

def lora_linear(x, W, A, B, alpha=1.0):
    """计算 x @ W.T + (alpha/r) * x @ A.T @ B.T。"""
    x = np.asarray(x, dtype=float)
    W = np.asarray(W, dtype=float)
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    r = A.shape[0]
    _check_rank(r)
    return x @ W.T + (alpha / r) * (x @ A.T @ B.T)

def merge_lora_weights(W, A, B, alpha=1.0):
    """返回合并 LoRA 增量后的新权重。"""
    W = np.asarray(W, dtype=float)
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    r = A.shape[0]
    _check_rank(r)
    return W + (alpha / r) * (B @ A)

def lora_trainable_params(in_features, out_features, r):
    """返回只训练 LoRA A/B 时的参数量。"""
    _check_rank(r)
    return r * in_features + out_features * r
''',
        hints=[
            "先固定形状：`W=(out,in)`、`A=(r,in)`、`B=(out,r)`，输入按行向量处理。",
            "未合并输出可以写成 `x @ W.T + (alpha/r) * (x @ A.T @ B.T)`。",
            "合并到权重时增量在权重空间是 `(alpha/r) * (B @ A)`，不要写反成 `A @ B`。",
        ],
        points=["LoRA 矩阵形状", "初始化零增量", "merge 前后一致性", "参数量计算"],
        numpy=True,
    ),
    dict(
        id="lab-sampling",
        course="llm",
        title="用 NumPy 实现 temperature、top-k、top-p 采样",
        level="medium",
        desc='''### 背景
大模型应用里，采样策略直接影响回答的稳定性、创造性和安全边界。面试官让你手写 `sample`，通常会重点追问 temperature 为 0 时是不是 greedy、top-k 与 top-p 同时出现时如何组合、`-inf` logits 是否会被采到、以及概率归一化是否数值稳定。真实工程中这些边界处理不好，会出现线上偶发 NaN、空候选集合、或者明明屏蔽了某个 token 却仍然被采样出来的问题。

### 要实现什么
请实现 `sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None)`，返回被采样 token 的整数下标。`logits` 是一维数组，可以包含 `-np.inf` 表示禁止采样。`temperature=0` 时退化为 greedy，返回最大 logit 的最小下标，不再使用随机数。`temperature>0` 时先把有限 logits 除以 temperature，再依次应用 top-k 和 top-p 过滤：top-k 只保留 logit 最大的 k 个有限 token；top-p 在当前候选 softmax 概率上按概率从大到小排序，保留累计概率达到或刚超过 `top_p` 的最小集合，并且至少保留一个 token。top-k 与 top-p 可以同时生效，后者在前者过滤后的候选上计算。

`rng` 是可注入随机数对象，默认可用 `np.random.default_rng()`。实现应调用类似 `rng.choice(n, p=probs)` 的接口进行采样。若没有任何有限 logit，应抛出 `ValueError`。`top_k=None` 表示不过滤；`top_p=None` 表示不过滤。所有概率计算都必须减最大值做稳定 softmax。

### 例子
`sample([1, 5, 5], temperature=0)` 返回 1，因为并列最大时取最小下标。若 logits 为 `[10, 9, 1]` 且 `top_k=2`，下标 2 不允许被采样。若再设置很小的 `top_p`，只会保留概率最高的 token。

### 约束
只能使用 `numpy`。测试会用固定 rng 或 fake rng 保证确定性。不要联网、不要调用时间函数，也不要在函数内部创建不可控随机状态来覆盖传入的 `rng`。''',
        starter='''import numpy as np

def sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None):
    """按 temperature/top-k/top-p 从一维 logits 中采样并返回 token 下标。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

class LastAllowedRng:
    def __init__(self):
        self.last_p = None
    def choice(self, n, p):
        self.last_p = np.asarray(p)
        allowed = np.flatnonzero(self.last_p > 0)
        return int(allowed[-1])

def test_temperature_zero_is_greedy_with_smallest_tie_index():
    """验证 temperature=0 时走 greedy，并在并列最大时返回最小下标。"""
    got = sample(np.array([1.0, 5.0, 5.0, -np.inf]), temperature=0.0, rng=LastAllowedRng())
    assert got == 1, f"greedy 并列时应返回最小最大下标 1，实际 {got}"

def test_top_k_filters_low_rank_tokens():
    """验证 top_k 会把排名之外的 token 概率置为 0。"""
    rng = LastAllowedRng()
    got = sample(np.array([10.0, 9.0, 1.0]), temperature=1.0, top_k=2, rng=rng)
    assert got in (0, 1), f"top_k=2 不应采到下标 2: {got}"
    assert rng.last_p[2] == 0.0, f"下标 2 概率应为 0: {rng.last_p}"

def test_top_p_keeps_minimal_prefix_after_softmax():
    """验证 top_p 只保留按概率排序后的最小前缀集合。"""
    rng = LastAllowedRng()
    got = sample(np.array([5.0, 4.0, 0.0]), top_p=0.7, rng=rng)
    assert got == 0, f"top_p=0.7 时最高概率 token 已超过阈值，应只保留下标 0: {got}"
    assert np.allclose(rng.last_p, [1.0, 0.0, 0.0]), f"过滤后概率错误: {rng.last_p}"

def test_negative_infinity_is_never_sampled():
    """验证 -inf token 不会被采样，且概率为 0。"""
    rng = LastAllowedRng()
    got = sample(np.array([-np.inf, 0.0, -np.inf, 0.0]), rng=rng)
    assert got in (1, 3), f"只能采样有限 logits: {got}"
    assert rng.last_p[0] == 0 and rng.last_p[2] == 0, f"-inf 概率应为 0: {rng.last_p}"
''',
        hidden='''import numpy as np

def test_top_k_and_top_p_can_apply_together():
    """验证 top_k 过滤后再在剩余候选上应用 top_p。"""
    class FirstAllowedRng:
        def __init__(self):
            self.p = None
        def choice(self, n, p):
            self.p = np.asarray(p)
            return int(np.flatnonzero(self.p > 0)[0])
    rng = FirstAllowedRng()
    got = sample(np.array([4.0, 3.9, 3.8, 0.0]), top_k=3, top_p=0.65, rng=rng)
    assert got in (0, 1), f"top_p 应在 top3 内保留前两个左右的候选: {got}"
    assert rng.p[2] == 0 and rng.p[3] == 0, f"过滤结果错误: {rng.p}"

def test_all_equal_logits_are_sampled_from_uniform_distribution():
    """验证全相等 logits 会得到均匀概率。"""
    class CaptureRng:
        def __init__(self):
            self.p = None
        def choice(self, n, p):
            self.p = np.asarray(p)
            return 2
    rng = CaptureRng()
    got = sample(np.array([1.0, 1.0, 1.0, 1.0]), rng=rng)
    assert got == 2
    assert np.allclose(rng.p, np.full(4, 0.25)), f"全相等 logits 应均匀: {rng.p}"

def test_no_finite_logits_raises_value_error():
    """验证没有任何有限 logit 时抛出 ValueError。"""
    try:
        sample(np.array([-np.inf, -np.inf]))
    except ValueError:
        return
    assert False, "全 -inf logits 必须抛出 ValueError"
''',
        solution='''import numpy as np

def _stable_probs(masked_logits):
    finite = np.isfinite(masked_logits)
    if not finite.any():
        raise ValueError("没有可采样的有限 logit")
    shifted = masked_logits[finite] - np.max(masked_logits[finite])
    probs = np.zeros_like(masked_logits, dtype=float)
    exp_values = np.exp(shifted)
    probs[finite] = exp_values / exp_values.sum()
    return probs

def sample(logits, temperature=1.0, top_k=None, top_p=None, rng=None):
    """按 temperature/top-k/top-p 从一维 logits 中采样并返回 token 下标。"""
    logits = np.asarray(logits, dtype=float)
    if logits.ndim != 1:
        raise ValueError("logits 必须是一维数组")
    finite = np.isfinite(logits)
    if not finite.any():
        raise ValueError("没有可采样的有限 logit")
    if temperature == 0:
        max_value = np.max(logits[finite])
        return int(np.flatnonzero(logits == max_value)[0])
    if temperature < 0:
        raise ValueError("temperature 不能为负数")
    filtered = np.where(finite, logits / temperature, -np.inf)

    if top_k is not None:
        k = int(top_k)
        if k <= 0:
            raise ValueError("top_k 必须为正数")
        finite_idx = np.flatnonzero(np.isfinite(filtered))
        if len(finite_idx) > k:
            order = finite_idx[np.argsort(filtered[finite_idx])[::-1]]
            keep = order[:k]
            new_filtered = np.full_like(filtered, -np.inf)
            new_filtered[keep] = filtered[keep]
            filtered = new_filtered

    if top_p is not None:
        p = float(top_p)
        if not (0 < p <= 1):
            raise ValueError("top_p 必须在 (0, 1] 内")
        probs = _stable_probs(filtered)
        order = np.argsort(probs)[::-1]
        keep = []
        cumulative = 0.0
        for idx in order:
            if probs[idx] <= 0:
                continue
            keep.append(idx)
            cumulative += probs[idx]
            if cumulative >= p:
                break
        new_filtered = np.full_like(filtered, -np.inf)
        new_filtered[keep] = filtered[keep]
        filtered = new_filtered

    probs = _stable_probs(filtered)
    if rng is None:
        rng = np.random.default_rng()
    return int(rng.choice(len(probs), p=probs))
''',
        hints=[
            "先把不可采样 token 统一设为 `-np.inf`，之后所有过滤都只在有限位置上做。",
            "top-k 先保留 logit 最大的 k 个，再基于这些候选的 softmax 概率做 top-p。",
            "temperature=0 不要做除法也不要采样；softmax 前一定减去有限候选的最大值。",
        ],
        points=["temperature 与 greedy", "top-k/top-p 组合过滤", "稳定 softmax", "-inf 和空候选边界"],
        numpy=True,
    ),
    dict(
        id="lab-dpo-grpo",
        course="llm",
        title="用 NumPy 实现 DPO Loss 与 GRPO 组内优势标准化",
        level="medium",
        desc='''### 背景
偏好优化是大模型对齐和 Agent 行为调优里的核心环节。DPO 用 chosen/rejected 两个回答的相对对数概率，直接优化策略模型相对参考模型的偏好间隔；GRPO 则常在一组候选回答内部根据奖励做标准化优势，降低不同题目、不同组之间奖励尺度不一致的影响。面试里这类题经常用来考察你是否能把论文公式落成稳定的数组代码，并正确处理 batch、广播和方差为 0 的边界。

### 要实现什么
请实现两个函数：`dpo_loss(policy_chosen_logps, policy_rejected_logps, ref_chosen_logps, ref_rejected_logps, beta=0.1)` 和 `grpo_advantages(rewards, group_ids, eps=1e-8)`。DPO 中先计算策略间隔 `policy_chosen_logps - policy_rejected_logps`，再减去参考模型间隔 `ref_chosen_logps - ref_rejected_logps`，得到 `margin`。每个样本 loss 为 `-log(sigmoid(beta * margin))`，要求用 `np.logaddexp(0, -z)` 实现稳定形式，返回逐样本 loss 数组，不要直接求平均。

`grpo_advantages` 接收一维 `rewards` 和同长度 `group_ids`。对每个 group 分别计算均值和标准差，返回 `(reward - group_mean) / group_std`。如果某个组内标准差小于 `eps`，该组所有 advantage 返回 0，避免除以 0。`group_ids` 可以是整数、字符串或其他可比较标识，输出顺序必须与输入样本顺序一致。

### 例子
如果策略模型比参考模型更偏好 chosen，则 DPO loss 会变小。若某组 rewards 为 `[1, 2, 3]`，组内优势为负、零、正且均值为 0；若某组 rewards 全相同，则该组优势全为 0。

### 约束
只能使用 `numpy`。函数应支持标量或数组形式的 log probability，并依赖 NumPy 广播得到结果。测试会覆盖 `beta=0`、极大 margin、字符串 group id、以及组内方差为 0 的情况。''',
        starter='''import numpy as np

def dpo_loss(policy_chosen_logps, policy_rejected_logps, ref_chosen_logps, ref_rejected_logps, beta=0.1):
    """返回逐样本 DPO loss: -log sigmoid(beta * margin)。"""
    raise NotImplementedError

def grpo_advantages(rewards, group_ids, eps=1e-8):
    """按 group_id 对 rewards 做组内标准化 advantage。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_dpo_loss_matches_stable_formula():
    """验证 DPO loss 与 logaddexp 稳定公式一致。"""
    pc = np.array([-1.0, -0.2])
    pr = np.array([-2.0, -0.5])
    rc = np.array([-1.5, -0.1])
    rr = np.array([-1.7, -0.4])
    beta = 0.3
    margin = (pc - pr) - (rc - rr)
    expected = np.logaddexp(0.0, -beta * margin)
    got = dpo_loss(pc, pr, rc, rr, beta=beta)
    assert np.allclose(got, expected), f"DPO loss 错误: {got} vs {expected}"

def test_better_policy_margin_has_lower_loss():
    """验证策略偏好 chosen 的间隔越大，DPO loss 越小。"""
    low = dpo_loss(-1.0, -1.1, -1.0, -1.1, beta=1.0)
    high = dpo_loss(-0.1, -3.0, -1.0, -1.1, beta=1.0)
    assert high < low, f"更大的偏好间隔应有更小 loss: high={high}, low={low}"

def test_grpo_advantages_are_groupwise_normalized():
    """验证 GRPO advantage 在每个组内均值为 0、标准差为 1。"""
    rewards = np.array([1.0, 2.0, 3.0, 10.0, 14.0])
    groups = np.array([0, 0, 0, 1, 1])
    adv = grpo_advantages(rewards, groups)
    assert abs(adv[:3].mean()) < 1e-12, f"第一组均值应为 0: {adv}"
    assert abs(adv[:3].std() - 1.0) < 1e-12, f"第一组 std 应为 1: {adv}"
    assert abs(adv[3:].mean()) < 1e-12, f"第二组均值应为 0: {adv}"
    assert abs(adv[3:].std() - 1.0) < 1e-12, f"第二组 std 应为 1: {adv}"

def test_zero_variance_group_returns_zero_advantages():
    """验证组内奖励完全相同的时候 advantage 全部为 0。"""
    adv = grpo_advantages(np.array([5.0, 5.0, 1.0]), np.array(["a", "a", "b"]))
    assert np.allclose(adv, [0.0, 0.0, 0.0]), f"零方差组应返回 0: {adv}"
''',
        hidden='''import numpy as np

def test_dpo_beta_zero_is_log_two():
    """验证 beta=0 时每个样本 loss 都是 log(2)。"""
    got = dpo_loss(np.array([10.0, -10.0]), np.array([-3.0, 4.0]), 0.0, 0.0, beta=0.0)
    assert np.allclose(got, np.log(2.0)), f"beta=0 应为 log(2): {got}"

def test_dpo_large_margin_is_finite():
    """验证极大正负 margin 下 DPO loss 不溢出。"""
    got = dpo_loss(np.array([1000.0, -1000.0]), np.array([-1000.0, 1000.0]), 0.0, 0.0, beta=1.0)
    assert np.isfinite(got).all(), f"loss 应为有限值: {got}"
    assert got[0] < 1e-6 and got[1] > 1000.0, f"极端 margin 结果异常: {got}"

def test_grpo_preserves_input_order_with_string_groups():
    """验证字符串 group id 下输出仍与输入顺序对齐。"""
    rewards = np.array([1.0, 10.0, 3.0, 14.0])
    groups = np.array(["x", "y", "x", "y"])
    adv = grpo_advantages(rewards, groups)
    assert np.allclose(adv, [-1.0, -1.0, 1.0, 1.0]), f"输出顺序或标准化错误: {adv}"
''',
        solution='''import numpy as np

def dpo_loss(policy_chosen_logps, policy_rejected_logps, ref_chosen_logps, ref_rejected_logps, beta=0.1):
    """返回逐样本 DPO loss: -log sigmoid(beta * margin)。"""
    pc = np.asarray(policy_chosen_logps, dtype=float)
    pr = np.asarray(policy_rejected_logps, dtype=float)
    rc = np.asarray(ref_chosen_logps, dtype=float)
    rr = np.asarray(ref_rejected_logps, dtype=float)
    margin = (pc - pr) - (rc - rr)
    return np.logaddexp(0.0, -beta * margin)

def grpo_advantages(rewards, group_ids, eps=1e-8):
    """按 group_id 对 rewards 做组内标准化 advantage。"""
    rewards = np.asarray(rewards, dtype=float)
    group_ids = np.asarray(group_ids)
    if rewards.shape[0] != group_ids.shape[0]:
        raise ValueError("rewards 和 group_ids 长度必须相同")
    out = np.zeros_like(rewards, dtype=float)
    for group in np.unique(group_ids):
        mask = group_ids == group
        values = rewards[mask]
        std = values.std()
        if std >= eps:
            out[mask] = (values - values.mean()) / std
    return out
''',
        hints=[
            "DPO 先算策略 chosen-rejected 间隔，再减参考模型的同类间隔。",
            "`-log(sigmoid(z))` 可以稳定写成 `np.logaddexp(0, -z)`。",
            "GRPO 标准化必须在每个 group 内单独做；单样本组或零方差组直接给 0。",
        ],
        points=["DPO 偏好间隔", "稳定 logistic loss", "组内 advantage 标准化", "零方差处理"],
        numpy=True,
    ),
    dict(
        id="lab-bpe",
        course="llm",
        title="纯 Python 实现简化 BPE 训练与编码",
        level="medium",
        desc='''### 背景
BPE（Byte Pair Encoding）是许多分词器的核心思想：从字符级表示开始，反复把语料中最常见的相邻符号对合并成新符号。虽然生产级 tokenizer 会处理字节、Unicode 归一化、特殊 token 和大规模词表，但面试中的手写 BPE 更关注你是否理解“从语料统计 pair”“按规则顺序编码新词”“合并时要左到右处理且不能重叠”。这道题能帮助准备大模型面试的工程师把 tokenizer 的黑盒拆开。

### 要实现什么
请实现 `train_bpe(corpus, num_merges)` 和 `encode_bpe(word, merges)`。`corpus` 是字符串列表，每个字符串表示一个单词。训练开始时，把每个单词表示成字符列表并在末尾追加特殊符号 `"</w>"`，例如 `"low" -> ["l", "o", "w", "</w>"]`。每轮统计所有 token 序列中的相邻符号对频次，选择频次最高的一对；若频次相同，按 Python 元组字典序选择最小的 pair。然后在所有序列中把该 pair 左到右、非重叠地合并成字符串拼接 `a + b`。重复 `num_merges` 轮；如果已经没有可合并 pair，则提前停止。`train_bpe` 返回按顺序学到的 pair 列表，每个 pair 是二元 tuple。

`encode_bpe(word, merges)` 对新单词执行同样的初始化，然后按 `merges` 的顺序逐条应用合并规则，返回最终符号列表，保留 `"</w>"` 或包含它的合并符号。编码阶段不要重新统计频次，也不要跳过前面的规则。

### 例子
若规则包含 `("l", "o")`，编码 `"low"` 会先把 `l` 和 `o` 合成 `"lo"`。若规则随后包含 `("lo", "w")`，会继续得到 `"low"`。对于 `"aaa"` 和规则 `("a", "a")`，左到右非重叠合并结果是 `["aa", "a", "</w>"]`。

### 约束
只能使用 Python 标准库，不要使用 numpy。实现应清晰、确定性强；测试会覆盖频次并列的字典序规则、合并规则顺序、重复 pair 非重叠合并，以及 `num_merges` 大于可合并轮数的情况。''',
        starter='''def train_bpe(corpus, num_merges):
    """从单词语料中训练简化 BPE 合并规则，返回 pair 列表。"""
    raise NotImplementedError

def encode_bpe(word, merges):
    """按给定 BPE 合并规则编码一个新单词，返回符号列表。"""
    raise NotImplementedError
''',
        tests='''def test_train_bpe_learns_most_frequent_pair():
    """验证训练会优先合并语料中频次最高的相邻符号对。"""
    merges = train_bpe(["low", "low", "lower"], 1)
    assert merges == [("l", "o")], f"最高频 pair 应是 ('l','o'): {merges}"

def test_encode_bpe_applies_rules_in_order():
    """验证编码新词时按训练得到的规则顺序依次合并。"""
    merges = [("l", "o"), ("lo", "w"), ("low", "</w>")]
    got = encode_bpe("low", merges)
    assert got == ["low</w>"], f"编码结果错误: {got}"

def test_tie_break_uses_lexicographic_order():
    """验证频次相同时按 pair 的字典序选择最小者。"""
    merges = train_bpe(["ab", "ac"], 1)
    assert merges == [("a", "b")], f"并列时应选择字典序最小 pair: {merges}"

def test_repeated_pair_merges_left_to_right_without_overlap():
    """验证同一规则在一个词内左到右非重叠合并。"""
    got = encode_bpe("aaa", [("a", "a")])
    assert got == ["aa", "a", "</w>"], f"重复 pair 合并应非重叠: {got}"
''',
        hidden='''def test_training_multiple_rounds_updates_corpus_after_each_merge():
    """验证每一轮合并后会基于新符号序列重新统计 pair。"""
    merges = train_bpe(["ababc", "ababc"], 3)
    assert merges[0] == ("a", "b"), f"第一轮应合并 ab: {merges}"
    assert ("ab", "ab") in merges, f"后续应能基于新符号继续合并: {merges}"

def test_num_merges_can_exceed_available_pairs():
    """验证请求很多轮合并时会在无 pair 后提前停止。"""
    merges = train_bpe([""], 5)
    assert merges == [], f"空词只有 </w>，没有可合并 pair: {merges}"

def test_encode_unknown_word_keeps_unmerged_characters():
    """验证编码阶段对规则覆盖不到的字符保持原样。"""
    got = encode_bpe("cat", [("c", "a")])
    assert got == ["ca", "t", "</w>"], f"未覆盖字符应保留: {got}"
''',
        solution='''def _merge_sequence(seq, pair):
    out = []
    i = 0
    while i < len(seq):
        if i + 1 < len(seq) and (seq[i], seq[i + 1]) == pair:
            out.append(seq[i] + seq[i + 1])
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out

def train_bpe(corpus, num_merges):
    """从单词语料中训练简化 BPE 合并规则，返回 pair 列表。"""
    tokens = [list(word) + ["</w>"] for word in corpus]
    merges = []
    for _ in range(num_merges):
        counts = {}
        for seq in tokens:
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i + 1])
                counts[pair] = counts.get(pair, 0) + 1
        if not counts:
            break
        best_freq = max(counts.values())
        best_pair = min(pair for pair, freq in counts.items() if freq == best_freq)
        merges.append(best_pair)
        tokens = [_merge_sequence(seq, best_pair) for seq in tokens]
    return merges

def encode_bpe(word, merges):
    """按给定 BPE 合并规则编码一个新单词，返回符号列表。"""
    seq = list(word) + ["</w>"]
    for pair in merges:
        seq = _merge_sequence(seq, tuple(pair))
    return seq
''',
        hints=[
            "把每个词先转成 `list(word) + ['</w>']`，训练过程维护的是这些符号序列。",
            "每一轮都重新统计相邻 pair；选择 pair 时先看频次，再用 `min(...)` 做字典序平局处理。",
            "合并一个序列时用 while 循环，命中 pair 后索引加 2，避免重叠合并。",
        ],
        points=["BPE pair 统计", "确定性平局处理", "非重叠合并", "训练规则与编码规则分离"],
        numpy=False,
    ),
    dict(
        id="lab-ce-ppl",
        course="llm",
        title="用 NumPy 实现交叉熵、困惑度与标签平滑",
        level="medium",
        desc='''### 背景
交叉熵和困惑度是训练、评估语言模型时最常见的指标。看似简单的 `cross_entropy`，在工程里却经常踩坑：logits 很大导致 `exp` 溢出，padding token 不该参与平均，所有标签都被忽略时要有定义，标签平滑的分布也容易写错。面试官让你手写这题，通常会观察你是否知道稳定 log-softmax、ignore_index 的分母应该只统计有效 token，以及 perplexity 只是交叉熵的指数变换。

### 要实现什么
请实现三个函数：`cross_entropy(logits, labels, ignore_index=-100)`、`perplexity(cross_entropy_value)`、`label_smoothing_cross_entropy(logits, labels, smoothing=0.0, ignore_index=-100)`。`logits` 形状为 `(..., C)`，`labels` 形状为 `(...)`，每个 label 是 `[0, C)` 内的类别下标，或等于 `ignore_index` 表示 padding/忽略。`cross_entropy` 需要先沿最后一维计算数值稳定的 log-softmax：`logits - max - log(sum(exp(logits-max)))`，再取有效标签的负 log probability，返回有效位置上的平均值。如果没有任何有效标签，返回 `0.0`。

`perplexity` 返回 `exp(cross_entropy_value)`。`label_smoothing_cross_entropy` 中，平滑系数 `smoothing` 在 `[0, 1]` 内；有效位置 loss 为 `(1-smoothing) * nll + smoothing * mean(-log_probs over all classes)`，最后同样只对有效标签求平均。`smoothing=0` 时应与普通交叉熵一致。

### 例子
若某个位置 logits 为 `[10, 0]` 且标签为 0，该位置 loss 接近 0。若标签为 `-100`，该位置不参与 loss 分子和分母。若平均交叉熵为 `ln(2)`，困惑度为 2。

### 约束
只能使用 `numpy`。测试会覆盖二维和三维 logits、极大 logits、ignore padding、全 padding、标签平滑以及 smoothing 为 0 的一致性。不要调用深度学习框架。''',
        starter='''import numpy as np

def cross_entropy(logits, labels, ignore_index=-100):
    """计算带 ignore_index 的平均交叉熵。"""
    raise NotImplementedError

def perplexity(cross_entropy_value):
    """由交叉熵计算困惑度。"""
    raise NotImplementedError

def label_smoothing_cross_entropy(logits, labels, smoothing=0.0, ignore_index=-100):
    """计算带 label smoothing 和 ignore_index 的平均交叉熵。"""
    raise NotImplementedError
''',
        tests='''import numpy as np

def test_cross_entropy_matches_manual_log_softmax():
    """验证交叉熵与手写稳定 log-softmax 公式一致。"""
    logits = np.array([[2.0, 0.0, -1.0], [0.0, 3.0, 1.0]])
    labels = np.array([0, 2])
    shifted = logits - logits.max(axis=-1, keepdims=True)
    log_probs = shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))
    expected = float((-log_probs[0, 0] - log_probs[1, 2]) / 2)
    got = cross_entropy(logits, labels)
    assert abs(got - expected) < 1e-12, f"CE 错误: {got} vs {expected}"

def test_ignore_index_excludes_padding_from_average():
    """验证 ignore_index 位置不参与 loss 平均。"""
    logits = np.array([[5.0, 0.0], [0.0, 5.0]])
    labels = np.array([0, -100])
    got = cross_entropy(logits, labels)
    expected = cross_entropy(logits[:1], labels[:1])
    assert abs(got - expected) < 1e-12, f"padding 不应影响平均: {got} vs {expected}"

def test_perplexity_is_exp_of_cross_entropy():
    """验证困惑度等于交叉熵的指数。"""
    ce = np.log(2.0)
    assert abs(perplexity(ce) - 2.0) < 1e-12, "PPL 应为 exp(CE)"

def test_label_smoothing_zero_matches_cross_entropy():
    """验证 smoothing=0 时标签平滑 CE 与普通 CE 一致。"""
    logits = np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]])
    labels = np.array([2, 0])
    got = label_smoothing_cross_entropy(logits, labels, smoothing=0.0)
    expected = cross_entropy(logits, labels)
    assert abs(got - expected) < 1e-12, f"smoothing=0 应一致: {got} vs {expected}"
''',
        hidden='''import numpy as np

def test_cross_entropy_is_stable_for_large_logits():
    """验证极大 logits 下交叉熵不会溢出。"""
    logits = np.array([[10000.0, 9999.0], [-10000.0, -10001.0]])
    labels = np.array([0, 0])
    got = cross_entropy(logits, labels)
    assert np.isfinite(got), f"CE 应为有限值: {got}"
    assert got < 0.4, f"正确类明显更大时 CE 应较小: {got}"

def test_all_ignored_labels_return_zero():
    """验证所有标签都被忽略时 loss 返回 0。"""
    logits = np.ones((2, 3))
    labels = np.array([-100, -100])
    assert cross_entropy(logits, labels) == 0.0
    assert label_smoothing_cross_entropy(logits, labels, smoothing=0.2) == 0.0

def test_label_smoothing_matches_manual_formula():
    """验证标签平滑交叉熵使用 nll 与全类别平均负 log_prob 的加权和。"""
    logits = np.array([[2.0, 0.0, -2.0]])
    labels = np.array([0])
    smoothing = 0.3
    shifted = logits - logits.max(axis=-1, keepdims=True)
    log_probs = shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))
    expected = (1 - smoothing) * (-log_probs[0, 0]) + smoothing * (-log_probs[0].mean())
    got = label_smoothing_cross_entropy(logits, labels, smoothing=smoothing)
    assert abs(got - expected) < 1e-12, f"label smoothing 公式错误: {got} vs {expected}"

def test_three_dimensional_logits_are_supported():
    """验证 logits 可以有 batch/seq 等多个前置维度。"""
    logits = np.array([[[3.0, 0.0], [0.0, 3.0]], [[1.0, 2.0], [2.0, 1.0]]])
    labels = np.array([[0, 1], [1, -100]])
    got = cross_entropy(logits, labels)
    flat = cross_entropy(logits.reshape(-1, 2), labels.reshape(-1))
    assert abs(got - flat) < 1e-12, f"多维 logits 应等价于展平有效位置: {got} vs {flat}"
''',
        solution='''import numpy as np

def _log_softmax(logits):
    logits = np.asarray(logits, dtype=float)
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))

def _valid_nll_and_log_probs(logits, labels, ignore_index):
    log_probs = _log_softmax(logits)
    labels = np.asarray(labels)
    flat_log_probs = log_probs.reshape(-1, log_probs.shape[-1])
    flat_labels = labels.reshape(-1)
    valid = flat_labels != ignore_index
    if not valid.any():
        return None, None
    valid_labels = flat_labels[valid].astype(int)
    valid_log_probs = flat_log_probs[valid]
    nll = -valid_log_probs[np.arange(len(valid_labels)), valid_labels]
    return nll, valid_log_probs

def cross_entropy(logits, labels, ignore_index=-100):
    """计算带 ignore_index 的平均交叉熵。"""
    nll, _ = _valid_nll_and_log_probs(logits, labels, ignore_index)
    if nll is None:
        return 0.0
    return float(nll.mean())

def perplexity(cross_entropy_value):
    """由交叉熵计算困惑度。"""
    return float(np.exp(cross_entropy_value))

def label_smoothing_cross_entropy(logits, labels, smoothing=0.0, ignore_index=-100):
    """计算带 label smoothing 和 ignore_index 的平均交叉熵。"""
    if not (0.0 <= smoothing <= 1.0):
        raise ValueError("smoothing 必须在 [0, 1] 内")
    nll, valid_log_probs = _valid_nll_and_log_probs(logits, labels, ignore_index)
    if nll is None:
        return 0.0
    smooth_loss = -valid_log_probs.mean(axis=-1)
    loss = (1.0 - smoothing) * nll + smoothing * smooth_loss
    return float(loss.mean())
''',
        hints=[
            "稳定 log-softmax 的关键是先减去每行最大 logit，再做 exp 和 logsum。",
            "把 `logits` 展平成 `(-1, C)`、`labels` 展平成 `(-1,)` 后处理 ignore_index 会简单很多。",
            "标签平滑不是把正确类换成 one-hot 后再手动构造矩阵；可用 `nll` 和 `-log_probs.mean(axis=-1)` 加权。",
        ],
        points=["稳定 log-softmax", "ignore_index 平均分母", "困惑度定义", "标签平滑公式"],
        numpy=True,
    ),
]
