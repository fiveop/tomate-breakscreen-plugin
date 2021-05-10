import random
from typing import Iterator

import pytest
from gi.repository import Gtk
from wiring import Graph

from tomate.pomodoro import Bus, Config, ConfigPayload, Events, Session, SessionType, TimerPayload
from tomate.ui.testing import Q, create_session_end_payload, create_session_payload, run_loop_for

SECTION_NAME = "break_screen"
SKIP_BREAK_OPTION = "skip_break"
AUTO_START_OPTION = "auto_start"


@pytest.fixture
def bus() -> Bus:
    return Bus()


@pytest.fixture
def config(bus, tmpdir) -> Config:
    instance = Config(bus)
    tmp_path = tmpdir.mkdir("tomate").join("tomate.config")
    instance.config_path = lambda: tmp_path.strpath
    return instance


@pytest.fixture
def graph() -> Graph:
    instance = Graph()
    instance.register_instance(Graph, instance)
    return instance


@pytest.fixture
def session(mocker):
    return mocker.Mock(spec=Session)


@pytest.fixture
def plugin(bus, config, graph, session):
    graph.providers.clear()
    graph.register_instance("tomate.bus", bus)
    graph.register_instance("tomate.config", config)
    graph.register_instance("tomate.session", session)

    import breakscreen_plugin

    instance = breakscreen_plugin.BreakScreenPlugin()
    instance.configure(bus, graph)
    return instance


def none(values: Iterator) -> bool:
    return all([value is False for value in values])


def label_text(countdown: str, plugin) -> bool:
    return len(plugin.screens) > 0 and all(
        [Q.select(screen.widget, Q.props("name", "countdown")).get_text() == countdown for screen in plugin.screens]
    )


class TestPlugin:
    @pytest.mark.parametrize("session_type", [SessionType.SHORT_BREAK, SessionType.LONG_BREAK])
    def test_shows_screens_when_session_starts(self, session_type, bus, plugin):
        plugin.activate()

        payload = create_session_payload(type=session_type)
        bus.send(Events.SESSION_START, payload=payload)

        assert all([screen.widget.props.visible for screen in plugin.screens])
        assert label_text(payload.countdown, plugin)

    def test_do_no_show_screen_when_plugin_is_deactivated(self, bus, plugin):
        plugin.activate()

        payload = create_session_payload(type=SessionType.SHORT_BREAK)
        bus.send(Events.SESSION_START, payload=payload)

        plugin.deactivate()

        assert none([screen.widget.props.visible for screen in plugin.screens])

    def test_do_not_show_screen_when_the_session_is_a_pomodoro(self, bus, plugin):
        plugin.activate()

        payload = create_session_payload(type=SessionType.POMODORO)
        bus.send(Events.SESSION_START, payload=payload)

        assert none([screen.widget.props.visible for screen in plugin.screens])

    def test_starts_session_when_auto_start_option_is_enabled(self, bus, config, plugin, session):
        config.set(SECTION_NAME, AUTO_START_OPTION, "true")

        plugin.activate()

        payload = create_session_end_payload(type=SessionType.SHORT_BREAK, previous="")
        bus.send(Events.SESSION_END, payload=payload)

        run_loop_for(1)

        session.start.assert_called_once()

    def test_do_not_start_when_auto_start_is_disabled(self, bus, config, plugin, session):
        config.set(SECTION_NAME, AUTO_START_OPTION, "false")

        plugin.activate()

        payload = create_session_end_payload(type=SessionType.SHORT_BREAK, previous="")
        bus.send(Events.SESSION_END, payload=payload)

        session.start.assert_not_called()

        assert none([screen.widget.props.visible for screen in plugin.screens])

    def test_hides_screens_when_session_is_interrupted(self, bus, plugin):
        plugin.activate()

        bus.send(Events.SESSION_START, payload=create_session_payload(type=SessionType.SHORT_BREAK))
        bus.send(Events.SESSION_INTERRUPT, payload=create_session_payload())

        assert none([screen.widget.props.visible for screen in plugin.screens])

    def test_do_not_start_session_when_is_not_a_break(self, bus, config, plugin, session):
        config.set(SECTION_NAME, AUTO_START_OPTION, "True")
        plugin.activate()

        for screen in plugin.screens:
            screen.widget.show()

        payload = create_session_end_payload(type=SessionType.POMODORO, previous="")
        bus.send(Events.SESSION_END, payload=payload)

        session.start.assert_not_called()

        assert none([screen.widget.props.visible for screen in plugin.screens])

    @pytest.mark.parametrize(
        "action,option,initial,value, want",
        [
            ("set", AUTO_START_OPTION, "false", "true", True),
            ("remove", AUTO_START_OPTION, "true", "", False),
            ("set", SKIP_BREAK_OPTION, "false", "true", True),
            ("remove", SKIP_BREAK_OPTION, "true", "", False),
        ],
    )
    def test_listen_for_break_screen_settings_change(self, action, option, initial, value, want, bus, config, plugin):
        config.set(SECTION_NAME, option, initial)
        plugin.activate()

        payload = ConfigPayload(action, SECTION_NAME, option, value)
        bus.send(Events.CONFIG_CHANGE, payload=payload)

        assert all([screen.options[option] == want for screen in plugin.screens])

    def test_updates_screens_countdown(self, bus, plugin):
        plugin.activate()

        time_left = random.randint(1, 100)

        payload = TimerPayload(time_left=time_left, duration=150)
        bus.send(Events.TIMER_UPDATE, payload=payload)

        assert label_text(payload.countdown, plugin)


class TestSettingsWindow:
    def test_options_labels(self, plugin):
        dialog = plugin.settings_window(Gtk.Window())

        assert Q.select(dialog.widget, Q.props("label", "Auto start:")) is not None
        assert Q.select(dialog.widget, Q.props("label", "Skip break:")) is not None

    def test_with_all_options_enabled(self, config, plugin):
        config.set(SECTION_NAME, AUTO_START_OPTION, "true")
        config.set(SECTION_NAME, SKIP_BREAK_OPTION, "true")

        dialog = plugin.settings_window(Gtk.Window())

        assert Q.select(dialog.widget, Q.props("name", AUTO_START_OPTION)).props.active is True
        assert Q.select(dialog.widget, Q.props("name", SKIP_BREAK_OPTION)).props.active is True

    def test_with_all_options_disabled(self, config, plugin):
        config.remove(SECTION_NAME, AUTO_START_OPTION)
        config.remove(SECTION_NAME, SKIP_BREAK_OPTION)

        dialog = plugin.settings_window(Gtk.Window())

        assert Q.select(dialog.widget, Q.props("name", AUTO_START_OPTION)).props.active is False
        assert Q.select(dialog.widget, Q.props("name", SKIP_BREAK_OPTION)).props.active is False

    def test_change_options(self, config, plugin):
        config.remove(SECTION_NAME, AUTO_START_OPTION)
        config.remove(SECTION_NAME, SKIP_BREAK_OPTION)

        dialog = plugin.settings_window(Gtk.Window())

        Q.select(dialog.widget, Q.props("name", AUTO_START_OPTION)).props.active = True
        Q.select(dialog.widget, Q.props("name", SKIP_BREAK_OPTION)).props.active = True

        config.load()

        assert config.get_bool(SECTION_NAME, AUTO_START_OPTION) is True
        assert config.get_bool(SECTION_NAME, SKIP_BREAK_OPTION) is True
