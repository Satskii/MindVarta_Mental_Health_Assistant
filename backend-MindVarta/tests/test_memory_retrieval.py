"""Regression tests for conversation-memory persistence and retrieval."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


def load_repository_with_fake_db(rows):
    calls = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params):
            calls.append((query, params))

        def fetchall(self):
            return rows

    class Connection:
        def cursor(self):
            return Cursor()

    connection_module = types.ModuleType("database.connection")
    connection_module.get_connection = lambda: Connection()
    connection_module.release_connection = lambda _conn: None
    sys.modules["database.connection"] = connection_module

    spec = importlib.util.spec_from_file_location("memory_repository", BACKEND / "database" / "repository.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, calls


def load_response_generator():
    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = object
    sys.modules["openai"] = openai_module

    config_module = types.ModuleType("ai_module.config")
    config_module.GROQ_API_KEY = "test"
    config_module.AI_MODEL = "test"
    config_module.TEMPERATURE = 0
    config_module.MAX_TOKENS = 250
    config_module.BASE_URL = "https://example.test"
    sys.modules["ai_module.config"] = config_module

    prompts_module = types.ModuleType("ai_module.prompts.language_prompts")
    prompts_module.PromptManagerV3 = lambda: object()
    sys.modules["ai_module.prompts.language_prompts"] = prompts_module

    spec = importlib.util.spec_from_file_location("memory_response_generator", BACKEND / "ai_module" / "response_generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MemoryRetrievalTests(unittest.TestCase):
    def test_cross_session_query_uses_one_rolling_memory_per_conversation(self):
        repository, calls = load_repository_with_fake_db([("Latest session memory",), ("Older session memory",)])

        context = repository.get_user_context_summary("user-1", "current-conversation")

        self.assertEqual(context, "Latest session memory | Older session memory")
        query, params = calls[0]
        self.assertIn("SELECT c.memory", query)
        self.assertIn("c.memory <> ''", query)
        self.assertNotIn("conversation_summaries", query)
        self.assertEqual(params, ("user-1", "current-conversation", "current-conversation"))

    def test_memory_is_not_removed_when_prompt_is_within_budget(self):
        generator = load_response_generator()
        memory = "User's name is Anika and she is preparing for exams."
        messages = [
            {"role": "system", "content": "Keep replies supportive."},
            {"role": "system", "content": f"What you already know about this person:\n{memory}\n\nUse this naturally. Do not ask them to repeat what they already shared."},
            {"role": "user", "content": "What is my name?"},
        ]

        trimmed = generator.trim_prompt_for_budget(messages, max_tokens=1000)

        self.assertTrue(any(memory in message["content"] for message in trimmed))

    def test_fused_emotion_words_are_separated_without_damaging_normal_words(self):
        generator = load_response_generator()

        repaired = generator.fix_missing_spaces(
            "Grief can bring sadnessangerconfusionguilteven moments of relief."
        )

        self.assertIn("sadness anger confusion guilt even moments", repaired)
        self.assertEqual(generator.fix_missing_spaces("A stranger listened."), "A stranger listened.")

    def test_user_reported_spacing_issue_is_fully_repaired(self):
        generator = load_response_generator()
        reported_text = (
            "YesAnikesh— I remember your name. How are you feeling today? "
            "If there’s anything on your mind or something you’d like to talk aboutI’m here to listen."
        )
        repaired = generator.fix_missing_spaces(reported_text)
        self.assertIn("Yes, Anikesh", repaired)
        self.assertIn("talk about I’m", repaired)
        self.assertIn("— I remember", repaired)
        self.assertNotIn("YesAnikesh", repaired)
        self.assertNotIn("aboutI’m", repaired)

    def test_compound_words_are_preserved(self):
        generator = load_response_generator()
        compounds = [
            "A stranger listened.",
            "We can work together.",
            "I understand how you feel.",
            "Maybe we can try again.",
            "This is important.",
            "Take care of yourself.",
            "Sometimes it feels hard.",
            "I am talking to myself today.",
        ]
        for sentence in compounds:
            self.assertEqual(generator.fix_missing_spaces(sentence), sentence)

    def test_em_dash_and_indic_punctuation_spacing(self):
        generator = load_response_generator()
        self.assertEqual(
            generator.fix_missing_spaces("YesI remember—your name"),
            "Yes I remember — your name"
        )
        self.assertEqual(
            generator.fix_missing_spaces("আমি আছি।কী হয়েছে বল?"),
            "আমি আছি। কী হয়েছে বল?"
        )


    def test_complete_reply_check_uses_visible_text_not_json_wrapper(self):
        generator = load_response_generator()

        self.assertFalse(generator.looks_incomplete("I'm here with you. What feels hardest right now?"))
        self.assertTrue(generator.looks_incomplete("I'm here with you, and I want to"))

    def test_provider_response_label_is_removed(self):
        generator = load_response_generator()

        cleaned = generator.enforce_response_length_and_format(
            "response I understand how stressful this feels. What would help most right now?"
        )

        self.assertEqual(
            cleaned,
            "I understand how stressful this feels. What would help most right now?"
        )

    def test_repeated_follow_up_question_is_removed(self):
        generator = load_response_generator()

        cleaned = generator.enforce_response_length_and_format(
            "Try short walks and consistent sleep. How many minutes can you dedicate "
            "to a walk each day? followupquestion How many minutes can you dedicate "
            "to a walk each day?"
        )

        self.assertEqual(
            cleaned,
            "Try short walks and consistent sleep. How many minutes can you dedicate to a walk each day?"
        )

    def test_short_fallback_is_complete_and_invites_a_follow_up(self):
        generator = load_response_generator()

        fallback = generator.get_complete_fallback("english")

        self.assertTrue(fallback.endswith("?"))
        self.assertIn("What feels most important", fallback)

    def test_provider_length_cutoff_is_replaced_not_stitched_to_partial_json(self):
        generator = load_response_generator()

        class PromptManager:
            def detect_possible_crisis(self, _text):
                return False

            def detect_active_harm(self, _text):
                return False

            def build_prompt(self, **_kwargs):
                return [{"role": "system", "content": "supportive"}]

        def choice(content, finish_reason):
            return types.SimpleNamespace(
                message=types.SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )

        first = choice('{"actual_response":"I am here and",', "length")
        replacement = choice(
            '{"actual_response":"I am here with you. What feels hardest right now?",'
            '"summarize_context":"User is upset."}',
            "stop",
        )

        class Completions:
            def __init__(self):
                self.responses = [first, replacement]

            def create(self, **_kwargs):
                return types.SimpleNamespace(choices=[self.responses.pop(0)])

        client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=Completions()))
        generator.prompt_manager = PromptManager()
        generator.OpenAI = lambda **_kwargs: client

        result = generator.generate_response("I feel sad", [], "english")

        self.assertEqual(result["actual_response"], "I am here with you. What feels hardest right now?")


if __name__ == "__main__":
    unittest.main()
