from __future__ import annotations

import os
import typing as t
import pkgutil
import logging
from types import ModuleType
from typing import TYPE_CHECKING
from importlib import import_module

import pytest

if TYPE_CHECKING:
    from .models import FrameworkTestModel

    from _pytest.nodes import Item
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser


logger = logging.getLogger("bentoml.tests")

def pytest_addoption(parser: Parser):
    parser.addoption("--framework", action="store", default=None)
    parser.addoption(
        "--disable-tf-eager-execution",
        action="store_true",
        default=False,
        help="Disable TF eager execution",
    )


def pytest_configure(config: "Config") -> None:
    # We will inject marker documentation here.
    config.addinivalue_line(
        "markers",
        "requires_eager_execution: requires enable eager execution to run Tensorflow-based tests.",
    )


def pytest_collection_modifyitems(config: "Config", items: t.List["Item"]) -> None:
    if config.getoption("--disable-tf-eager-execution"):
        try:
            from tensorflow.python.framework.ops import disable_eager_execution

            disable_eager_execution()
        except ImportError:
            return

    requires_eager_execution = pytest.mark.skip(reason="Requires eager execution")
    for item in items:
        if "requires_eager_execution" in item.keywords:
            item.add_marker(requires_eager_execution)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    framework_name: str = t.cast(str, metafunc.config.getoption("framework"))

    if "framework" in metafunc.fixturenames and "test_model" in metafunc.fixturenames:
        metafunc.parametrize("framework,test_model", test_inputs(framework_name))
    elif "framework" in metafunc.fixturenames:
        metafunc.parametrize(
            "framework", [inp[0] for inp in test_inputs(framework_name)]
        )


def test_inputs(framework: str | None) -> list[tuple[ModuleType, FrameworkTestModel]]:
    if framework is None:
        frameworks = [
            name
            for _, name, _ in pkgutil.iter_modules(
                [os.path.join(os.path.dirname(__file__), "models")]
            )
        ]
    else:
        frameworks = [framework]

    input_modules: list[ModuleType] = []
    for framework_name in frameworks:
        try:
            input_modules.append(
                import_module(
                    f".{framework_name}", "tests.integration.frameworks.models"
                )
            )
        except ModuleNotFoundError as e:
            logger.warning(f"Failed to find test module for framework {framework_name} (tests.integration.frameworks.models.{framework_name})")

    return [
        (module.framework, _model)
        for module in input_modules
        for _model in module.models
    ]
