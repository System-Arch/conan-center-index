from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"
    enable_cxx = False

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_CXX"] = self.dependencies["gmp"].options.enable_cxx
        tc.variables["TEST_PIC"] = "fPIC" in self.dependencies["gmp"].options and self.dependencies["gmp"].options.fPIC
        tc.generate()
        # Conan 1.x doesn't permit accessing dependencits in test method()
        if self.dependencies["gmp"].options.enable_cxx:
            self.enable_cxx = True

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
            if self.enable_cxx:
                bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package_cpp")
                self.run(bin_path, env="conanrun")
