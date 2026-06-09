# test_main.py
from unittest.mock import patch, MagicMock
from main import conversation

def test_exit_on_quit():
    with patch("builtins.input", side_effect=["quit"]):
        conversation()  # should not raise

def test_question_limit():
    mock_response = MagicMock()
    mock_response.content[0].text = "Some answer"

    with patch("builtins.input", side_effect=["q1", "q2", "q3", "q4"]):
        with patch("main.client.messages.create", return_value=mock_response):
            conversation()  # should stop after MAX_QUESTIONS

def test_api_error_handled():
    from anthropic import AnthropicError
    with patch("builtins.input", side_effect=["hello", "quit"]):
        with patch("main.client.messages.create", side_effect=AnthropicError("fail")):
            conversation()  # should not crash
