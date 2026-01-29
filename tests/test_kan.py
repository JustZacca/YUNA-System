"""
Tests for kan.py - Telegram bot interface for YUNA-System.

This module tests:
    - Kan initialization
    - Removal keyboard building
    - Authorization checks
    - Error handler behavior
    - Command handlers with mocked Telegram
"""

import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKanInitialization:
    """Tests for Kan class initialization."""

    def test_kan_initialization(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan initializes correctly with required attributes."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                assert kan.airi is not None
                assert kan.AUTHORIZED_USER_ID == int(mock_env["TELEGRAM_CHAT_ID"])
                assert kan.LINK == 1
                assert kan.SEARCH_NAME == 0
                assert kan.anime_id_map == {}
                assert kan.anime_link is None
                assert kan.missing_episodes_list == []
                assert kan.selected_anime_for_removal == {}

    def test_kan_has_miko_instance(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan has a Miko instance for anime operations."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                assert kan.miko_instance is not None

    def test_kan_has_logger(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan has a configured logger."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                assert kan.logger is not None


class TestBuildRemovalKeyboard:
    """Tests for _build_removal_keyboard method."""

    def test_build_removal_keyboard_empty_list(self, mock_env, temp_db, mock_httpx):
        """Verify that keyboard is built correctly with empty anime list."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                user_id = 123456789

                keyboard = kan._build_removal_keyboard(user_id)

                # Should have action buttons even with empty list
                assert keyboard is not None
                assert hasattr(keyboard, "inline_keyboard")

    def test_build_removal_keyboard_with_anime(self, mock_env, temp_db, mock_httpx):
        """Verify that keyboard includes anime buttons."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                user_id = 123456789

                # Add test anime
                kan.airi.add_anime(
                    name="Test Anime",
                    link="/play/test.12345",
                    last_update="2024-01-15 10:30:00",
                    numero_episodi=12,
                )

                keyboard = kan._build_removal_keyboard(user_id)

                # Keyboard should contain anime name
                keyboard_texts = []
                for row in keyboard.inline_keyboard:
                    for button in row:
                        keyboard_texts.append(button.text)

                assert any("Test Anime" in text for text in keyboard_texts)

    def test_build_removal_keyboard_shows_selection_state(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that keyboard shows correct selection checkbox."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                user_id = 123456789

                # Add test anime
                kan.airi.add_anime(
                    name="Selected Anime",
                    link="/play/selected.12345",
                    last_update="2024-01-15 10:30:00",
                    numero_episodi=12,
                )

                # Set as selected
                kan.selected_anime_for_removal[user_id] = {"Selected Anime"}

                keyboard = kan._build_removal_keyboard(user_id)

                # Find the anime button
                for row in keyboard.inline_keyboard:
                    for button in row:
                        if "Selected Anime" in button.text:
                            # Should have checkmark
                            assert "\u2705" in button.text  # Green checkmark

    def test_build_removal_keyboard_has_action_buttons(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that keyboard has select all/deselect and confirm/cancel buttons."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                user_id = 123456789

                keyboard = kan._build_removal_keyboard(user_id)

                callback_data_list = []
                for row in keyboard.inline_keyboard:
                    for button in row:
                        callback_data_list.append(button.callback_data)

                assert "removal_select_all" in callback_data_list
                assert "removal_deselect_all" in callback_data_list
                assert "removal_confirm" in callback_data_list
                assert "removal_cancel" in callback_data_list


class TestAuthorizationChecks:
    """Tests for authorization checks in various handlers."""

    @pytest.mark.asyncio
    async def test_start_unauthorized_user(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users are rejected from /start."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                # Create mock update with unauthorized user
                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = 999999  # Different from authorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.start(update, context)

                # Should reply with unauthorized message
                update.message.reply_text.assert_called_once()
                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_start_authorized_user(self, mock_env, temp_db, mock_httpx):
        """Verify that authorized users receive welcome message."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                # Create mock update with authorized user
                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.start(update, context)

                # Should reply with welcome message
                update.message.reply_text.assert_called_once()
                call_args = update.message.reply_text.call_args[0][0]
                assert "benvenuto" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lista_anime_unauthorized(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users cannot list anime."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = 999999  # Unauthorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.lista_anime(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_aggiungi_anime_unauthorized(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users cannot add anime."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan
                from telegram.ext import ConversationHandler

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = 999999  # Unauthorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                result = await kan.aggiungi_anime(update, context)

                assert result == ConversationHandler.END
                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_stop_bot_unauthorized(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users cannot stop the bot."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = 999999  # Unauthorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.stop_bot(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()


class TestErrorHandler:
    """Tests for error_handler method."""

    @pytest.mark.asyncio
    async def test_error_handler_does_not_crash(self, mock_env, temp_db, mock_httpx):
        """Verify that error_handler handles errors without crashing."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                context = MagicMock()
                context.error = ValueError("Test error")
                context.bot = MagicMock()
                context.bot.send_message = AsyncMock()

                # Should not raise any exception
                try:
                    await kan.error_handler(update, context)
                    error_raised = False
                except Exception:
                    error_raised = True

                assert error_raised is False

    @pytest.mark.asyncio
    async def test_error_handler_notifies_user(self, mock_env, temp_db, mock_httpx):
        """Verify that error_handler sends notification to authorized user."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                context = MagicMock()
                context.error = ValueError("Test error message")
                context.bot = MagicMock()
                context.bot.send_message = AsyncMock()

                await kan.error_handler(update, context)

                # Should send message to authorized user
                context.bot.send_message.assert_called_once()
                call_kwargs = context.bot.send_message.call_args[1]
                assert call_kwargs["chat_id"] == kan.AUTHORIZED_USER_ID

    @pytest.mark.asyncio
    async def test_error_handler_handles_notification_failure(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that error_handler handles notification failure gracefully."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                context = MagicMock()
                context.error = ValueError("Original error")
                context.bot = MagicMock()
                context.bot.send_message = AsyncMock(
                    side_effect=Exception("Notification failed")
                )

                # Should not raise even if notification fails
                try:
                    await kan.error_handler(update, context)
                    error_raised = False
                except Exception:
                    error_raised = True

                assert error_raised is False


class TestReceiveLink:
    """Tests for receive_link handler."""

    @pytest.mark.asyncio
    async def test_receive_link_valid_animeworld(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that valid AnimeWorld links are processed."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                mock_episode = MagicMock()
                mock_episode.number = 1
                mock_episode.fileInfo.return_value = {"last_modified": "2024-01-15"}

                mock_anime = MagicMock()
                mock_anime.getName.return_value = "Valid Anime"
                mock_anime.getCover.return_value = "https://example.com/cover.jpg"
                mock_anime.getEpisodes.return_value = [mock_episode]
                mock_aw.Anime.return_value = mock_anime

                from kan import Kan
                from telegram.ext import ConversationHandler

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.text = "https://animeworld.tv/play/valid-anime.12345"
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                with patch("miko.requests") as mock_requests:
                    mock_response = MagicMock()
                    mock_response.iter_content.return_value = [b"image"]
                    mock_response.raise_for_status = MagicMock()
                    mock_requests.get.return_value = mock_response

                    result = await kan.receive_link(update, context)

                assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_receive_link_invalid_url(self, mock_env, temp_db, mock_httpx):
        """Verify that invalid URLs are rejected."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan
                from telegram.ext import ConversationHandler

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.text = "not a valid url"
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                result = await kan.receive_link(update, context)

                assert result == ConversationHandler.END
                # Should warn about invalid link
                call_args = update.message.reply_text.call_args[0][0]
                assert "non sembra provenire" in call_args.lower() or "non" in call_args.lower()


class TestListaAnime:
    """Tests for lista_anime handler."""

    @pytest.mark.asyncio
    async def test_lista_anime_empty(self, mock_env, temp_db, mock_httpx):
        """Verify that empty anime list shows appropriate message."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.lista_anime(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "vuota" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lista_anime_with_data(self, mock_env, temp_db, mock_httpx):
        """Verify that anime list is displayed correctly."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                # Add anime
                kan.airi.add_anime(
                    name="Listed Anime",
                    link="/play/listed.12345",
                    last_update="2024-01-15 10:30:00",
                    numero_episodi=12,
                )

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.lista_anime(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "Listed Anime" in call_args


class TestCancelHandler:
    """Tests for cancel handler."""

    @pytest.mark.asyncio
    async def test_cancel_ends_conversation(self, mock_env, temp_db, mock_httpx):
        """Verify that cancel returns ConversationHandler.END."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan
                from telegram.ext import ConversationHandler

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                result = await kan.cancel(update, context)

                assert result == ConversationHandler.END
                update.message.reply_text.assert_called_once()


class TestRimuoviAnime:
    """Tests for rimuovi_anime handler."""

    @pytest.mark.asyncio
    async def test_rimuovi_anime_unauthorized(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users cannot remove anime."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = 999999  # Unauthorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.rimuovi_anime(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_rimuovi_anime_empty_list(self, mock_env, temp_db, mock_httpx):
        """Verify that empty anime list shows appropriate message."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.rimuovi_anime(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "vuota" in call_args.lower()

    @pytest.mark.asyncio
    async def test_rimuovi_anime_shows_keyboard(self, mock_env, temp_db, mock_httpx):
        """Verify that removal menu shows keyboard with anime."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                # Add anime
                kan.airi.add_anime(
                    name="Removable Anime",
                    link="/play/removable.12345",
                    last_update="2024-01-15 10:30:00",
                    numero_episodi=12,
                )

                update = MagicMock()
                update.message = MagicMock()
                update.effective_user = MagicMock()
                update.effective_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.rimuovi_anime(update, context)

                # Should be called with reply_markup
                call_kwargs = update.message.reply_text.call_args[1]
                assert "reply_markup" in call_kwargs


class TestKeyboardStopBot:
    """Tests for keyboard_stop_bot method."""

    def test_keyboard_stop_bot_sends_signal(self, mock_env, temp_db, mock_httpx):
        """Verify that keyboard_stop_bot sends SIGINT signal."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                with patch("os.kill") as mock_kill:
                    import signal

                    kan.keyboard_stop_bot()

                    mock_kill.assert_called_once()
                    # Should send SIGINT to current process
                    call_args = mock_kill.call_args[0]
                    assert call_args[1] == signal.SIGINT


class TestDownloadTask:
    """Tests for download_task helper method."""

    @pytest.mark.asyncio
    async def test_download_task_empty_list(self, mock_env, temp_db, mock_httpx):
        """Verify that download_task returns False for empty list."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                kan.missing_episodes_list = []

                result = await kan.download_task()

                assert result is False

    @pytest.mark.asyncio
    async def test_download_task_with_episodes(
        self, mock_env, temp_db, temp_download_folder, mock_httpx, monkeypatch
    ):
        """Verify that download_task calls miko download."""
        monkeypatch.setenv("DESTINATION_FOLDER", temp_download_folder)

        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()
                kan.missing_episodes_list = [1, 2, 3]
                kan.miko_instance.downloadEpisodes = AsyncMock(return_value=True)

                result = await kan.download_task()

                assert result is True
                kan.miko_instance.downloadEpisodes.assert_called_once_with([1, 2, 3])


class TestHandleRemovalToggle:
    """Tests for handle_removal_toggle callback handler."""

    @pytest.mark.asyncio
    async def test_handle_removal_toggle_selects_anime(
        self, mock_env, temp_db, mock_httpx
    ):
        """Verify that toggling selects/deselects anime."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                # Add anime
                kan.airi.add_anime(
                    name="Toggle Anime",
                    link="/play/toggle.12345",
                    last_update="2024-01-15 10:30:00",
                    numero_episodi=12,
                )

                user_id = kan.AUTHORIZED_USER_ID
                kan.selected_anime_for_removal[user_id] = set()

                update = MagicMock()
                update.callback_query = MagicMock()
                update.callback_query.from_user = MagicMock()
                update.callback_query.from_user.id = user_id
                update.callback_query.data = "removal_toggle|Toggle Anime"
                update.callback_query.answer = AsyncMock()
                update.callback_query.edit_message_reply_markup = AsyncMock()

                context = MagicMock()

                await kan.handle_removal_toggle(update, context)

                # Anime should now be selected
                assert "Toggle Anime" in kan.selected_anime_for_removal[user_id]

    @pytest.mark.asyncio
    async def test_handle_removal_cancel(self, mock_env, temp_db, mock_httpx):
        """Verify that cancel clears selection and shows message."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                user_id = kan.AUTHORIZED_USER_ID
                kan.selected_anime_for_removal[user_id] = {"Some Anime"}

                update = MagicMock()
                update.callback_query = MagicMock()
                update.callback_query.from_user = MagicMock()
                update.callback_query.from_user.id = user_id
                update.callback_query.data = "removal_cancel"
                update.callback_query.answer = AsyncMock()
                update.callback_query.edit_message_text = AsyncMock()

                context = MagicMock()

                await kan.handle_removal_toggle(update, context)

                # Selection should be cleared
                assert user_id not in kan.selected_anime_for_removal


class TestAggiornaLibreria:
    """Tests for aggiorna_libreria handler."""

    @pytest.mark.asyncio
    async def test_aggiorna_libreria_unauthorized(self, mock_env, temp_db, mock_httpx):
        """Verify that unauthorized users cannot update library."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = 999999  # Unauthorized
                update.message.reply_text = AsyncMock()

                context = MagicMock()

                await kan.aggiorna_libreria(update, context)

                call_args = update.message.reply_text.call_args[0][0]
                assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_aggiorna_libreria_triggers_job(self, mock_env, temp_db, mock_httpx):
        """Verify that aggiorna_libreria triggers the update job."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()

                from kan import Kan

                kan = Kan()

                update = MagicMock()
                update.message = MagicMock()
                update.message.from_user = MagicMock()
                update.message.from_user.id = kan.AUTHORIZED_USER_ID
                update.message.reply_text = AsyncMock()

                context = MagicMock()
                context.application = MagicMock()
                context.application.job_queue = MagicMock()
                context.application.job_queue.run_once = MagicMock()

                await kan.aggiorna_libreria(update, context)

                # Should trigger job queue
                context.application.job_queue.run_once.assert_called_once()

                # Should confirm to user
                call_args = update.message.reply_text.call_args[0][0]
                assert "aggiornamento" in call_args.lower()


# ==================== STREAMINGCOMMUNITY COMMANDS TESTS ====================

class TestKanSCInitialization:
    """Tests for StreamingCommunity-related initialization in Kan."""

    def test_kan_has_miko_sc_instance(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan has a MikoSC instance."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    # Must patch Database before Airi imports it
                    from database import Database
                    with patch.object(Database, "_init_database", return_value=None):
                        with patch.object(Database, "get_all_anime", return_value=[]):
                            from kan import Kan
                            kan = Kan()
                            assert kan.miko_sc is not None

    def test_kan_has_sc_search_results_dict(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan has SC search results dictionary."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from database import Database
                    with patch.object(Database, "_init_database", return_value=None):
                        with patch.object(Database, "get_all_anime", return_value=[]):
                            from kan import Kan
                            kan = Kan()
                            assert kan.sc_search_results == {}
                            assert kan.sc_current_series == {}

    def test_kan_has_sc_conversation_states(self, mock_env, temp_db, mock_httpx):
        """Verify that Kan has SC conversation states."""
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    from database import Database
                    with patch.object(Database, "_init_database", return_value=None):
                        with patch.object(Database, "get_all_anime", return_value=[]):
                            from kan import Kan
                            kan = Kan()
                            assert hasattr(kan, "SC_SEARCH")
                            assert hasattr(kan, "SC_SELECT_SEASON")


class TestCercaSC:
    """Tests for /cerca_sc command."""

    @pytest.mark.asyncio
    async def test_cerca_sc_unauthorized(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that unauthorized users cannot search SC."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = 999999  # Unauthorized
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        await kan.cerca_sc(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cerca_sc_authorized_prompts_search(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that authorized users get search prompt."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        result = await kan.cerca_sc(update, context)

                        # Should return SC_SEARCH state
                        assert result == kan.SC_SEARCH
                        update.message.reply_text.assert_called_once()


class TestReceiveSCSearch:
    """Tests for SC search result handling."""

    @pytest.mark.asyncio
    async def test_receive_sc_search_no_results(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that no results message is shown."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.text = "nonexistent query"
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "search", return_value=[]):
                            result = await kan.receive_sc_search(update, context)

                        # Should stay in search state
                        assert result == kan.SC_SEARCH
                        call_args = update.message.reply_text.call_args[0][0]
                        assert "nessun risultato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_sc_search_with_results(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that search results show keyboard."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan
                        from streamingcommunity import MediaItem
                        from telegram.ext import ConversationHandler

                        kan = Kan()
                        user_id = kan.AUTHORIZED_USER_ID

                        mock_results = [
                            MediaItem(id=1, name="Test Movie", slug="test-movie", type="movie", year="2024"),
                            MediaItem(id=2, name="Test Series", slug="test-series", type="tv", year="2020"),
                        ]

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = user_id
                        update.message = MagicMock()
                        update.message.text = "test query"
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "search", return_value=mock_results):
                            result = await kan.receive_sc_search(update, context)

                        # Should end conversation and show keyboard
                        assert result == ConversationHandler.END
                        assert user_id in kan.sc_search_results
                        assert len(kan.sc_search_results[user_id]) == 2

                        # Should have reply_markup
                        call_kwargs = update.message.reply_text.call_args[1]
                        assert "reply_markup" in call_kwargs


class TestListaSerie:
    """Tests for /lista_serie command."""

    @pytest.mark.asyncio
    async def test_lista_serie_unauthorized(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that unauthorized users cannot list series."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = 999999
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        await kan.lista_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lista_serie_empty(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that empty series list shows appropriate message."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "get_library_series", return_value=[]):
                            await kan.lista_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "nessuna serie" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lista_serie_with_data(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that series list is displayed correctly."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        # Mock library series
                        mock_series = [
                            {"name": "Test Series", "year": "2020", "episodi_scaricati": 10, "numero_episodi": 20}
                        ]

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "get_library_series", return_value=mock_series):
                            await kan.lista_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "Test Series" in call_args


class TestListaFilm:
    """Tests for /lista_film command."""

    @pytest.mark.asyncio
    async def test_lista_film_unauthorized(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that unauthorized users cannot list films."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = 999999
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        await kan.lista_film(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_lista_film_empty(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that empty film list shows appropriate message."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "get_library_films", return_value=[]):
                            await kan.lista_film(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "nessun film" in call_args.lower()


class TestRimuoviSerie:
    """Tests for /rimuovi_serie command."""

    @pytest.mark.asyncio
    async def test_rimuovi_serie_unauthorized(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that unauthorized users cannot remove series."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = 999999
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        await kan.rimuovi_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_rimuovi_serie_empty_list(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that empty series list shows message."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "get_library_series", return_value=[]):
                            await kan.rimuovi_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "nessuna serie" in call_args.lower()


class TestBuildSeriesRemovalKeyboard:
    """Tests for _build_series_removal_keyboard method."""

    def test_build_series_removal_keyboard_with_series(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that keyboard includes series buttons."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()
                        user_id = kan.AUTHORIZED_USER_ID

                        # Mock get_library_series
                        mock_series = [{"name": "Keyboard Test Series"}]
                        with patch.object(kan.miko_sc, "get_library_series", return_value=mock_series):
                            keyboard = kan._build_series_removal_keyboard(user_id)

                        # Find series in keyboard
                        keyboard_texts = []
                        for row in keyboard.inline_keyboard:
                            for button in row:
                                keyboard_texts.append(button.text)

                        assert any("Keyboard Test Series" in text for text in keyboard_texts)

    def test_build_series_removal_keyboard_has_action_buttons(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify keyboard has action buttons."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()
                        user_id = kan.AUTHORIZED_USER_ID

                        with patch.object(kan.miko_sc, "get_library_series", return_value=[]):
                            keyboard = kan._build_series_removal_keyboard(user_id)

                        callback_data_list = []
                        for row in keyboard.inline_keyboard:
                            for button in row:
                                callback_data_list.append(button.callback_data)

                        assert "sc_removal_select_all" in callback_data_list
                        assert "sc_removal_deselect_all" in callback_data_list
                        assert "sc_removal_confirm" in callback_data_list
                        assert "sc_removal_cancel" in callback_data_list


class TestAggiornaSerie:
    """Tests for /aggiorna_serie command."""

    @pytest.mark.asyncio
    async def test_aggiorna_serie_unauthorized(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that unauthorized users cannot update series."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = 999999
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        await kan.aggiorna_serie(update, context)

                        call_args = update.message.reply_text.call_args[0][0]
                        assert "non sei autorizzato" in call_args.lower()

    @pytest.mark.asyncio
    async def test_aggiorna_serie_no_updates(self, mock_env, temp_db, mock_httpx, monkeypatch):
        """Verify that message is shown when no updates available."""
        monkeypatch.setenv("DATABASE_PATH", temp_db)
        with patch("airi.httpx", mock_httpx):
            with patch("miko.aw") as mock_aw:
                mock_aw.SES = MagicMock()
                with patch("streamingcommunity.httpx"):
                    with patch("miko.Database") as mock_db:
                        mock_db.return_value = MagicMock()
                        from kan import Kan

                        kan = Kan()

                        update = MagicMock()
                        update.effective_user = MagicMock()
                        update.effective_user.id = kan.AUTHORIZED_USER_ID
                        update.message = MagicMock()
                        update.message.reply_text = AsyncMock()

                        context = MagicMock()

                        with patch.object(kan.miko_sc, "check_and_download_new_episodes", new_callable=AsyncMock, return_value={}):
                            await kan.aggiorna_serie(update, context)

                        # Should show "all updated" message
                        calls = update.message.reply_text.call_args_list
                        messages = [call[0][0].lower() for call in calls]
                        assert any("aggiornate" in msg for msg in messages)
