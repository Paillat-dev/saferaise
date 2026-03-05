"""Tests for _errors.py."""

from saferaise._errors import NameCollisionError, NotEnteredError, SafeRaiseError, UnwatchedRaiseError


class TestSafeRaiseError:
    def test_inherits_from_base_exception(self):
        assert issubclass(SafeRaiseError, BaseException)

    def test_is_not_exception(self):
        assert not issubclass(SafeRaiseError, Exception)


class TestUnwatchedRaiseError:
    def test_inherits_from_saferaise_error(self):
        assert issubclass(UnwatchedRaiseError, SafeRaiseError)

    def test_attributes(self):
        err = UnwatchedRaiseError("my_func", (ValueError, TypeError), TypeError)
        assert err.func_name == "my_func"
        assert err.declared == (ValueError, TypeError)
        assert err.missing is TypeError

    def test_message_single_exception(self):
        err = UnwatchedRaiseError("fn", (ValueError,), ValueError)
        assert "fn" in str(err)
        assert "ValueError" in str(err)

    def test_message_multiple_exceptions(self):
        err = UnwatchedRaiseError("fn", (ValueError, TypeError), TypeError)
        msg = str(err)
        assert "ValueError" in msg
        assert "TypeError" in msg


class TestNotEnteredError:
    def test_inherits_from_saferaise_error(self):
        assert issubclass(NotEnteredError, SafeRaiseError)

    def test_attributes(self):
        err = NotEnteredError("watch_exceptions")
        assert err.context_name == "watch_exceptions"

    def test_message(self):
        err = NotEnteredError("watch_exceptions")
        assert "watch_exceptions" in str(err)
        assert "not entered" in str(err)


class TestNameCollisionError:
    def test_inherits_from_saferaise_error(self):
        assert issubclass(NameCollisionError, SafeRaiseError)

    def test_attributes(self):
        err = NameCollisionError("my_module", "_saferaise_watch_exceptions")
        assert err.module_name == "my_module"
        assert err.key == "_saferaise_watch_exceptions"

    def test_message(self):
        err = NameCollisionError("my_module", "_key")
        msg = str(err)
        assert "my_module" in msg
        assert "_key" in msg
