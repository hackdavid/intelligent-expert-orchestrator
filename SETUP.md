# 🚀 Quick Setup Guide

## Prerequisites
- Python 3.8 or higher
- Azure OpenAI account with API access
- Git

## Step-by-Step Setup

### 1. Clone and Navigate
```bash
git clone <your-repo-url>
cd adventure_system
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy environment template
cp env_sample.txt .env

# Edit .env file with your Azure OpenAI credentials
```

**Required Environment Variables:**
```bash
AZURE_OPENAI_API_KEY_ANNA_GPT4O="your-actual-api-key"
AZURE_OPENAI_ENDPOINT_ANNA_GPT4O="https://your-resource.openai.azure.com/"
MODEL_NAME_ANNA_GPT4O="gpt-4o"
DEPLOYMENT_NAME_ANNA_GPT4O="your-deployment-name"
OPENAI_API_VERSION_ANNA_GPT4O="2024-08-01-preview"
OPENAI_API_TYPE_ANNA_GPT4O="azure"
```

### 5. Test the System
```bash
python run_anna_coach.py
```

## 🎯 First Run Example

When you run the system, you'll see:
```
🤖 Anna AI Coach - Interactive Mode
============================================================
Ask me anything about business, strategy, finance, legal, or technical topics!
Type 'quit' or 'exit' to stop the session.
------------------------------------------------------------

💬 Your question: How should I structure my startup's equity?
```

## 🔧 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you're in the virtual environment
2. **API Key Error**: Verify your Azure OpenAI credentials in `.env`
3. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

### Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Review the logs in the `logs/` directory for error details
- Ensure your Azure OpenAI deployment is active and accessible

## 🎉 You're Ready!

The system is now configured and ready to handle complex multi-agent problem-solving. Try asking questions about business strategy, financial planning, legal considerations, or technical challenges!
