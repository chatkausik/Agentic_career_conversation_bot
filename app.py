"""
Agentic Career Conversation Bot

An AI-powered conversational bot that acts as a digital twin for career-related interactions.
The bot uses OpenAI's GPT-4o-mini to answer questions about career, background, skills, and
experience based on provided LinkedIn profile, resume, and summary documents.

Features:
- Document-based knowledge from LinkedIn PDF, resume PDF, and summary text
- Automatic response evaluation using Anthropic's Claude model
- Auto-retry mechanism for rejected responses (up to 2 attempts)
- Pushover notifications for new contacts and unanswered questions
- OpenAI function calling for structured interactions
- Gradio web interface for user interactions
"""

from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr

# Load environment variables from .env file
load_dotenv(override=True)


def push(text):
    """
    Send a push notification via Pushover service.
    
    This function sends a notification to the configured Pushover account.
    If Pushover credentials are not configured, the function silently returns
    without sending a notification.
    
    Args:
        text (str): The message text to send as a notification.
    
    Note:
        Requires PUSHOVER_TOKEN and PUSHOVER_USER environment variables.
        If either is missing, the function will log a message and return early.
    """
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if not token or not user:
        print("Pushover: Missing PUSHOVER_TOKEN or PUSHOVER_USER", flush=True)
        return
    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": token,
                "user": user,
                "message": text,
            },
            timeout=10
        )
        response.raise_for_status()
        print(f"Pushover: Message sent successfully", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Pushover: Error sending message - {e}", flush=True)
    except Exception as e:
        print(f"Pushover: Unexpected error - {e}", flush=True)


def record_user_details(email, name="Name not provided", notes="not provided"):
    """
    Record user contact details and send a Pushover notification.
    
    This function is called by the AI agent when a user provides their email address
    or expresses interest in being contacted. It formats the information and sends
    a notification via Pushover.
    
    Args:
        email (str): The user's email address (required).
        name (str, optional): The user's name. Defaults to "Name not provided".
        notes (str, optional): Additional context about the conversation. 
                              Defaults to "not provided".
    
    Returns:
        dict: A confirmation dictionary with status "ok".
    
    Note:
        This function is exposed as a tool to the OpenAI API for function calling.
    """
    print(f"Tool called: record_user_details(email={email}, name={name}, notes={notes})", flush=True)
    message = f"New contact: {name}\nEmail: {email}\nNotes: {notes}"
    push(message)
    return {"recorded": "ok"}


def record_unknown_question(question):
    """
    Record a question that the AI agent couldn't answer.
    
    This function is called by the AI agent when it encounters a question it cannot
    answer based on the provided documents. It sends a notification via Pushover
    so the question can be reviewed and potentially answered later.
    
    Args:
        question (str): The question that couldn't be answered.
    
    Returns:
        dict: A confirmation dictionary with status "ok".
    
    Note:
        This function is exposed as a tool to the OpenAI API for function calling.
    """
    print(f"Tool called: record_unknown_question(question={question})", flush=True)
    push(f"Unanswered question: {question}")
    return {"recorded": "ok"}


# OpenAI function calling schema for recording user contact details
record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address. Extract the actual email address from the user's message - do not use placeholders like '[email]' or 'email@example.com'. Use the exact email address the user provided.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The actual email address provided by the user in their message. Extract it exactly as they wrote it. Must be a real email address, not a placeholder."
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it. Use 'Name not provided' if no name was given."
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context. Use 'not provided' if there's nothing notable."
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

# OpenAI function calling schema for recording unanswered questions
record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

# List of tools available to the OpenAI API for function calling
tools = [{"type": "function", "function": record_user_details_json},
         {"type": "function", "function": record_unknown_question_json}]


class Me:
    """
    Main class representing the AI agent that acts as a digital twin.
    
    This class manages the conversation bot, loads personal documents (LinkedIn profile,
    resume, and summary), handles tool calls, evaluates responses, and manages the
    conversation flow with automatic retry logic.
    
    Attributes:
        openai (OpenAI): OpenAI client instance for API calls.
        name (str): The name of the person the bot represents.
        linkedin (str): Extracted text from the LinkedIn profile PDF.
        resume (str): Extracted text from the resume PDF.
        summary (str): Text summary loaded from summary.txt file.
    """

    def __init__(self):
        """
        Initialize the Me class.
        
        Sets up the OpenAI client, loads personal documents from the me/ directory,
        and extracts text from PDF files. If PDF files are missing or unreadable,
        the corresponding attributes will be empty strings.
        
        Raises:
            FileNotFoundError: If me/summary.txt is not found (other files are optional).
        """
        self.openai = OpenAI()
        self.name = "Joshua"

        # Read LinkedIn and Resume PDFs from local me/ directory
        self.linkedin = ""
        self.resume = ""
        try:
            reader = PdfReader("me/linkedin.pdf")
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    self.linkedin += text
        except Exception:
            # LinkedIn PDF is optional - continue if missing
            pass
        try:
            reader_r = PdfReader("me/resume.pdf")
            for page in reader_r.pages:
                text = page.extract_text()
                if text:
                    self.resume += text
        except Exception:
            # Resume PDF is optional - continue if missing
            pass

        # Summary file is required
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        """
        Execute tool calls returned by the OpenAI API.
        
        This method processes function calls made by the AI agent, executes the
        corresponding Python functions, and returns the results in the format
        expected by the OpenAI API.
        
        Args:
            tool_calls: List of tool call objects from OpenAI API response.
        
        Returns:
            list: List of tool result messages formatted for the OpenAI API.
                 Each message has role "tool", content (JSON string), and tool_call_id.
        
        Note:
            If a tool function is not found, an empty dict is returned for that tool.
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            print(f"Arguments: {arguments}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
        return results

    def system_prompt(self):
        """
        Generate the system prompt for the AI agent.
        
        Creates a comprehensive system prompt that includes:
        - Instructions for the agent's role and behavior
        - The person's name and context
        - Instructions to use tools for recording contacts and unknown questions
        - The loaded documents (summary, LinkedIn profile, resume) as context
        
        Returns:
            str: The complete system prompt string to be used with the OpenAI API.
        """
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, " \
                        f"particularly questions related to {self.name}'s career, background, skills and experience. " \
                        f"Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. " \
                        f"You are given a summary, a LinkedIn profile, and a resume which you can use to answer questions. " \
                        f"Be professional and engaging, as if talking to a potential client or future employer who came across the website. " \
                        f"If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer. " \
                        f"If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        # Append the loaded documents as context
        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n## Resume:\n{self.resume}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt

    def _evaluate_with_anthropic(self, reply, message, history_messages):
        """
        Evaluate a response using Anthropic's Claude model.
        
        This private method sends the agent's reply to Claude for evaluation based on:
        - Helpfulness: How well the response addresses the question
        - Professionalism: Tone and appropriateness
        - Factuality: Accuracy with respect to the provided documents
        - Clarity: How clear and understandable the response is
        
        Args:
            reply (str): The agent's reply to evaluate.
            message (str): The user's original message.
            history_messages (list): The conversation history up to this point.
        
        Returns:
            dict: Evaluation result with keys:
                - is_acceptable (bool): Whether the response is acceptable
                - feedback (str): Feedback from the evaluator (1-2 sentences)
        
        Note:
            If ANTHROPIC_API_KEY is not set, returns {"is_acceptable": True, "feedback": "Evaluator unavailable"}.
            On any error, defaults to accepting the response to avoid blocking the conversation.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"is_acceptable": True, "feedback": "Evaluator unavailable"}
        rubric = (
            "You are an evaluator that decides whether a response is acceptable. "
            "Judge helpfulness, professionalism, factuality with respect to the provided persona documents, and clarity. "
            "Return JSON with: is_acceptable (true/false) and feedback (1-2 short sentences)."
        )
        convo = json.dumps(history_messages, ensure_ascii=False)
        prompt = (
            f"Conversation so far (JSON array of messages):\n{convo}\n\n"
            f"User message: {message}\n\nAgent reply: {reply}\n\nProvide only the JSON object."
        )
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-7-sonnet-latest",
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": rubric},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            r.raise_for_status()
            out = r.json()
            parts = out.get("content", [])
            text = "".join([p.get("text", "") for p in parts if isinstance(p, dict)])
            try:
                data = json.loads(text)
            except Exception:
                # If JSON parsing fails, accept the response and use the text as feedback
                data = {"is_acceptable": True, "feedback": text.strip()[:400]}
            if "is_acceptable" not in data:
                data["is_acceptable"] = True
            if "feedback" not in data:
                data["feedback"] = ""
            return data
        except Exception as e:
            # On any error, default to accepting the response
            return {"is_acceptable": True, "feedback": str(e)}

    def chat(self, message, history):
        """
        Process a user message and generate a response.
        
        This is the main conversation handler that:
        1. Generates an initial response using GPT-4o-mini
        2. Handles any function calls (tool calls) that the model requests
        3. Evaluates the response using Claude (if available)
        4. Retries up to 2 times if the response is rejected
        5. Returns the final response
        
        The method supports multi-turn function calling, where the model can make
        multiple tool calls in sequence before providing a final answer.
        
        Args:
            message (str): The user's message.
            history (list): Previous conversation messages in OpenAI format.
                          Each message is a dict with "role" and "content" keys.
        
        Returns:
            str: The agent's response to the user's message.
        
        Note:
            - Function calls are handled automatically and may be executed multiple times
            - If evaluation is unavailable, responses are always accepted
            - Maximum 2 retry attempts if a response is rejected by the evaluator
        """
        base_system = self.system_prompt()
        messages = [{"role": "system", "content": base_system}] + history + [{"role": "user", "content": message}]
        
        # First attempt: Generate response and handle any function calls
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason == "tool_calls":
                # Model wants to call functions - execute them and continue
                tool_msg = response.choices[0].message
                tool_calls = tool_msg.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(tool_msg)
                messages.extend(results)
            else:
                # Model provided a final response
                done = True
        reply = response.choices[0].message.content

        # Evaluate the response and optionally retry up to 2 times
        eval_history = [m for m in messages if m["role"] in ("system", "user", "assistant", "tool")]
        evaluation = self._evaluate_with_anthropic(reply, message, eval_history)
        attempts = 0
        while not evaluation.get("is_acceptable", True) and attempts < 2:
            attempts += 1
            # Add evaluator feedback to system prompt for retry
            improved_system = base_system + (
                "\n\n## Previous answer rejected\n"
                f"Your previous answer was:\n{reply}\n\n"
                f"Reason for rejection (from evaluator):\n{evaluation.get('feedback','')}\n\n"
                "Revise your answer to address the feedback while staying faithful to the provided documents."
            )
            messages = [{"role": "system", "content": improved_system}] + history + [{"role": "user", "content": message}]
            done = False
            while not done:
                response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
                if response.choices[0].finish_reason == "tool_calls":
                    tool_msg = response.choices[0].message
                    tool_calls = tool_msg.tool_calls
                    results = self.handle_tool_call(tool_calls)
                    messages.append(tool_msg)
                    messages.extend(results)
                else:
                    done = True
            reply = response.choices[0].message.content
            eval_history = [m for m in messages if m["role"] in ("system", "user", "assistant", "tool")]
            evaluation = self._evaluate_with_anthropic(reply, message, eval_history)

        return reply


if __name__ == "__main__":
    """
    Main entry point for the application.
    
    Initializes the Me class and launches the Gradio chat interface.
    The interface will be available at http://127.0.0.1:7860 by default.
    """
    me = Me()
    gr.ChatInterface(me.chat, type="messages").launch()

