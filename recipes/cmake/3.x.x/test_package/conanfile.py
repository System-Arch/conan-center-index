from six import StringIO
from conan import ConanFile, conan_version
from conan.tools.build import can_run
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            output = StringIO()
            # Third arg to self.run renamed "stdout" in Conan 2.0 but 1.x linter doesn't like it
            self.run("cmake --version", output, env="conanrun")
            output_str = str(output.getvalue())
            self.output.info("Installed version: {}".format(output_str))
            if Version(conan_version).major < 2:
                require_version = str(self.deps_cpp_info["cmake"].version)
            else:
                require_version = str(self.dependencies["cmake"].ref.version)
            self.output.info("Expected version: {}".format(require_version))
            assert_cmake_version = "cmake version %s" % require_version
            assert(assert_cmake_version in output_str)
