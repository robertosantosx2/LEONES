"""kinetic.llama_cpp against llama-cpp-python's response shapes.

KINETIC_TEST_GGUF=SmolLM2-135M-Instruct-f16.gguf KINETIC_TEST_EMBED_GGUF=bge-small-en-v1.5-f16.gguf
python -m unittest discover -s tests
"""

import os
import unittest

from kinetic.llama_cpp import Llama

TEXT = os.environ.get("KINETIC_TEST_GGUF")
EMBED = os.environ.get("KINETIC_TEST_EMBED_GGUF")
QUESTION = [{"role": "user", "content": "What is the capital of France?"}]


@unittest.skipUnless(TEXT, "set KINETIC_TEST_GGUF")
class Completion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm = Llama(model_path=TEXT, n_ctx=2048, n_gpu_layers=0, seed=1, verbose=False)

    def test_completion_shape_and_limits(self):
        out = self.llm("The capital of France is", max_tokens=8, temperature=0)
        self.assertEqual(out["object"], "text_completion")
        choice = out["choices"][0]
        self.assertEqual(choice["finish_reason"], "length")
        self.assertIsNone(choice["logprobs"])
        self.assertEqual(out["usage"]["completion_tokens"], 8)
        self.assertEqual(out["usage"]["total_tokens"], out["usage"]["prompt_tokens"] + 8)
        self.assertTrue(choice["text"].strip())
        self.assertEqual(self.llm.n_ctx(), 2048)

    def test_streamed_completion_matches(self):
        whole = self.llm.create_completion("Once upon a time", max_tokens=12, temperature=0)
        chunks = list(self.llm.create_completion("Once upon a time", max_tokens=12, temperature=0, stream=True))
        self.assertEqual("".join(c["choices"][0]["text"] for c in chunks), whole["choices"][0]["text"])
        self.assertEqual(chunks[-1]["choices"][0]["finish_reason"], "length")
        self.assertTrue(all(c["choices"][0]["finish_reason"] is None for c in chunks[:-1]))

    def test_echo_stop_and_seed(self):
        out = self.llm("Count: 1, 2, 3,", max_tokens=20, temperature=0, stop=[" 6"], echo=True)
        text = out["choices"][0]["text"]
        self.assertTrue(text.startswith("Count: 1, 2, 3,"))
        self.assertNotIn(" 6", text)
        self.assertEqual(out["choices"][0]["finish_reason"], "stop")
        a = self.llm("Hello", max_tokens=16, temperature=1.0, seed=7)["choices"][0]["text"]
        b = self.llm("Hello", max_tokens=16, temperature=1.0, seed=7)["choices"][0]["text"]
        self.assertEqual(a, b)

    def test_chat_shape_and_stream(self):
        out = self.llm.create_chat_completion(messages=QUESTION, max_tokens=16, temperature=0)
        self.assertEqual(out["object"], "chat.completion")
        message = out["choices"][0]["message"]
        self.assertEqual(message["role"], "assistant")
        self.assertIn("Paris", message["content"])
        chunks = list(self.llm.create_chat_completion(messages=QUESTION, max_tokens=16, temperature=0, stream=True))
        self.assertEqual(chunks[0]["choices"][0]["delta"], {"role": "assistant"})
        text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
        self.assertEqual(text, message["content"])
        self.assertEqual(chunks[-1]["choices"][0]["delta"], {})
        self.assertEqual(chunks[-1]["object"], "chat.completion.chunk")

    def test_tokens_round_trip(self):
        tokens = self.llm.tokenize(b"Hello world")
        self.assertEqual(self.llm.detokenize(tokens).strip(), b"Hello world")
        bare = self.llm.tokenize(b"Hello world", add_bos=False)
        self.assertNotEqual(bare[0], self.llm.token_bos())
        self.assertIsInstance(self.llm.token_eos(), int)

    def test_unsupported_arguments_raise(self):
        with self.assertRaises(NotImplementedError):
            self.llm("Hi", logprobs=5)
        with self.assertRaises(NotImplementedError):
            self.llm.create_chat_completion(messages=QUESTION, tools=[{"type": "function"}])


@unittest.skipUnless(EMBED, "set KINETIC_TEST_EMBED_GGUF")
class Embedding(unittest.TestCase):
    def test_embed_shapes(self):
        llm = Llama(model_path=EMBED, embedding=True, verbose=False)
        one = llm.embed("a cat")
        self.assertIsInstance(one[0], float)
        two = llm.embed(["a cat", "a dog"], normalize=True)
        self.assertEqual(len(two), 2)
        self.assertAlmostEqual(sum(x * x for x in two[0]), 1.0, places=4)
        out = llm.create_embedding(["a cat"])
        self.assertEqual(out["data"][0]["object"], "embedding")
        self.assertGreater(out["usage"]["prompt_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
