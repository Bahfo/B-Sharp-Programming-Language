module shell;

import std.file;
import std.stdio;
import std.format;


string fetchDocument(string file_path) {
    string contents = readText(file_path);
    return contents;
}

void populateProject(string file_name) {
    string project_path = getcwd() ~ "/" ~ file_name;
    string modules_path = project_path ~ "/modules";
    if (exists(project_path)) {
        writeln(format("[ERROR] A directory with name %s exists.", file_name));
        writeln("At: ", project_path);
        return;
    } else {
        mkdir(project_path);
        chdir(project_path);
        write("main.bsharp", fetchDocument("Docs/template/main.bsharp"));
        mkdir(modules_path);
        chdir(modules_path);
        write("modules_get.json", "{}");
        return;
    }
}

void parseCommand(string[] Args) {
    if (Args[0] == "help") {
        if (Args.length > 1) {
            writeln("[BSHARP SDK ERROR] Unknown arg or args after 'help': ", Args[1..$]);
            return;
        } // Error if help is followed by args.
        string contents = fetchDocument("Docs/genhelp.txt");
        writeln(contents);
    } else if (Args[0] == "init") {
        if (Args.length > 2) {
            writeln("[BSHARP SDK ERROR] too much args for command 'init'");
            return;
        } else if (Args.length < 2) {
            writeln("[BSHARP SDK ERROR] too few args for command 'init'");
            return;
        } else {
            string project_name = Args[1];
            try {
                populateProject(project_name);
            } catch (Exception e) {
                writeln("Exception Occurred: ", e);
                writeln("Exited.");
                return;
            }
        }
    } else if (Args[0] == "install") {
        return;
    } else if (Args[0] == "uninstall") {
        return;
    } else if (Args[0] == "man") {
        return;
    } else {
        writeln("[BSHARP SDK ERROR] Unknown command or argument: ", Args[0]);
        return;
    }
}

void main(string[] Args) {
    parseCommand(Args[1 .. $]);
}