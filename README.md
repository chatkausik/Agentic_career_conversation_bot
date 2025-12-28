---
title: Agentic_career_conversation_bot
app_file: app.py
sdk: gradio
sdk_version: 5.33.1
---

# Agentic Career Conversation Bot

An AI-powered conversational bot that acts as a digital twin for career-related interactions. The bot uses OpenAI's GPT-4o-mini model to answer questions about career, background, skills, and experience based on provided LinkedIn profile, resume, and summary documents. It features automatic response evaluation using Anthropic's Claude model and notifications via Pushover.

## Features

- 🤖 **AI-Powered Conversations**: Uses OpenAI's GPT-4o-mini for natural, context-aware responses
- 📄 **Document-Based Knowledge**: Loads information from LinkedIn PDF, resume PDF, and summary text file
- ✅ **Response Evaluation**: Automatically evaluates responses using Anthropic's Claude model for quality assurance
- 🔄 **Auto-Retry**: Automatically retries up to 2 times if a response is rejected by the evaluator
- 📱 **Push Notifications**: Sends notifications via Pushover for:
  - New user contacts (email addresses)
  - Unanswered questions
- 🛠️ **Function Calling**: Uses OpenAI function calling to record user details and track unknown questions
- 🎨 **Gradio Interface**: Beautiful, interactive web interface built with Gradio

## Requirements

- Python >= 3.13
- OpenAI API key
- Anthropic API key (optional, for response evaluation)
- Pushover token and user key (optional, for notifications)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Agentic_career_conversation_bot
   ```

2. **Install dependencies**:
   
   Using `uv` (recommended):
   ```bash
   uv pip install -r requirements.txt
   ```
   
   Or using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your personal documents**:
   
   Place your documents in the `me/` directory:
   - `me/linkedin.pdf` - Your LinkedIn profile (exported as PDF)
   - `me/resume.pdf` - Your resume (PDF format, optional)
   - `me/summary.txt` - A text summary about yourself

4. **Configure environment variables**:
   
   Create a `.env` file in the project root with the following variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
   PUSHOVER_TOKEN=your_pushover_token_here  # Optional
   PUSHOVER_USER=your_pushover_user_key_here  # Optional
   ```

## Usage

### Running the Application

Simply run:
```bash
python app.py
```

This will start a Gradio web interface. The application will:
1. Load your documents from the `me/` directory
2. Initialize the AI agent with your information
3. Launch a web interface (typically at `http://127.0.0.1:7860`)

### Testing Pushover Notifications

To test your Pushover configuration:
```bash
python test_pushover.py
```

## How It Works

1. **Document Loading**: The bot loads your LinkedIn profile, resume, and summary from the `me/` directory at startup.

2. **System Prompt**: Creates a comprehensive system prompt that includes:
   - Your name and role
   - Instructions to represent you professionally
   - The loaded documents as context
   - Instructions to use tools for recording contacts and unknown questions

3. **Conversation Flow**:
   - User sends a message
   - Bot generates a response using GPT-4o-mini with function calling enabled
   - If function calls are needed (e.g., recording email), they're executed
   - Response is evaluated by Claude (if API key is provided)
   - If rejected, the bot retries up to 2 times with feedback
   - Final response is returned to the user

4. **Tool Functions**:
   - `record_user_details`: Records when a user provides their email address
   - `record_unknown_question`: Records questions that couldn't be answered

## Project Structure

```
Agentic_career_conversation_bot/
├── app.py                 # Main application file
├── main.py                # Entry point (placeholder)
├── test_pushover.py       # Pushover notification tester
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Project configuration
├── README.md             # This file
└── me/                   # Personal documents directory
    ├── linkedin.pdf      # LinkedIn profile PDF
    ├── resume.pdf        # Resume PDF (optional)
    └── summary.txt       # Text summary
```

## Technologies Used

- **OpenAI API**: GPT-4o-mini for conversation generation
- **Anthropic API**: Claude 3.7 Sonnet for response evaluation
- **Gradio**: Web interface framework
- **pypdf**: PDF document parsing
- **python-dotenv**: Environment variable management
- **requests**: HTTP requests for Pushover notifications

## Configuration Details

### Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Optional Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key (for response evaluation)
  - If not provided, evaluation is skipped and all responses are accepted
- `PUSHOVER_TOKEN`: Your Pushover application token
- `PUSHOVER_USER`: Your Pushover user key
  - If not provided, notifications are skipped (errors are logged)

### Customization

To customize the bot for a different person:

1. Update the name in `app.py` (line 100):
   ```python
   self.name = "Your Name"
   ```

2. Replace the documents in the `me/` directory with your own

3. Update the system prompt in the `system_prompt()` method if needed

## Response Evaluation

The bot uses Anthropic's Claude model to evaluate responses based on:
- **Helpfulness**: How well the response addresses the user's question
- **Professionalism**: Tone and appropriateness
- **Factuality**: Accuracy with respect to the provided documents
- **Clarity**: How clear and understandable the response is

If a response is rejected, the bot automatically retries with the evaluator's feedback, up to 2 additional attempts.

## Notifications

The bot sends Pushover notifications for:
- **New Contacts**: When a user provides their email address
- **Unknown Questions**: When the bot encounters a question it cannot answer

To set up Pushover:
1. Create an account at [pushover.net](https://pushover.net)
2. Create an application to get a token
3. Get your user key from your account dashboard
4. Add both to your `.env` file

## Error Handling

- Missing API keys are handled gracefully (evaluation/notifications are skipped)
- PDF parsing errors are caught and logged (empty strings are used if files are missing)
- Network errors for Pushover are caught and logged without crashing the application

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions, please [open an issue](link-to-issues) or contact [your contact information].
