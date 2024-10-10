import logging
import os
import re
from io import StringIO

from PyQt5 import QtWidgets
from ruamel.yaml import YAML

from core_tools.GUI.keysight_videomaps.GUI.videomode_gui import Ui_MainWindow
from core_tools.startup.config import get_configuration as ct_get_configuration
from core_tools.GUI.qt_util import qt_log_exception, qt_show_exception, qt_show_error


logger = logging.getLogger(__name__)


_help_text = r"""
<html>
<b><u>Favorites</u></b>
<p>
Settings for scan can be saved as favorites.
Only the settings in a checked group
are saved in a file, or applied to the GUI.
Settings that are not in text will not be changed.
</p>
<p>
"Default" is applied when Video Mode is started.
</p>
<p>
Settings are formatted as YAML.
The text fields with settings are editable.
</p>
<p/>
<u>Favorites per project</u>
<p>
By default all favorites are stored in the same directory.
This directory can be changed to store the settings per project.
</p>
The video mode settings directory can be specified in the
<code>ct-config.yaml</code> file as <pre>
videomode:
    settings_dir: ~/.core_tools/videomode
</pre>
or as argument <code>settings_dir="..."</code> when calling
<code>liveplotting(..., settings_dir="...")</code>
<br/>Default directory is
<code>~/.core_tools/videomode</code> which corresponds to <br/>
C:\Users\&lt;user&gt;\.core_tools\videomode on Windows.
</p>
</html>
"""


def yaml_string(data: dict[str, any]) -> str:
    if data in [{}, ""]:
        return ""
    yaml = YAML()
    stream = StringIO()
    yaml.dump(data, stream)
    result = stream.getvalue()
    return result


class Favorites:
    def __init__(self, main_window: Ui_MainWindow, favorites_dir: str | None):
        self._ui_name_list = main_window._favorites_names
        self._ui_name = main_window._fav_name
        self._ui_check_1D = main_window._fav_check_1D
        self._ui_check_2D = main_window._fav_check_2D
        self._ui_check_gen = main_window._fav_check_gen
        self._ui_settings_1D = main_window._fav_settings_1D
        self._ui_settings_2D = main_window._fav_settings_2D
        self._ui_settings_gen = main_window._fav_settings_gen

        if favorites_dir is not None:
            self._favorites_dir = favorites_dir
        else:
            self._favorites_dir = self._get_favorites_dir()

        os.makedirs(self._favorites_dir, exist_ok=True)

        main_window._fav_help.setHtml(_help_text)

    def _get_favorites_dir(self):
        try:
            config = ct_get_configuration()
        except Exception:
            return os.path.expanduser("~/.core_tools/videomode")

        conf_dir = config.get("videomode/settings_dir", "~/.core_tools/videomode")
        return os.path.expanduser(conf_dir)

    def _get_favorite_path(self, name: str):
        return os.path.join(self._favorites_dir, f"videomode.{name}.yaml")

    def read_settings(self, name: str, may_fail: bool = False) -> bool:
        path = self._get_favorite_path(name)
        if not os.path.isfile(path):
            if not may_fail:
                raise Exception(f"Settings file {path} not found")
            return {}
        yaml = YAML()
        try:
            with open(path) as fp:
                settings = yaml.load(fp)
        except Exception:
            logger.error(f"File {path} cannot be parsed")
            if may_fail:
                return {}
            else:
                qt_show_error(
                    "VideoMode: Parse error",
                    f"Stored favorite '{name}' cannot be parsed as YAML.\n"
                    f"Check file '{path}'.")
                raise
        return settings

    def _parse_settings_text(self, text_edit: QtWidgets.QTextEdit, group: str):
        text = text_edit.toPlainText()
        if text == "":
            return {}
        yaml = YAML()
        stream = StringIO(text)
        try:
            result = yaml.load(stream)
        except Exception as ex:
            qt_show_exception("VideoMode: Failed to parse YAML", ex, f"in group '{group}'")
            raise
        return result

    @qt_log_exception
    def save(self):
        name = self._ui_name.text()
        path = self._get_favorite_path(name)
        data = {}
        if self._ui_check_1D.isChecked():
            data['1D'] = self._parse_settings_text(self._ui_settings_1D, "1D")
        if self._ui_check_2D.isChecked():
            data['2D'] = self._parse_settings_text(self._ui_settings_2D, "2D")
        if self._ui_check_gen.isChecked():
            data['gen'] = self._parse_settings_text(self._ui_settings_gen, "gen")
        yaml = YAML()
        with open(path, "w") as fp:
            self._config = yaml.dump(data, fp)
        self._load_favorites()

    @qt_log_exception
    def save_default(self):
        self._ui_name.setText("Default")
        self.save()

    def current_settings(self):
        settings = {}
        if self._ui_check_1D.isChecked():
            settings["1D"] = self._parse_settings_text(self._ui_settings_1D, "1D")
        if self._ui_check_2D.isChecked():
            settings["2D"] = self._parse_settings_text(self._ui_settings_2D, "2D")
        if self._ui_check_gen.isChecked():
            settings["3D"] = self._parse_settings_text(self._ui_settings_gen, "gen")
        return settings

    def load_selected(self, active_settings: dict[str, any]):
        currentItem = self._ui_name_list.currentItem()
        name = currentItem.text() if currentItem is not None else ""
        if name == "":
            return
        if name in ["<active settings>"]:
            self._ui_name.setText("")
            settings = active_settings
        else:
            self._ui_name.setText(name)
            settings = self.read_settings(name)
        self._ui_settings_1D.setText(yaml_string(settings.get("1D", {})))
        self._ui_settings_2D.setText(yaml_string(settings.get("2D", {})))
        self._ui_settings_gen.setText(yaml_string(settings.get("gen", {})))

    def _list_favorites(self):
        pattern = re.compile(r"videomode\.([a-zA-Z0-9_ -.]+)\.yaml")
        result = []
        for entry in os.scandir(self._favorites_dir):
            if m := pattern.match(entry.name):
                result.append(m.group(1))
        return result

    def _is_valid_favorite_name(self, name: str):
        pattern = re.compile(r"[a-zA-Z0-9_ -.]+")
        if not pattern.match(name):
            qt_show_error(
                "VideoMode: Invalid name",
                f"'{name}' is not a valid favorite name.\n"
                "Valid characters are: a-zA-Z0-9_ -.")

    def _load_favorites(self):
        keep_selected = False
        names = self._list_favorites()
        names = sorted(names, key=str.casefold)

        fav_list = self._ui_name_list
        if keep_selected:
            currentItem = fav_list.currentItem()
            selected_name = currentItem.text() if currentItem is not None else ""

        fav_list.clear()
        fav_list.addItem("<active settings>")
        for name in names:
            if name == "Default":
                fav_list.insertItem(1, "Default")
            else:
                fav_list.addItem(name)

        if keep_selected:
            for i in range(fav_list.count()):
                if fav_list.item(i).text() == selected_name:
                    fav_list.setCurrentRow(i)
