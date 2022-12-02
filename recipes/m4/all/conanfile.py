from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, chdir, rmdir, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path
from conan.tools.scm import Version
import os
import shutil

required_conan_version = ">=1.53.0"


class M4Conan(ConanFile):
    name = "m4"
    package_type = "application"
    description = "GNU M4 is an implementation of the traditional Unix macro processor"
    topics = ("macro", "preprocessor")
    homepage = "https://www.gnu.org/software/m4/"
    url = "https://github.com/conan-io/conan-center-index"
    license = "GPL-3.0-only"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    def build_requirements(self):
        if self._settings_build.os == "Windows":
            if not self.conf.get("tools.microsoft.bash:path", default=False, check_type=bool):
                self.tool_requires("msys2/cci.latest")
            self.win_bash = True

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.extra_cflags.append("-FS")
            # Avoid a `Assertion Failed Dialog Box` during configure with build_type=Debug
            # Visual Studio does not support the %n format flag:
            # https://docs.microsoft.com/en-us/cpp/c-runtime-library/format-specification-syntax-printf-and-wprintf-functions
            # Because the %n format is inherently insecure, it is disabled by default. If %n is encountered in a format string,
            # the invalid parameter handler is invoked, as described in Parameter Validation. To enable %n support, see _set_printf_count_output.
            tc.configure_args.extend([
                "gl_cv_func_printf_directive_n=no",
                "gl_cv_func_snprintf_directive_n=no",
                "gl_cv_func_snprintf_directive_n=no",
            ])
            if self.settings.build_type in ("Debug", "RelWithDebInfo"):
                tc.extra_ldflags.append("-PDB")
        elif self.settings.compiler == "clang":
            if Version(self.version) < "1.4.19":
                tc.extra_cflags.extend([
                    "-rtlib=compiler-rt",
                    "-Wno-unused-command-line-argument",
                ])
        if self.settings.os == "Windows":
            tc.configure_args.append("ac_cv_func__set_invalid_parameter_handler=yes")
        env = tc.environment()
        # help2man trick
        env.prepend_path("PATH", self.source_folder)
        # handle msvc
        if is_msvc(self):
            ar_wrapper = unix_path(self, os.path.join(self.source_folder, "build-aux", "ar-lib"))
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("LD", "link")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
        tc.generate(env)

    def _patch_sources(self):
        apply_conandata_patches(self)
        if shutil.which("help2man") == None:
            # dummy file for configure
            help2man = os.path.join(self.source_folder, "help2man")
            save(self, help2man, "#!/usr/bin/env bash\n:")
            if os.name == "posix":
                os.chmod(help2man, os.stat(help2man).st_mode | 0o111)

    def build(self):
        # Support building with source from Git reop
        with chdir(self, self.source_folder):
            command = "./bootstrap"
            if os.path.exists(command) and not os.path.exists("configure"):
                self.run(command)
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        if os.path.islink(os.path.join(self.source_folder, "COPYING")):
            # Use mkdir and copyfile when "COPYING" is a symlink as it is when building with source from Git repo
            os.mkdir(os.path.join(self.package_folder, "licenses"))
            shutil.copyfile(os.path.join(self.source_folder, os.readlink(os.path.join(self.source_folder, "COPYING"))),
                         os.path.join(self.package_folder, "licenses", "COPYING"))
        else:
            copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        # TODO: replace by autotools.install() once https://github.com/conan-io/conan/issues/12153 fixed
        autotools.install(args=[f"DESTDIR={unix_path(self, self.package_folder)}"])
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # M4 environment variable is used by a lot of scripts as a way to override a hard-coded embedded m4 path
        bin_ext = ".exe" if self.settings.os == "Windows" else ""
        m4_bin = os.path.join(self.package_folder, "bin", f"m4{bin_ext}").replace("\\", "/")
        self.runenv_info.define_path("M4", m4_bin)
        self.buildenv_info.define_path("M4", m4_bin)

