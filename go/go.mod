module github.com/Max-code7997/fixpm/go

// 1.26, not 1.22: older toolchains emit a Mach-O without LC_UUID when the
// binary is stripped, and macOS 15+ refuses to load such a binary
// ("dyld: missing LC_UUID load command", exit 134). The CI job that runs the
// built probe is what caught it. This is also the version the probe is
// verified with, so it is the honest floor.
go 1.26
