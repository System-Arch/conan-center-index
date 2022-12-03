from conan import ConanFile
from conan.tools.files import chdir, copy, rmdir, get, files
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.build import build_jobs, cross_building, check_min_cppstd
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration
import os


required_conan_version = ">=1.53.0"

class CMakeConan(ConanFile):
    name = "cmake"
    package_type = "application"
    description = "Conan installer for CMake"
    topics = ("cmake", "build", "installer")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/Kitware/CMake"
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "with_openssl": [True, False],
        "bootstrap": [True, False],
    }
    default_options = {
        "with_openssl": True,
        "bootstrap": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.with_openssl = False

    def requirements(self):
        if self.options.with_openssl:
            self.requires("openssl/1.1.1s")

    def validate(self):
        if self.info.settings.os == "Macos" and self.info.settings.arch == "x86":
            raise ConanInvalidConfiguration("CMake does not support x86 for macOS")

    def validate_build(self):
        if self.settings.os == "Windows" and self.options.bootstrap:
            raise ConanInvalidConfiguration("CMake does not support bootstrapping on Windows")

        minimal_cpp_standard = "11"
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, minimal_cpp_standard)

        minimal_version = {
            "gcc": "4.8",
            "clang": "3.3",
            "apple-clang": "9",
            "msvc": "191",
        }

        compiler = str(self.settings.compiler)
        if compiler not in minimal_version:
            self.output.warning(
                "{} recipe lacks information about the {} compiler standard version support".format(self.name, compiler))
            self.output.warning(
                "{} requires a compiler that supports at least C++{}".format(self.name, minimal_cpp_standard))
            return

        version = Version(self.settings.compiler.version)
        if version < minimal_version[compiler]:
            raise ConanInvalidConfiguration(
                "{} requires a compiler that supports at least C++{}".format(self.name, minimal_cpp_standard))

    def layout(self):
        if self.options.bootstrap:
            basic_layout(self, src_folder="src")
        else:
            cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)
        rmdir(self, os.path.join(self.source_folder, "Tests", "RunCMake", "find_package"))

    def generate(self):
        if self.options.bootstrap:
            tc = AutotoolsToolchain(self)
            tc.generate()
            bootstrap_cmake_options = ["--"]
            bootstrap_cmake_options.append(f'-DCMAKE_CXX_STANDARD={"11" if not self.settings.compiler.cppstd else self.settings.compiler.cppstd}')
            if self.settings.os == "Linux":
                if self.options.with_openssl:
                    openssl = self.dependencies["openssl"]
                    bootstrap_cmake_options.append("-DCMAKE_USE_OPENSSL=ON")
                    bootstrap_cmake_options.append(f'-DOPENSSL_USE_STATIC_LIBS={"FALSE" if openssl.options.shared else "TRUE"}')
                else:
                    bootstrap_cmake_options.append("-DCMAKE_USE_OPENSSL=OFF")
            files.save_toolchain_args({"bootstrap_cmake_options": ' '.join(arg for arg in bootstrap_cmake_options)}, namespace="bootstrap")
        else:
            tc = CMakeToolchain(self)
            if not self.settings.compiler.cppstd:
                tc.variables["CMAKE_CXX_STANDARD"] = 11
            tc.variables["CMAKE_BOOTSTRAP"] = False
            if self.settings.os == "Linux":
                tc.variables["CMAKE_USE_OPENSSL"] = self.options.with_openssl
                if self.options.with_openssl:
                    openssl = self.dependencies["openssl"]
                    tc.variables["OPENSSL_USE_STATIC_LIBS"] = not openssl.options.shared
            if cross_building(self):
                tc.variables["HAVE_POLL_FINE_EXITCODE"] = ''
                tc.variables["HAVE_POLL_FINE_EXITCODE__TRYRUN_OUTPUT"] = ''
            tc.generate()

    def build(self):
        if self.options.bootstrap:
            toolchain_file_content = files.load_toolchain_args(self.generators_folder, namespace="bootstrap")
            bootstrap_cmake_options = toolchain_file_content.get("bootstrap_cmake_options")
            with chdir(self, self.source_folder):
                self.run(f'./bootstrap --prefix="" --parallel={build_jobs(self)} {bootstrap_cmake_options}')
                autotools = Autotools(self)
                autotools.make()
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        copy(self, "Copyright.txt", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        if self.options.bootstrap:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                autotools.install()
        else:
            cmake = CMake(self)
            cmake.install()
        rmdir(self, os.path.join(self.package_folder, "doc"))

    def package_id(self):
        del self.info.settings.compiler
        del self.info.options.bootstrap

    def package_info(self):
        self.cpp_info.includedirs = []
