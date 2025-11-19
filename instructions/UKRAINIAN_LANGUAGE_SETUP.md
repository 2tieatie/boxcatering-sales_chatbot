# Ukrainian Language Setup for Boxcatering Chatbot

This guide explains how to configure the AI agent to speak only Ukrainian and how to use the new GPT-4o models.

## 🎯 What's Been Added

### 1. New GPT Models

- **GPT-4o** - Latest and fastest model (recommended)
- **GPT-4o Mini** - Fast and efficient alternative
- **GPT-4** - Previous recommended model
- **GPT-4 Turbo** - Latest GPT-4 version
- **GPT-3.5 Turbo** - Fast and cost-effective

### 2. Ukrainian Language Support

- **Default Language**: Ukrainian (Українська)
- **Strict Language Enforcement**: AI will only respond in Ukrainian
- **Language Configuration**: Available in chatbot settings
- **Fallback Handling**: Automatic language detection and enforcement

## 🚀 Setup Instructions

### Step 1: Run the Database Migration

```bash
python scripts/migrate_chatbot_config.py
```

This will:

- Add `language` and `force_language` columns to the `chatbot_configs` table
- Set default language to Ukrainian (`uk`)
- Enable strict language enforcement by default

### Step 2: Configure Chatbot Settings

1. Go to `/chatbot-settings` page
2. In the **AI Model Settings** section:
   - Select **GPT-4o** as the AI model (recommended)
   - Set your preferred temperature and max tokens
3. In the **Language Settings** section:
   - Select **🇺🇦 Ukrainian (Українська)** as the chatbot language
   - Enable **Strict Language Enforcement** checkbox
4. Save your settings

### Step 3: Configure System Settings

1. Go to `/settings` page
2. In the **OpenAI Configuration** section:
   - Select **GPT-4o** as the model
   - Enter your OpenAI API key
3. Save your settings

## 🔧 How It Works

### Language Enforcement

The AI agent will now:

1. **Always respond in Ukrainian** when Ukrainian is selected
2. **Ignore customer language** - even if they write in English/German/etc.
3. **Maintain consistency** across all conversations
4. **Provide natural Ukrainian responses** for catering inquiries

### System Prompt Enhancement

The system prompt now includes:

```uk
ВАЖЛИВО: Ви ОБОВ'ЯЗКОВО повинні відповідати ТІЛЬКИ українською мовою.
Ніколи не використовуйте інші мови, навіть якщо клієнт пише англійською або іншою мовою.
Всі ваші відповіді мають бути українською мовою.
```

### Database Configuration

The `chatbot_configs` table now includes:

- `language`: The language the AI should use (default: 'uk')
- `force_language`: Whether to strictly enforce the selected language (default: true)

## 📱 Available Languages

You can configure the chatbot to use:

- 🇺🇦 **Ukrainian** (Українська) - Default and recommended
- 🇺🇸 **English**
- 🇩🇪 **German** (Deutsch)
- 🇫🇷 **French** (Français)
- 🇪🇸 **Spanish** (Español)

## 🧪 Testing

### Test Ukrainian Language

1. Start a chat with the chatbot
2. Write your message in any language (English, German, etc.)
3. The AI should respond **only in Ukrainian**

### Test GPT-4o Model

1. Configure the AI model to use GPT-4o
2. Send a complex catering inquiry
3. You should notice faster and more accurate responses

## 🔍 Troubleshooting

### Language Not Working

- Check that `force_language` is enabled in chatbot settings
- Verify the database migration ran successfully
- Check the browser console for any JavaScript errors

### GPT-4o Not Available

- Ensure you have a valid OpenAI API key
- Check that your OpenAI account has access to GPT-4o
- Verify the model name is exactly `gpt-4o` (not `gpt-4-o`)

### Database Issues

- Run the migration script again: `python scripts/migrate_chatbot_config.py`
- Check database connection and permissions
- Verify the `chatbot_configs` table exists

## 📊 Benefits

### Ukrainian Language

- **Local Market Focus**: Better serves Ukrainian customers
- **Cultural Relevance**: More appropriate for Ukrainian business context
- **Customer Trust**: Native language builds confidence
- **Professional Image**: Shows commitment to local market

### GPT-4o Models

- **Faster Responses**: Reduced latency for better user experience
- **Better Quality**: More accurate and helpful responses
- **Cost Efficiency**: Better performance per token
- **Latest Features**: Access to newest AI capabilities

## 🔄 Future Updates

The system is designed to:

- Easily add more languages
- Support multiple language configurations
- Allow per-conversation language switching
- Integrate with translation services if needed

## 📞 Support

If you encounter issues:

1. Check the application logs for error messages
2. Verify all configuration settings are correct
3. Ensure the database migration completed successfully
4. Test with a simple message first

---

**Note**: The AI agent will now strictly respond in Ukrainian by default. This ensures consistent Ukrainian language support for your boxcatering business in Ukraine.
