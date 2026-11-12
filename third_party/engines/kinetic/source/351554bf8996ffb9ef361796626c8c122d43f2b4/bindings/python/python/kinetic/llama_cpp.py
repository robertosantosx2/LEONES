"""The commonly used part of llama-cpp-python's API, run by Kinetic.

Switch a project by changing one import::

    from kinetic.llama_cpp import Llama   # was: from llama_cpp import Llama

    llm = Llama(model_path="model.gguf", n_ctx=4096, n_gpu_layers=-1, seed=42)
    print(llm("Q: Name the planets. A:", max_tokens=64, stop=["Q:"])["choices"][0]["text"])
    print(llm.create_chat_completion(messages=[{"role": "user", "content": "Hi"}]))

Arguments that would change the output and are not supported, such as
grammars, tools or logprobs, raise NotImplementedError instead of being
ignored. `kinetic serve` offers tools and JSON output over HTTP.
"""

import math
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional, Union

from ._kinetic import Model

__all__ = ["Llama", "LLAMA_DEFAULT_SEED"]

LLAMA_DEFAULT_SEED = 0xFFFFFFFF


def _unsupported(**given: Any) -> None:
    for name, value in given.items():
        if value:
            raise NotImplementedError(f"kinetic.llama_cpp does not support {name}")


def _stops(stop: Union[None, str, List[str]]) -> List[str]:
    if stop is None:
        return []
    return [stop] if isinstance(stop, str) else list(stop)


