module shell;

import std.file : readText, exists, getcwd, mkdirRecurse, thisExePath;
import std.path : buildPath, dirName, absolutePath;
import std.stdio : writeln, writefln;

// Local Imports
import Utils.scan;
import Utils.run;


string fetchDocument(string file_path) {
    // Resolve relative to executable location first, then cwd, then SDK fallback
    string exeDir;
    try {
        exeDir = dirName(thisExePath());
    } catch (Exception) {
        exeDir = "";
    }

    string[] candidates;
    if (exeDir.length > 0) {
        candidates ~= buildPath(exeDir, file_path);
        candidates ~= buildPath(exeDir, "..", file_path);
        candidates ~= buildPath(exeDir, "..", "SDK", file_path);
        candidates ~= buildPath(exeDir, "SDK", file_path);
    }
    candidates ~= buildPath(getcwd(), file_path);
    candidates ~= buildPath(getcwd(), "SDK", file_path);
    // Absolute fallback for development layout
    candidates ~= file_path;

    foreach (c; candidates) {
        try {
            string abs = absolutePath(c);
            if (exists(abs)) {
                return readText(abs);
            }
        } catch (Exception) {
            continue;
        }
    }
    // Final attempt: let readText throw with clear message
    return readText(file_path);
}

void populateProject(string file_name) {
    string project_path = buildPath(getcwd(), file_name);

    // Ensure project directory exists before scanning
    if (!exists(project_path)) {
        mkdirRecurse(project_path);
    }

    CheckResult[] results = doctor(project_path);
    populate(project_path, results);
}

int parseCommand(string[] Args) {
    if (Args.length == 0) {
        writeln("[BSHARP SDK] No command provided. Run 'bsharp help' for usage.");
        return 1;
    }

    if (Args[0] == "help") {
        if (Args.length > 1) {
            writeln("[BSHARP SDK ERROR] Unknown arg or args after 'help': ", Args[1..$]);
            return 1;
        }
        try {
            string contents = fetchDocument("Docs/genhelp.txt");
            writeln(contents);
        } catch (Exception e) {
            writeln("[BSHARP SDK ERROR] Could not load help document: ", e.msg);
            return 1;
        }
        return 0;
    } else if (Args[0] == "init") {
        if (Args.length > 2) {
            writeln("[BSHARP SDK ERROR] too many args for command 'init'");
            return 1;
        } else if (Args.length < 2) {
            writeln("[BSHARP SDK ERROR] too few args for command 'init'");
            return 1;
        } else {
            string project_name = Args[1];
            try {
                populateProject(project_name);
            } catch (Exception e) {
                writeln("Exception Occurred: ", e.msg);
                writeln("Exited.");
                return 1;
            }
            return 0;
        }
    } else if (Args[0] == "run") {
        if (Args.length > 2) {
            writeln("[BSHARP SDK ERROR] too many args for command 'run'");
            return 1;
        } else if (Args.length < 2) {
            writeln("[BSHARP SDK ERROR] too few args for command 'run'");
            return 1;
        } else {
            string target = Args[1];
            try {
                return interpret_BSharp_file(target);
            } catch (Exception e) {
                writeln("[BSHARP SDK ERROR] Failed to run '", target, "': ", e.msg);
                return 1;
            }
        }
    } else if (Args[0] == "install") {
        writeln("[BSHARP SDK] 'install' is not yet implemented.");
        return 1;
    } else if (Args[0] == "uninstall") {
        writeln("[BSHARP SDK] 'uninstall' is not yet implemented.");
        return 1;
    } else if (Args[0] == "man") {
        writeln("[BSHARP SDK] 'man' is not yet implemented.");
        return 1;
    } else {
        writeln("[BSHARP SDK ERROR] Unknown command or argument: ", Args[0]);
        return 1;
    }
}

int main(string[] Args) {
    return parseCommand(Args[1 .. $]);
}
