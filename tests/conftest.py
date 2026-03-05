"""Shared fixtures for saferaise tests."""

import pytest


class CustomError(Exception):
    """A custom exception for testing."""


class AnotherError(Exception):
    """Another custom exception for testing."""


class ChildError(CustomError):
    """A child of CustomError for subclass testing."""


@pytest.fixture
def custom_error():
    return CustomError


@pytest.fixture
def another_error():
    return AnotherError


@pytest.fixture
def child_error():
    return ChildError