def _text(content: Any) -> str:
    """A message's content as text: a string, None, or a list of parts."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for part in content:
        if part.get("type") != "text":
            raise NotImplementedError("kinetic.llama_cpp takes text content only")
        parts.append(part["text"])
    return "".join(parts)


def _usage(done: Dict[str, Any]) -> Dict[str, int]:
    return {
        "prompt_tokens": done["prompt_tokens"],
        "completion_tokens": done["completion_tokens"],
        "total_tokens": done["prompt_tokens"] + done["completion_tokens"],
    }


class Llama:
    """A model loaded as llama_cpp.Llama loads one.

    `n_gpu_layers=0` (the default, as in llama-cpp-python) runs on the CPU;
    any other value runs on the GPU when the model fits there, since Kinetic
    places a model wholly on one device. `n_ctx=0` takes the model's own
    context length.
    """

    def __init__(
        self,
        model_path: str,
        *,
        n_gpu_layers: int = 0,
        seed: int = LLAMA_DEFAULT_SEED,
        n_ctx: int = 512,
        embedding: bool = False,
        verbose: bool = True,
        **kwargs: Any,
    ) -> None:
        self.model_path = model_path
        self.verbose = verbose
        self._seed = None if seed == LLAMA_DEFAULT_SEED else seed
        self._model = Model(model_path, context=n_ctx or None, gpu=n_gpu_layers != 0)
        if embedding and not self._model.is_embedding:
            raise ValueError(f"{model_path} generates text; embeddings need an embedding model")

    def n_ctx(self) -> int:
        return self._model.context_length or 0

    def token_bos(self) -> int:
        return -1 if self._model.bos is None else self._model.bos

    def token_eos(self) -> int:
        return -1 if self._model.eos is None else self._model.eos

    def tokenize(self, text: bytes, add_bos: bool = True, special: bool = False) -> List[int]:
        tokens = self._model.tokenize(text.decode("utf-8", errors="replace"), special)
        bos = self._model.bos
        if not add_bos and tokens and tokens[0] == bos:
            tokens = tokens[1:]
        return tokens

    def detokenize(self, tokens: List[int], prev_tokens: Optional[List[int]] = None, special: bool = False) -> bytes:
        return self._model.detokenize(list(tokens))

    def _sampling(self, seed: Optional[int], **settings: Any) -> Dict[str, Any]:
        settings["seed"] = self._seed if seed is None else seed
        return settings

    def create_completion(
        self,
        prompt: Union[str, List[int]],
        suffix: Optional[str] = None,
        max_tokens: Optional[int] = 16,
        temperature: float = 0.8,
        top_p: float = 0.95,
        min_p: float = 0.05,
        typical_p: float = 1.0,
        logprobs: Optional[int] = None,
        echo: bool = False,
        stop: Union[None, str, List[str]] = None,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        repeat_penalty: float = 1.0,
        top_k: int = 40,
        stream: bool = False,
        seed: Optional[int] = None,
        grammar: Any = None,
        logits_processor: Any = None,
        **kwargs: Any,
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        _unsupported(
            suffix=suffix,
            logprobs=logprobs,
            typical_p=typical_p != 1.0,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            grammar=grammar,
            logits_processor=logits_processor,
        )
        if not isinstance(prompt, str):
            prompt = self.detokenize(prompt).decode("utf-8", errors="replace")
        settings = self._sampling(
            seed,
            max_tokens=max_tokens if max_tokens and max_tokens > 0 else None,
            temperature=temperature,
            top_p=top_p,
            min_p=min_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            stop=_stops(stop),
        )
        meta = {
            "id": f"cmpl-{uuid.uuid4()}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": self.model_path,
        }
        head = prompt if echo else ""
        if not stream:
            done = self._model.complete(prompt=prompt, **settings)
            choice = {"text": head + done["text"], "index": 0, "logprobs": None, "finish_reason": done["finish_reason"]}
            return {**meta, "choices": [choice], "usage": _usage(done)}
        return self._stream_completion(meta, head, self._model.complete(prompt=prompt, stream=True, **settings))

    @staticmethod
    def _stream_completion(meta: Dict[str, Any], head: str, pieces: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        if head:
            yield {**meta, "choices": [{"text": head, "index": 0, "logprobs": None, "finish_reason": None}]}
        for piece in pieces:
            finish = piece.get("finish_reason")
            yield {**meta, "choices": [{"text": piece["text"], "index": 0, "logprobs": None, "finish_reason": finish}]}

    __call__ = create_completion

    def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        functions: Any = None,
        function_call: Any = None,
        tools: Any = None,
        tool_choice: Any = None,
        temperature: float = 0.2,
        top_p: float = 0.95,
        top_k: int = 40,
        min_p: float = 0.05,
        typical_p: float = 1.0,
        stream: bool = False,
        stop: Union[None, str, List[str]] = None,
        seed: Optional[int] = None,
        response_format: Any = None,
        max_tokens: Optional[int] = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        repeat_penalty: float = 1.0,
        logprobs: Optional[bool] = None,
        grammar: Any = None,
        logits_processor: Any = None,
        **kwargs: Any,
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        if response_format is not None and response_format.get("type") == "text":
            response_format = None
        _unsupported(
            functions=functions,
            function_call=function_call,
            tools=tools,
            tool_choice=tool_choice if tool_choice != "none" else None,
            typical_p=typical_p != 1.0,
            response_format=response_format,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            logprobs=logprobs,
            grammar=grammar,
            logits_processor=logits_processor,
        )
        turns = [{"role": m["role"], "content": _text(m.get("content"))} for m in messages]
        settings = self._sampling(
            seed,
            max_tokens=max_tokens if max_tokens and max_tokens > 0 else None,
            temperature=temperature,
            top_p=top_p,
            min_p=min_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            stop=_stops(stop),
        )
        meta = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "created": int(time.time()),
            "model": self.model_path,
        }
        if not stream:
            done = self._model.complete(messages=turns, **settings)
            message = {"role": "assistant", "content": done["text"]}
            choice = {"index": 0, "message": message, "logprobs": None, "finish_reason": done["finish_reason"]}
            return {**meta, "object": "chat.completion", "choices": [choice], "usage": _usage(done)}
        return self._stream_chat(meta, self._model.complete(messages=turns, stream=True, **settings))

    @staticmethod
    def _stream_chat(meta: Dict[str, Any], pieces: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        chunk = {**meta, "object": "chat.completion.chunk"}
        yield {**chunk, "choices": [{"index": 0, "delta": {"role": "assistant"}, "logprobs": None, "finish_reason": None}]}
        for piece in pieces:
            finish = piece.get("finish_reason")
            delta = {"content": piece["text"]} if finish is None else {}
            yield {**chunk, "choices": [{"index": 0, "delta": delta, "logprobs": None, "finish_reason": finish}]}

    def embed(
        self,
        input: Union[str, List[str]],
        normalize: bool = False,
        truncate: bool = True,
        return_count: bool = False,
    ) -> Any:
        texts = [input] if isinstance(input, str) else list(input)
        vectors = self._model.embed(texts)
        if normalize:
            vectors = [[x / (math.sqrt(sum(v * v for v in vec)) or 1.0) for x in vec] for vec in vectors]
        result = vectors[0] if isinstance(input, str) else vectors
        if return_count:
            count = sum(len(self._model.tokenize(t)) for t in texts)
            return result, count
        return result

    def create_embedding(self, input: Union[str, List[str]], model: Optional[str] = None) -> Dict[str, Any]:
        texts = [input] if isinstance(input, str) else list(input)
        vectors = self._model.embed(texts)
        tokens = sum(len(self._model.tokenize(t)) for t in texts)
        return {
            "object": "list",
            "data": [{"object": "embedding", "embedding": v, "index": i} for i, v in enumerate(vectors)],
            "model": model or self.model_path,
            "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
        }
