# Task 15: Alerting Telegram - Implementation Prompt

## Objective

Implement Telegram notification channel for the alerting system.

## Context

You are implementing Task 15 of the Master Orchestrator for the AlgoTrading system.
This is Phase 5 (User Interface Layer), task 3 of 4.

### Current Status

- 14 out of 19 tasks COMPLETED
- Phase 4 Integration Layer: 3/3 COMPLETED
- Phase 5 User Interface Layer: 2/4 IN PROGRESS (Tasks 13, 14 done)

## Existing Infrastructure

The project has a complete alerting system at `app/services/alerting_system/`:

1. **models.py** - Has `NotificationChannelType` enum with WEBHOOK, EMAIL, SLACK, DISCORD
2. **notification_channels.py** - Has WebhookChannel, EmailChannel, SlackChannel, DiscordChannel
3. **NotificationDispatcher** - Dispatches to multiple channels
4. **user_settings.py** (Task 14) - Has NotificationSettings with `enable_telegram` and `telegram_chat_id`

## Implementation Steps

### 1. Update NotificationChannelType Enum

Add `TELEGRAM = "telegram"` to the `NotificationChannelType` enum in `app/services/alerting_system/models.py`.

### 2. Create TelegramChannel Class

Add `TelegramChannel` class to `app/services/alerting_system/notification_channels.py`:

- Implement `async send(self, target: NotificationTarget, payload: NotificationPayload) -> bool`
- Use Telegram Bot API: `https://api.telegram.org/bot{bot_token}/sendMessage`
- Support Markdown formatting with emojis by severity
- Extract bot_token and chat_id from target.headers or endpoint
- Handle errors gracefully

### 3. Register TelegramChannel in NotificationDispatcher

Update `NotificationDispatcher.__init__()` to include:
```python
NotificationChannelType.TELEGRAM: TelegramChannel()
```

### 4. Create TelegramBotHelper

Create `app/services/alerting_system/telegram_helper.py`:

- `test_bot_token(bot_token)` - Validate bot token via getMe API
- `get_chat_id(bot_token)` - Get chat_id from getUpdates API
- `send_test_message(bot_token, chat_id, message)` - Send test message
- `get_setup_instructions()` - Return setup instructions
- `setup_telegram_bot_interactive()` - Interactive setup helper

### 5. Create Setup Script

Create `scripts/setup_telegram.py`:

- Interactive CLI for Telegram bot setup
- Guides user through BotFather process
- Tests bot token
- Retrieves chat_id
- Sends test message
- Outputs YAML config snippet

### 6. Create UserConfigAdapter

Create `app/services/alerting_system/user_config_adapter.py`:

- `user_settings_to_notification_targets(settings)` - Convert UserSettings to NotificationTarget list
- Read credentials from environment variables for security
- Support both Telegram and Email channels

### 7. Create Tests

Create `tests/unit/alerting_system/test_telegram_channel.py`:

- Test successful send
- Test disabled channel
- Test missing bot token
- Test API error response
- Test connection error

Create `tests/unit/alerting_system/test_telegram_helper.py`:

- Test bot token validation (valid/invalid)
- Test get_chat_id
- Test send_test_message

### 8. Update __init__.py

Update `app/services/alerting_system/__init__.py` to export `TelegramChannel`.

### 9. Validate

- Make `scripts/setup_telegram.py` executable
- Compile all new files
- Run all tests
- Verify imports work
- Verify dispatcher has Telegram channel registered

## Deliverables

1. Modified: `app/services/alerting_system/models.py` - Add TELEGRAM to enum
2. Modified: `app/services/alerting_system/notification_channels.py` - Add TelegramChannel
3. Modified: `app/services/alerting_system/__init__.py` - Export TelegramChannel
4. Created: `app/services/alerting_system/telegram_helper.py`
5. Created: `app/services/alerting_system/user_config_adapter.py`
6. Created: `scripts/setup_telegram.py`
7. Created: `tests/unit/alerting_system/test_telegram_channel.py`
8. Created: `tests/unit/alerting_system/test_telegram_helper.py`

## Validation Checklist

- [ ] NotificationChannelType.TELEGRAM exists
- [ ] TelegramChannel implements NotificationChannel
- [ ] TelegramChannel registered in NotificationDispatcher
- [ ] TelegramBotHelper provides setup utilities
- [ ] setup_telegram.py script is executable
- [ ] All tests pass
- [ ] Integration with UserSettings works

## Next Task

After completion, proceed to Task 16 (Simple Dashboard) - the final task of Phase 5.
