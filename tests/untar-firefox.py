from PerfTest import TimeTest
import utils

class UntarFirefox(TimeTest):
    name = "untarfirefox"
    command = "tar -xf firefox-87.0b5.source.tar.xz -C DIRECTORY"

    def setup(self, config, section):
        utils.run_command("wget -nc https://archive.mozilla.org/pub/firefox/releases/87.0b5/source/firefox-87.0b5.source.tar.xz")
