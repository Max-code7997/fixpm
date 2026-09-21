class Fixpm < Formula
  desc "Interactive fixer for mistyped CLI commands: npm, git, docker, cargo, pip and go"
  homepage "https://github.com/Max-code7997/fixpm"
  version "0.3.2"
  license "MIT"

  # Prebuilt single-file binaries rather than the PyPI sdist: `brew install`
  # should not have to resolve and compile eleven dependency sdists to end up
  # with a 12 MB binary, and the binary is the same artefact the other install
  # channels ship. `pipx install fixpm` remains the Python-native path.
  on_macos do
    on_arm do
      url "https://github.com/Max-code7997/fixpm/releases/download/v0.3.2/fixpm-macos-arm64"
      sha256 "cb1962b64a095c267691c2e2911d3e91c28d45f4bc22d630ca7bc7473cfd902f"
    end
  end

  on_linux do
    on_intel do
      url "https://github.com/Max-code7997/fixpm/releases/download/v0.3.2/fixpm-linux-x64"
      sha256 "cef71b87c30aed9ccb1a7ef3d87e8e204643aa815a7d706a2f2c7aca64590bce"
    end
  end

  # The shell hook runs this probe on the prompt path, where the Python CLI's
  # interpreter start-up is felt as a pause after every failed command. A
  # formula gets one `url`, so a second artefact is a `resource`.
  resource "probe" do
    on_macos do
      on_arm do
        url "https://github.com/Max-code7997/fixpm/releases/download/v0.3.2/fixpm-probe-macos-arm64"
        sha256 "e6422f907559d3a7fbe90fc0f032c9524d6d919d5b50097f02da30a74cacf234"
      end
    end

    on_linux do
      on_intel do
        url "https://github.com/Max-code7997/fixpm/releases/download/v0.3.2/fixpm-probe-linux-x64"
        sha256 "2cd8f444fbedb4f98ba63f4602cbe6b22d05cfedddff812226c2aa70735edda5"
      end
    end
  end

  def install
    # The downloaded file keeps the asset name, which carries the platform.
    bin.install Dir["fixpm-macos-arm64", "fixpm-linux-x64"].first => "fixpm"
    resource("probe").stage do
      bin.install Dir["fixpm-probe-macos-arm64", "fixpm-probe-linux-x64"].first => "fixpm-probe"
    end
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/fixpm --version")
    assert_match version.to_s, shell_output("#{bin}/fixpm-probe --version")
    # Stale rules show up as a missing fix rather than a crash, so assert the
    # fix itself instead of a zero exit code.
    assert_match "docker container ls",
                 shell_output("#{bin}/fixpm-probe --dry-run 'docker container lss'")
  end
end
