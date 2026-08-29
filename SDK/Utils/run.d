module Utils.run;

import std.file : exists, isFile, thisExePath;
import std.path : buildPath, dirName, absolutePath, extension;
import std.process : spawnProcess, wait;
import std.stdio : writeln;

import std.algorithm : endsWith;

private string resolveBSharpPy() {
    string exeDir;
    try {
        exeDir = dirName(thisExePath());
    } catch (Exception) {
        exeDir = "";
    }

    string[] candidates;
    if (exeDir.length > 0) {
        candidates ~= buildPath(exeDir, "bsharp.py");
        candidates ~= buildPath(exeDir, "..", "bsharp.py");
        candidates ~= buildPath(exeDir, "..", "..", "bsharp.py");
        // When built via dub, exe is in SDK subfolder
        candidates ~= buildPath(exeDir, "..", "bsharp.py");
    }
    // cwd based fallbacks
    import std.file : getcwd;
    try {
        string cwd = getcwd();
        candidates ~= buildPath(cwd, "bsharp.py");
        candidates ~= buildPath(cwd, "..", "bsharp.py");
        candidates ~= buildPath(cwd, "..", "..", "bsharp.py");
    } catch (Exception) {}

    // absolute fallback supplied by caller
    candidates ~= "bsharp.py";

    foreach (c; candidates) {
        try {
            string abs = absolutePath(c);
            if (exists(abs) && isFile(abs)) {
                return abs;
            }
        } catch (Exception) {
            continue;
        }
    }
    // Return last candidate to let spawnProcess produce clear error
    return "bsharp.py";
}

private string resolvePython() {
    version (Windows) {
        return "python";
    } else {
        return "python3";
    }
}

int interpret_BSharp_file(string file_path) {
    if (file_path.length == 0) {
        writeln("[BSHARP SDK ERROR] No file provided for 'run'");
        return 1;
    }

    // Validate file exists and has .bsharp extension (mirrors bsharp.py validation)
    string absPath;
    try {
        absPath = absolutePath(file_path);
    } catch (Exception) {
        absPath = file_path;
    }

    if (!exists(absPath) || !isFile(absPath)) {
        writeln("[BSHARP SDK ERROR] File '", file_path, "' does not exist.");
        return 1;
    }

    if (extension(absPath) != ".bsharp") {
        writeln("[BSHARP SDK ERROR] Invalid file extension. B# runner supports '.bsharp' files: ", file_path);
        return 1;
    }

    string bsharpPy = resolveBSharpPy();
    string python = resolvePython();

    // Allow override via env var BSHARP_PYTHON
    import std.process : environment;
    string envPython = environment.get("BSHARP_PYTHON", "");
    if (envPython.length > 0) python = envPython;

    // Also allow BSHARP_PY override for bsharp.py location
    string envPy = environment.get("BSHARP_PY", "");
    if (envPy.length > 0) bsharpPy = envPy;

    try {
        auto pid = spawnProcess([python, bsharpPy, absPath]);
        int exitCode = wait(pid);
        return exitCode;
    } catch (Exception e) {
        // Fallback: try alternative python binary once
        string fallback = (python == "python3") ? "python" : "python3";
        try {
            auto pid2 = spawnProcess([fallback, bsharpPy, absPath]);
            return wait(pid2);
        } catch (Exception e2) {
            writeln("[BSHARP SDK ERROR] Failed to spawn interpreter (", python, " / ", fallback, "): ", e.msg, " / ", e2.msg);
            writeln("  Hint: ensure Python is installed and '", bsharpPy, "' is reachable. Set BSHARP_PYTHON or BSHARP_PY env vars to override.");
            return 1;
        }
    }
}
