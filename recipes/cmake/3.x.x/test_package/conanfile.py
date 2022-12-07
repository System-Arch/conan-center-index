from six import StringIO
from conan import ConanFile
from conan.tools.build import can_run
import re


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            output = StringIO()
            # Third arg to self.run renamed "stdout" in Conan 2.0 but 1.x linter doesn't like it
            self.run("cmake --version", output, env="conanbuild")
            output_str = str(output.getvalue())
            self.output.info("Installed version: {}".format(output_str))
            tokens = re.split('[@#]', self.tested_reference_str)
            require_version = tokens[0].split("/", 1)[1]
            self.output.info("Expected version: {}".format(require_version))
            assert_cmake_version = "cmake version %s" % require_version
            assert(assert_cmake_version in output_str)
