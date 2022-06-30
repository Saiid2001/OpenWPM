""" This file aims to demonstrate how to write custom commands in OpenWPM
Steps to have a custom command run as part of a CommandSequence
1. Create a class that derives from BaseCommand
2. Implement the execute method
3. Append it to the CommandSequence
4. Execute the CommandSequence
"""

import json
import logging
import os
from pathlib import Path

from openwpm.commands.types import BaseCommand
from openwpm.config import BrowserParams, ManagerParams
from openwpm.socket_interface import ClientSocket
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..utilities.path import path_from_home

UBLOCK_XPI_PATH = os.environ.get(
    "UBLOCK_XPI_PATH",
    str(Path(os.path.realpath(__file__)).parent) + "/assets/ublock_origin-1.43.0.xpi",
)

UBLOCK_CONF_PATH = path_from_home(
    "~/.mozilla/managed-storage/uBlock0@raymondhill.net.json"
)


class NoAddonException(Exception):
    """Exception raised if the Ublock Addon is not loaded"""


class AddonSetupCommand(BaseCommand):
    """loads the ublock command"""

    def __init__(self, path=UBLOCK_XPI_PATH) -> None:
        self.logger = logging.getLogger("openwpm")
        self.addon_path = path

    # While this is not strictly necessary, we use the repr of a command for logging
    # So not having a proper repr will make your logs a lot less useful
    def __repr__(self) -> str:
        return "AddonSetupCommand"

    # Have a look at openwpm.commands.types.BaseCommand.execute to see
    # an explanation of each parameter
    def execute(
        self,
        webdriver: Firefox,
        browser_params: BrowserParams,
        manager_params: ManagerParams,
        extension_socket: ClientSocket,
    ) -> None:
        webdriver.install_addon(self.addon_path)
        self.logger.info("Loaded Ublock Origin Extension")


def get_addon_uuid(webdriver: Firefox) -> str:
    """gets the addon uuid from the browser
    Args:
        webdriver (Firefox)
    Raises:
        NoAddonException
    Returns:
        str: the uuid of the addon. ex: "moz-extension://5df5ca6d-ddd4-4a0f-acf3-665a2dbf2f98"
    """
    webdriver.get("about:devtools-toolbox?id=uBlock0%40raymondhill.net&type=extension")
    title = webdriver.find_element(By.TAG_NAME, "window").get_attribute("title")

    # if the document has a title and it has error it is the error page
    if title and "error" in title:
        raise NoAddonException()

    webdriver.get("about:debugging#/runtime/this-firefox")

    WebDriverWait(webdriver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[title='uBlock Origin']"))
    )

    url = webdriver.execute_script(
        'return document.querySelector("[title=\'uBlock Origin\']").parentElement.querySelector("a").href'
    )

    url = url.replace("/manifest.json", "")

    return url


class AddonCheckAndUUIDCommand(BaseCommand):
    """loads the ublock command"""

    def __init__(self) -> None:
        self.logger = logging.getLogger("openwpm")

    # While this is not strictly necessary, we use the repr of a command for logging
    # So not having a proper repr will make your logs a lot less useful
    def __repr__(self) -> str:
        return "AddonCheckAndUUIDCommand"

    # Have a look at openwpm.commands.types.BaseCommand.execute to see
    # an explanation of each parameter
    def execute(
        self,
        webdriver: Firefox,
        browser_params: BrowserParams,
        manager_params: ManagerParams,
        extension_socket: ClientSocket,
    ) -> None:

        try:
            url = get_addon_uuid(webdriver=webdriver)
            webdriver.extra = {"ublock-uuid": url}
            self.logger.info("UBlock installed @ %s", url)
        except NoAddonException:
            self.logger.error("UBlock Not installed")
        except Exception:
            self.logger.error("An error occured")


def load_filter_list_from_file(path: Path):
    """loads a filterlist from a file path to the Ublock Addon configuration file
    Args:
        path (Path): path to the filterlist file
    """

    with open(path, "r", encoding="utf-8") as f:
        rules = f.read()

    # add a title for checking equality later on
    rules = f"#--filter-path={path}\n\n" + rules

    load_filter_list(rules)


def load_filter_list(rules: str):
    """loads the rules provided to the Ublock Addon configuration file
    Args:
        rules (str): rules seperated by new lines
    """

    with open(UBLOCK_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    settings = json.loads(conf["data"]["adminSettings"])
    settings["userFilters"] = rules
    conf["data"]["adminSettings"] = json.dumps(settings)

    with open(UBLOCK_CONF_PATH, "w", encoding="utf-8") as f:
        json.dump(conf, f)


def empty_filter_list():
    """empties the Ublock Addon config file from filter rules."""
    with open(UBLOCK_CONF_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)

    settings = json.loads(conf["data"]["adminSettings"])
    settings["userFilters"] = ""
    conf["data"]["adminSettings"] = json.dumps(settings)

    with open(UBLOCK_CONF_PATH, "w", encoding="utf-8") as f:
        json.dump(conf, f)


class FilterListLoadCommand(BaseCommand):
    """loads the filterlist command"""

    def __init__(self, path=None, rules=None) -> None:
        self.logger = logging.getLogger("openwpm")
        self.path = path if path[0] != "~" else path_from_home(path)
        self.rules = rules

        assert (
            not self.path or not self.rules
        ), "Cannot load from a file path and from rules string at the same time. Remove the file path or rules arguments."

        self.is_file = self.path is not None

    # While this is not strictly necessary, we use the repr of a command for logging
    # So not having a proper repr will make your logs a lot less useful
    def __repr__(self) -> str:
        return "FilterListLoadCommand"

    # Have a look at openwpm.commands.types.BaseCommand.execute to see
    # an explanation of each parameter
    def execute(
        self,
        webdriver: Firefox,
        browser_params: BrowserParams,
        manager_params: ManagerParams,
        extension_socket: ClientSocket,
    ) -> None:

        if self.is_file:
            load_filter_list_from_file(self.path)
        else:
            load_filter_list(self.rules)

        # reinstall ublocker
        webdriver.uninstall_addon("uBlock0@raymondhill.net")
        webdriver.install_addon(str(Path(UBLOCK_XPI_PATH).absolute()))
        uuid = get_addon_uuid(webdriver)
        webdriver.extra = {"ublock-uuid": uuid}

        # get the filters page
        webdriver.get(
            f"{webdriver.extra['ublock-uuid']}/dashboard.html#1p-filters.html"
        )

        webdriver.implicitly_wait(2)

        # get the filter list loaded by the extension
        loaded_fl = webdriver.execute_async_script(
            """var done = arguments[0];
            vAPI.messaging.send('dashboard', {
                what: 'readUserFilters',
            }).then(x=>done(x));"""
        )

        # get only the path comment to check if list correct
        loaded_fl = loaded_fl["content"]
        loaded_fl_id = loaded_fl[: loaded_fl.find("\n")]

        if self.is_file and loaded_fl_id != f"#--filter-path={self.path}":
            self.logger.error(
                "Filter list not loaded: expecting [%s] got [%s] ",
                self.path,
                loaded_fl_id,
            )
        elif not self.is_file and loaded_fl == self.rules:
            self.logger.error(
                "Filter list not loaded: expecting [%s] got [%s] ",
                self.rules[: min(len(self.rules), 20)],
                loaded_fl[: min(len(loaded_fl), 20)],
            )
        else:
            self.logger.info("Filter list loaded successfully: %s", self.path)
